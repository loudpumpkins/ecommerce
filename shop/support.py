# external
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.signals import pre_delete, pre_save
from django.utils import timezone
from django.utils.module_loading import import_string

# internal
from shop.models.store import Store


class Availability:
	"""
	Contains the currently available quantity for a given product and period.
	"""
	def __init__(self, **kwargs):
		"""
		:param earliest:
			Point in time from when this product will be available.

		:param latest:
			Point in time until this product will be available.

		:param quantity:
			Number of available items. The type of this value is the same as
			the type of ``quantity`` in :class:`shop.models.CartItemModel`.

		:param sell_short:
			If ``True``, sell the product even though it's not in stock.
			It then will be shipped at the point in time specified by
			``earliest``.

		:param limited_offer:
			If ``True``, sell the product until the point in time specified by
			``latest``. After that period, the product will not be available
			anymore.
		"""
		tzinfo = timezone.get_current_timezone()
		self.earliest = kwargs.get('earliest', timezone.datetime.min.replace(tzinfo=tzinfo))
		self.latest = kwargs.get('latest', timezone.datetime.max.replace(tzinfo=tzinfo))
		quantity = kwargs.get('quantity', settings.MAX_PURCHASE_QUANTITY)
		self.quantity = min(quantity, settings.MAX_PURCHASE_QUANTITY)
		self.sell_short = bool(kwargs.get('sell_short', False))
		self.limited_offer = bool(kwargs.get('limited_offer', False))
		self.inventory = bool(kwargs.get('inventory', None))


class CartModifiersPool:
	"""
	Loads all the modifier classes

	Usage example:

		from shop.support import cart_modifiers_pool

		for modifier in cart_modifiers_pool.get_all_modifiers(request=request):
			modifier.pre_process_cart(self, request, raise_exception)
			for item in items:
				modifier.pre_process_cart_item(self, item, request, raise_exception)
	"""

	def __init__(self):
		self.MODIFIERS_CACHE = {}

	def clear_cache(self):
		self.MODIFIERS_CACHE = {}

	def clear_site_cache(self, sender, **kwargs):
		"""
		Clear the cache (if primed) each time a site is saved or deleted.
		"""
		instance = kwargs['instance']  # instance is a `store` object
		try:
			del self.MODIFIERS_CACHE[instance.domain]
		except KeyError:
			pass

	def get_all_modifiers(self, request=None, store=None):
		"""
		Returns all registered modifiers of the shop provided or the shop in
		the request.
		Must provide either a `store` object or a `request`.
		"""
		if store is None and request is None:
			raise ImproperlyConfigured("Must provide either a `store` object "
									   "or a `request`.")
		if store is None:
			store = Store.objects.get_current(request)

		# data cached
		if store.domain in self.MODIFIERS_CACHE:
			return self.MODIFIERS_CACHE[store.domain]

		# no cached data - make new entry
		imported = [import_string(mc) for mc in store.get_cart_modifiers()]
		self.MODIFIERS_CACHE[store.domain]['cart'] = [mc() for mc in imported]
		imported = [import_string(mc) for mc in store.get_payment_modifiers()]
		self.MODIFIERS_CACHE[store.domain]['payment'] = [mc() for mc in imported]
		imported = [import_string(mc) for mc in store.get_shipping_modifiers()]
		self.MODIFIERS_CACHE[store.domain]['shipping'] = [mc() for mc in imported]

		# check for uniqueness of the modifier's `identifier` attribute
		ModifierException = \
			ImproperlyConfigured("Each modifier requires a unique attribute "
			                     "'identifier'.")
		modifiers = self.MODIFIERS_CACHE[store.domain]['cart'] + \
		            self.MODIFIERS_CACHE[store.domain]['payment'] + \
		            self.MODIFIERS_CACHE[store.domain]['shipping']
		try:
			identifiers = [m.identifier for m in modifiers]
		except AttributeError:
			raise ModifierException
		for i in identifiers:
			if identifiers.count(i) > 1:
				raise ModifierException

		return modifiers

	def get_shipping_modifiers(self, request=None, store=None):
		"""
		Returns all registered shipping modifiers of this shop instance.
		Must provide either a `store` object or a `request`.
		"""
		if store is None and request is None:
			raise ImproperlyConfigured("Must provide either a `store` object "
									   "or a `request`.")
		if store is None:
			store = Store.objects.get_current(request)
		self.get_all_modifiers(store=store)
		return self.MODIFIERS_CACHE[store.domain]['shipping']

	def get_payment_modifiers(self, request=None, store=None):
		"""
		Returns all registered payment modifiers of this shop instance.
		Must provide either a `store` object or a `request`.
		"""
		if store is None and request is None:
			raise ImproperlyConfigured("Must provide either a `store` object "
			                           "or a `request`.")
		if store is None:
			store = Store.objects.get_current(request)
		self.get_all_modifiers(store=store)
		return self.MODIFIERS_CACHE[store.domain]['payment']

	def get_active_shipping_modifier(self, shipping_modifier):
		"""
		Return the shipping modifier object for the given string.
		"""
		# TODO - implement get_active_shipping_modifier
		pass

		# from shop.shipping.modifiers import ShippingModifier
		# for modifier in self.get_all_modifiers():
		# 	if isinstance(modifier, ShippingModifier) and modifier.is_active(shipping_modifier):
		# 		return modifier

	def get_active_payment_modifier(self, payment_modifier):
		"""
		Return the payment modifier object for the given string.
		"""
		# TODO - implement get_active_payment_modifier
		pass

		# from payment.modifiers import PaymentModifier
		# for modifier in self.get_all_modifiers():
		# 	if isinstance(modifier, PaymentModifier) and modifier.is_active(payment_modifier):
		# 		return modifier


cart_modifiers_pool = CartModifiersPool()
pre_save.connect(cart_modifiers_pool.clear_site_cache, sender=Store)
pre_delete.connect(cart_modifiers_pool.clear_site_cache, sender=Store)
