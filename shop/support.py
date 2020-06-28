# external
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

# internal


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

		cart_modifiers_pool = CartModifiersPool()
		cart_modifiers_pool.get_all_modifiers()

	Usage in context:

		cart_modifiers_pool = CartModifiersPool()
		for modifier in cart_modifiers_pool.get_all_modifiers():
			modifier.pre_process_cart(self, request, raise_exception)
			for item in items:
				modifier.pre_process_cart_item(self, item, request, raise_exception)

	"""
	USE_CACHE = True

	def __init__(self):
		self._modifiers_list = []

	def get_all_modifiers(self):
		"""
		Returns all registered modifiers of this shop instance.
		"""
		if not self.USE_CACHE or not self._modifiers_list:
			self._modifiers_list = []
			for modifiers_class in settings.CART_MODIFIERS:
				if issubclass(modifiers_class, (list, tuple)):
					self._modifiers_list.extend([mc() for mc in modifiers_class()])
				else:
					self._modifiers_list.append(modifiers_class())
			# check for uniqueness of the modifier's `identifier` attribute
			ModifierException = \
				ImproperlyConfigured("Each modifier requires a unique attribute "
									 "'identifier'.")
			try:
				identifiers = [m.identifier for m in self._modifiers_list]
			except AttributeError:
				raise ModifierException
			for i in identifiers:
				if identifiers.count(i) > 1:
					raise ModifierException
		return self._modifiers_list

	def get_shipping_modifiers(self):
		"""
		Returns all registered shipping modifiers of this shop instance.
		"""
		# TODO - implement get_shipping_modifiers
		pass

		# from shop.shipping.modifiers import ShippingModifier
		# return [m for m in self.get_all_modifiers() if isinstance(m, ShippingModifier)]

	def get_payment_modifiers(self):
		"""
		Returns all registered payment modifiers of this shop instance.
		"""
		# TODO - implement get_payment_modifiers
		pass

		# from payment.modifiers import PaymentModifier
		# return [m for m in self.get_all_modifiers() if isinstance(m, PaymentModifier)]

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
