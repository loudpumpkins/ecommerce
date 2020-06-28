from decimal import Decimal
from functools import reduce
import operator

# external
from django.conf import settings
from django.db import models
from django.utils.translation import get_language_from_request

# internal
from customer.models import Customer
from shared.util import get_client_ip
from shop.support import cart_modifiers_pool


################################################################################
# Address


class AddressManager(models.Manager):
    def get_max_priority(self, customer):
        aggr = self.get_queryset().filter(customer=customer)\
            .aggregate(models.Max('priority'))
        priority = aggr['priority__max'] or 0
        return priority

    def get_fallback(self, customer):
        """
        Return a fallback address, whenever the customer has not declared one.
        """
        qs = self.get_queryset()
        return qs.filter(customer=customer).order_by('priority').last()


################################################################################
# Cart

class CartManager(models.Manager):
    def get_from_request(self, request):
        """
        Return the cart for current customer.
        """
        if request.customer.is_visitor:
            raise self.model.DoesNotExist("Cart for visiting customer does not exist.")
        if not hasattr(request, '_cached_cart') or \
                request._cached_cart.customer.user_id != request.customer.user_id:
            request._cached_cart, created = self.get_or_create(customer=request.customer)
        return request._cached_cart

    def get_or_create_from_request(self, request):
        has_cached_cart = hasattr(request, '_cached_cart')
        if request.customer.is_visitor:
            request.customer = Customer.objects.get_or_create_from_request(request)
            has_cached_cart = False
        if not has_cached_cart or \
                request._cached_cart.customer.user_id != request.customer.user_id:
            request._cached_cart, created = self.get_or_create(customer=request.customer)
        return request._cached_cart


class CartItemManager(models.Manager):
    def get_or_create(self, **kwargs):
        """
        Create a unique cart item. If the same product exists already in the
        given cart, increase its quantity.
        :returns (cart_item, bool:created)
        """
        cart = kwargs.pop('cart')
        product = kwargs.pop('product')
        quantity = int(kwargs.pop('quantity', 1))

        # add a new item to the cart, or reuse an existing one, increasing the
        # quantity
        watched = not quantity
        cart_item = product.is_in_cart(cart, watched=watched, **kwargs)
        if cart_item:
            if not watched:
                cart_item.quantity += quantity
            created = False
        else:
            cart_item = self.model(
                cart=cart, product=product, quantity=quantity, **kwargs)
            created = True

        cart_item.save()
        return cart_item, created

    def filter_cart_items(self, cart, request):
        """
        Use this method to fetch items for shopping from the cart. It rearranges
        the result set according to the defined modifiers.
        """
        cart_items = self.filter(cart=cart, quantity__gt=0).order_by('updated_at')
        for modifier in cart_modifiers_pool.get_all_modifiers():
            cart_items = modifier.arrange_cart_items(cart_items, request)
        return cart_items

    def filter_watch_items(self, cart, request):
        """
        Use this method to fetch items from the watch list. It rearranges the
        result set according to the defined modifiers.
        """
        watch_items = self.filter(cart=cart, quantity=0)
        for modifier in cart_modifiers_pool.get_all_modifiers():
            watch_items = modifier.arrange_watch_items(watch_items, request)
        return watch_items


################################################################################
# Order


class OrderQuerySet(models.QuerySet):
    def _filter_or_exclude(self, negate, *args, **kwargs):
        """
        Emulate filter queries on the Order model using a pseudo slug attribute.
        This allows to use order numbers as slugs, formatted by method
        `Order.get_number()`.

        Effectively converts:   order.filter(slug__icontains='2014-00001') to
                                order.filter(number__icontains='201400001')
        """
        lookup_kwargs = {}
        for key, lookup in kwargs.items():
            try:
                index = key.index('__')
                field_name, lookup_type = key[:index], key[index:]
            except ValueError:
                field_name, lookup_type = key, ''
            if field_name == 'slug':
                key, lookup = self.model.resolve_number(lookup).popitem()
                lookup_kwargs.update({key + lookup_type: lookup})
            else:
                lookup_kwargs.update({key: lookup})
        return super()._filter_or_exclude(negate, *args, **lookup_kwargs)


class OrderManager(models.Manager):
    _queryset_class = OrderQuerySet

    def create_from_cart(self, cart, request):
        """
        This creates a new empty Order object with a valid order number (many
        payment service providers require an order number, before the purchase
        is actually completed). Therefore the order is not populated with any
        cart items yet; this must be performed in the next step by calling
        ``order.populate_from_cart(cart, request)``, otherwise the order object
        remains in state ``new``. The latter can happen, if a payment service
        provider did not acknowledge a payment, hence the items remain in the
        cart.
        """
        cart.update(request)
        cart.customer.get_or_assign_number()
        order = self.model(
            customer=cart.customer,
            currency=cart.total.currency,
            _subtotal=Decimal(0),
            _total=Decimal(0),
            stored_request=self.stored_request(request),
        )
        order.get_or_assign_number()
        order.assign_secret()
        order.save()
        return order

    def stored_request(self, request):
        """
        Extract useful information about the request to be used for emulating a
        Django request during offline rendering.
        """
        return {
            'language': get_language_from_request(request),
            'absolute_base_uri': request.build_absolute_uri('/'),
            'remote_ip': get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT'),
        }

    def get_summary_url(self):
        """
        Returns the URL of the page with the list view for all orders related
        to the current customer
        """
        # TODO - implement get_summary_url()
        # if not hasattr(self, '_summary_url'):
        #     try:  # via CMS pages
        #         page = Page.objects.public().get(reverse_id='shop-order')
        #     except Page.DoesNotExist:
        #         page = Page.objects.public().filter(application_urls='OrderApp').first()
        #     if page:
        #         self._summary_url = page.get_absolute_url()
        #     else:
        #         try:  # through hardcoded urlpatterns
        #             self._summary_url = reverse('shop-order')
        #         except NoReverseMatch:
        #             self._summary_url = '/cms-page_or_view_with__reverse_id=shop-order__does_not_exist/'
        # return self._summary_url


################################################################################
# Product


class ProductManager(models.Manager):
    """
    ModelManager for searching products
    """
    def select_lookup(self, search_term):
        """
        Returning a queryset containing the products matching the declared lookup
        fields together with the given search term provided by user or view.
        Each product subclass can define its own lookup fields using the member
        list or tuple `lookup_fields`.
        """
        filter_by_term = \
            (models.Q((sf, search_term)) for sf in self.model.lookup_fields)
        queryset = \
            self.get_queryset().filter(reduce(operator.or_, filter_by_term))
        return queryset

    def indexable(self):
        """
        Return a queryset of indexable Products.
        """
        queryset = self.get_queryset().filter(active=True)
        return queryset

