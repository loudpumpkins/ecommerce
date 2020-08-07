# external
from django.core.exceptions import ImproperlyConfigured
from django.db.models.signals import pre_delete, pre_save
from django.utils import timezone
from django.utils.module_loading import import_string

# internal
from shop.models.store import Store


class BaseCartModifier:
	"""
	Cart Modifiers are the cart's counterpart to backends. Inherit BaseCartModifier
	and implement the needed methods.

	They allow to implement taxes, rebates, bulk prices, shipping- and payment
	costs in an elegant and reusable manner:
	Every time the cart is refreshed (via it's update() method), the cart will
	call all subclasses of this modifier class registered with their full path
	in `settings.CART_MODIFIERS`.

	The methods defined here are called in the following sequence:

	1. `pre_process_cart`: Totals are not computed, the cart is "rough": only
	relations and quantities are available

	1a. `pre_process_cart_item`: Line totals are not computed, the cart and its
	items are "rough": only relations and quantities are available

	2. `process_cart_item`: Called for each cart_item in the cart. The modifier
	may change the amount in `cart_item.line_total`.

	2a. `add_extra_cart_item_row`: It optionally adds an object of type
	`ExtraCartRow` to the current cart item. This object adds additional
	information displayed on each cart items line.

	3. `process_cart`: Called once for the whole cart. Here, all fields relative
	to cart items are filled. Here the carts subtotal is used to computer the
	carts total.

	3a. `add_extra_cart_row`: It optionally adds an object of type `ExtraCartRow`
	to the current cart. This object adds additional information displayed in
	the carts footer section.

	4.  `post_process_cart`: all totals are up-to-date, the cart is ready to be
	displayed. Any change you make here must be consistent!

	Each method accepts the HTTP ``request`` object. It shall be used to let
	implementations determine their prices, availability, taxes, discounts, etc.
	according to the identified customer, the originating country, and other
	request information.


	- Example usage within context:

	from shop.support import cart_modifiers_pool

	for modifier in cart_modifiers_pool.get_all_modifiers():
		modifier.pre_process_cart(self, request, raise_exception)
		for item in items:
			modifier.pre_process_cart_item(self, item, request, raise_exception)

	"""
	def __init__(self):
		assert hasattr(self, 'identifier'), \
			"Each Cart modifier class requires a unique identifier"

	def arrange_watch_items(self, watch_items, request):
		"""
		Arrange all items, which are being watched.
		Override this method to resort and regroup the returned items.
		"""
		return watch_items

	# these methods are only used for the cart items

	def arrange_cart_items(self, cart_items, request):
		"""
		Arrange all items, which are intended for the shopping cart.
		Override this method to resort and regroup the returned items.
		"""
		return cart_items

	def pre_process_cart(self, cart, request, raise_exception=False):
		"""
		This method will be called before the Cart starts being processed.
		It shall be used to populate the cart with initial values, but not to
		compute the cart's totals.

		:param cart: The cart object.
		:param request: The request object.
		:param raise_exception: If ``True``, raise an exception if cart can not
			be fulfilled.
		"""

	def pre_process_cart_item(self, cart, item, request, raise_exception=False):
		"""
		This method will be called for each item before the Cart starts being
		processed. It shall be used to populate the cart item with initial
		values, but not to compute the item's linetotal.

		:param cart: The cart object.
		:param item: The cart item object.
		:param request: The request object.
		:param raise_exception: If ``True``, raise an exception if cart can not
			be fulfilled.
		"""

	def process_cart_item(self, cart_item, request):
		"""
		This will be called for every line item in the Cart:
		Line items typically contain: product, unit_price, quantity and a
		dictionary with extra row information.

		If configured, the starting line total for every line
		(unit price * quantity) is computed by the `DefaultCartModifier`, which
		is listed as the first modifier. Posterior modifiers can optionally
		change the cart items line total.

		After processing all cart items with all modifiers, these line totals
		are summed up to form the carts subtotal, which is used by method
		`process_cart`.
		"""
		self.add_extra_cart_item_row(cart_item, request)

	def post_process_cart_item(self, cart, item, request):
		"""
		This will be called for every line item in the Cart, while finally
		processing the Cart. It may be used to collect the computed line totals
		for each modifier.
		"""

	def process_cart(self, cart, request):
		"""
		This will be called once per Cart, after every line item was treated by
		method `process_cart_item`.

		The subtotal for the cart is already known, but the total is still
		unknown. Like for the line items, the total is expected to be calculated
		by the first cart modifier, which is the `DefaultCartModifier`.
		Posterior modifiers can optionally change the total and add additional
		information to the cart using an object of type `ExtraCartRow`.
		"""
		self.add_extra_cart_row(cart, request)

	def post_process_cart(self, cart, request):
		"""
		This method will be called after the cart was processed in reverse order
		of the registered cart modifiers.
		The Cart object is "final" and all the fields are computed. Remember
		that anything changed at this point should be consistent: If updating
		the price you should also update all
		relevant totals (for example).
		"""

	def add_extra_cart_item_row(self, cart_item, request):
		"""
		Optionally add an `ExtraCartRow` object to the current cart item.

		This allows to add an additional row description to a cart item line.
		This method optionally utilizes and/or modifies the amount in
		`cart_item.line_total`.
		"""

	def add_extra_cart_row(self, cart, request):
		"""
		Optionally add an `ExtraCartRow` object to the current cart.

		This allows to add an additional row description to the cart.
		This method optionally utilizes `cart.subtotal` and/or modifies the
		amount in `cart.total`.
		"""


