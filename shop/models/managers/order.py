from decimal import Decimal

# external
from django.db import models
from django.utils.translation import get_language_from_request

# internal
from shared.util import get_client_ip


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