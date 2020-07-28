# external
from django.db import models

# internal
from customer.models import Customer
from shop.modifier import cart_modifiers_pool


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