class PaymentProvider:
	"""
	Base class for all Payment Service Providers.
	"""
	@property
	def namespace(self):
		"""
		Use a unique namespace for this payment provider. It is used to build
		the communication URLs exposed to an external payment service provider.
		"""
		msg = "The attribute `namespace` must be implemented by the class `{}`"
		raise NotImplementedError(msg.format(self.__class__.__name__))

	def get_urls(self):
		"""
		Return a list of URL patterns for external communication with the payment
		service provider.
		"""
		return []

	def get_payment_request(self, cart, request):
		"""
		Build a JavaScript expression which is evaluated by the success handler
		on the page submitting the purchase command. When redirecting to another
		page, use:
		```
		window.location.href="URL-of-other-page";
		```
		since this expression is evaluated inside an AngularJS directive.
		"""
		return ('alert("Please implement method `get_payment_request` in the '
                'Python class inheriting from `PaymentProvider`!");')


class PaymentModifier(BaseCartModifier):
	"""
	See shop.modifiers.BaseCartModifier for usage details

	The methods defined here are called in the following sequence:
	1. `pre_process_cart`
	1a. `pre_process_cart_item`
	2. `process_cart_item`
	2a. `add_extra_cart_item_row`
	3. `process_cart`
	3a. `add_extra_cart_row`
	4.  `post_process_cart`

	Base class for all payment modifiers. Each method accepts the HTTP
	``request`` object. The purpose of a payment modifier is to calculate the
	payment surcharge and/or prevent its usage, in case the chosen payment
	method is not available for the given customer. Can either append a single
	payment modifier to the list of ``store.payment_modifiers``.

	Must specify at least one payment modifier. If there is more than one, offer
	a select option during checkout. In django-SHOP, one can use the plugin
	**Payment Method Form** to render such a select option.

	Each payment modifier can add a surcharge on the current cart.
	"""
	def __init__(self):
		assert isinstance(getattr(self, 'payment_provider', None),
						  PaymentProvider), "Each Payment modifier class " \
											"requires a Payment Provider"
		super().__init__()

	@property
	def identifier(self):
		"""
		Default identifier for payment providers.
		"""
		return self.payment_provider.namespace

	def get_choice(self):
		"""
		:returns: A tuple consisting of 'value, label' used by the payment form
		dialog to render the available payment choices.
		"""
		msg = "{} must implement method `get_choice()`."
		raise NotImplemented(msg.format(self.__class__))

	def is_active(self, payment_modifier):
		"""
		:returns: ``True`` if this payment modifier is active.
		"""
		assert hasattr(self, 'payment_provider'), "A Payment Modifier require" \
												  "s a Payment Provider"
		return payment_modifier == self.identifier

	def is_disabled(self, cart):
		"""
		Hook method to be overridden by the concrete payment modifier. Shall be
		used to temporarily disable a payment method, in case the cart does not
		fulfill certain criteria, for instance a too small total.

		:returns: ``True`` if this payment modifier is disabled for the current
		cart.
		"""
		return False

	def update_render_context(self, context):
		"""
		Hook to update the rendering context with payment specific data.
		"""
		from shop.models.cart import Cart

		if 'payment_modifiers' not in context:
			context['payment_modifiers'] = {}
		try:
			cart = Cart.objects.get_from_request(context['request'])
			if self.is_active(cart.extra.get('payment_modifier')):
				cart.update(context['request'])
				data = cart.extra_rows[self.identifier].data
				data.update(modifier=self.identifier)
				context['payment_modifiers']['initial_row'] = data
		except (KeyError, Cart.DoesNotExist):
			pass


class ShippingModifier(BaseCartModifier):
	"""
	Base class for all shipping modifiers. The purpose of a shipping modifier is
	to calculate the shipping costs and/or prevent its usage, in case products
	in the cart can not be shipped to the desired destination. The merchant may
	either append a single shipping modifier to the list of
	``shop.cart_modifiers``, or create a sublist of shipping modifier and append
	this sublist to ``SHOP_CART_MODIFIERS``. The latter is useful to instantiate
	the same shipping modifier multiple times for different shipping carriers
	using the same interface.

	The merchant must specify at least one shipping modifier. If there is more
	than one, the merchant shall offer a select option during checkout. In
	django-SHOP, one can use the plugin **Shipping Method Form** to render such
	a select option.

	Each shipping modifier can add a surcharge on the current cart. If weight
	affects the shipping price, it shall be summed up inside the method
	`add_extra_cart_row` and used to lookup the shipping costs.
	"""
	def get_choice(self):
		"""
		:returns: A tuple consisting of 'value, label' used by the shipping form
		dialog to render the available shipping choices.
		"""
		raise NotImplemented("{} must implement method `get_choice()`."
                             .format(self.__class__))

	def is_active(self, shipping_modifier):
		"""
		:returns: ``True`` if this shipping modifier is the actively selected one.
		"""
		return shipping_modifier == self.identifier

	def is_disabled(self, cart):
		"""
		Hook method to be overridden by the concrete shipping modifier. Shall be
		used to temporarily disable a shipping method, in case the cart does not
		fulfill certain criteria, for instance an undeliverable destination address.

		:returns: ``True`` if this shipping modifier is disabled for the current cart.
		"""
		return False

	def update_render_context(self, context):
		"""
		Hook to update the rendering context with shipping specific data.
		"""
		from shop.models.cart import Cart

		if 'shipping_modifiers' not in context:
			context['shipping_modifiers'] = {}
		try:
			cart = Cart.objects.get_from_request(context['request'])
			if self.is_active(cart.extra.get('shipping_modifier')):
				cart.update(context['request'])
				data = cart.extra_rows[self.identifier].data
				data.update(modifier=self.identifier)
				context['shipping_modifiers']['initial_row'] = data
		except (KeyError, Cart.DoesNotExist):
			pass

	def ship_the_goods(self, delivery):
		"""
		Hook to be overridden by the active shipping modifier. It should be used
		to perform the
		shipping request.
		"""
		delivery.shipped_at = timezone.now()


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

	def get_all_modifiers(self, store):
		"""
		Returns all registered modifiers of the shop provided or the shop in
		the request.
		"""
		# data cached
		if store.domain in self.MODIFIERS_CACHE:
			return self.MODIFIERS_CACHE[store.domain]

		# no cached data - make new entry
		imported = [import_string(mc) for mc in store.get_cart_modifiers()]
		self.MODIFIERS_CACHE[store.domain] = [mc() for mc in imported]

		# check for uniqueness of the modifier's `identifier` attribute
		ModifierException = \
			ImproperlyConfigured("Each modifier requires a unique attribute "
			                     "'identifier'.")
		try:
			identifiers = [m.identifier for m in self.MODIFIERS_CACHE[store.domain]]
		except AttributeError:
			# modifier has no identifier
			raise ModifierException
		for i in identifiers:
			if identifiers.count(i) > 1:
				# two or more modifiers with same identifier
				raise ModifierException

		return self.MODIFIERS_CACHE[store.domain]

	def get_shipping_modifiers(self, store):
		"""
		Returns all registered shipping modifiers of this shop instance.
		Must provide either a `store` object or a `request`.
		"""
		return [m for m in self.get_all_modifiers(store) if isinstance(m, ShippingModifier)]

	def get_payment_modifiers(self, store):
		"""
		Returns all registered payment modifiers of this shop instance.
		Must provide either a `store` object or a `request`.
		"""
		return [m for m in self.get_all_modifiers(store) if isinstance(m, PaymentModifier)]

	def get_active_shipping_modifier(self, shipping_modifier):
		"""
		Return the shipping modifier object for the given string.
		"""
		for modifier in self.get_all_modifiers():
			if isinstance(modifier, ShippingModifier) \
					and modifier.is_active(shipping_modifier):
				return modifier

	def get_active_payment_modifier(self, payment_modifier):
		"""
		Return the payment modifier object for the given string.
		"""
		for modifier in self.get_all_modifiers():
			if isinstance(modifier, PaymentModifier) \
					and modifier.is_active(payment_modifier):
				return modifier


cart_modifiers_pool = CartModifiersPool()
pre_save.connect(cart_modifiers_pool.clear_site_cache, sender=Store)
pre_delete.connect(cart_modifiers_pool.clear_site_cache, sender=Store)
