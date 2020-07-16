from decimal import Decimal
import logging
from urllib.parse import urljoin

# external
from django.conf import settings
from django.core import checks
from django.core.exceptions import ImproperlyConfigured
from django.db import models, transaction
from django.db.models.aggregates import Sum
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

# internal
from fsm import FSMField, transition
from shared.fields import JSONField, MoneyField
from shared.money import MoneyMaker
from shop.models.managers.order import OrderManager
from shop.models.cart import CartItem


class Order(models.Model):
	"""
	An Order is the "in process" counterpart of the shopping cart, which freezes the state of the
	cart on the moment of purchase. It also holds stuff like the shipping and billing addresses,
	and keeps all the additional entities, as determined by the cart modifiers.
	"""
	customer = models.ForeignKey(
		'customer.Customer',
		on_delete=models.PROTECT,
		verbose_name=_("Customer"),
		related_name='orders',
	)

	store = models.ForeignKey(
		'shop.Store',
		on_delete=models.PROTECT,
		verbose_name=_("Store"),
		related_name='orders',
	)

	number = models.PositiveIntegerField(
		_("Order Number"),
		null=True,
		default=None,
		unique=True,
	)

	shipping_address_text = models.TextField(
		_("Shipping Address"),
		blank=True,
		null=True,
		help_text=_("Shipping address at the time of purchase."),
	)

	billing_address_text = models.TextField(
		_("Billing Address"),
		blank=True,
		null=True,
		help_text=_("Billing address at the time of purchase."),
	)

	token = models.CharField(
		_("Token"),
		max_length=40,
		editable=False,
		null=True,
		help_text=_(
			"Secret key to verify ownership on detail view without requiring "
			"authentication."
		),
	)

	decimalfield_kwargs = {
		'max_digits': 30,
		'decimal_places': 2,
	}
	decimal_exp = Decimal('.' + '0' * decimalfield_kwargs['decimal_places'])

	status = FSMField(
		default='new',
		protected=True,
		verbose_name=_("Status"),
	)

	currency = models.CharField(
		max_length=7,
		editable=False,
		help_text=_("Currency in which this order was concluded"),
	)

	_subtotal = models.DecimalField(
		_("Subtotal"),
		**decimalfield_kwargs
	)

	_total = models.DecimalField(
		_("Total"),
		**decimalfield_kwargs
	)

	created_at = models.DateTimeField(
		_("Created at"),
		auto_now_add=True,
	)

	updated_at = models.DateTimeField(
		_("Updated at"),
		auto_now=True,
	)

	extra = JSONField(
		verbose_name=_("Extra fields"),
		help_text=_("Extra information for this order object."),
	)

	stored_request = JSONField(
		help_text=_("Parts of the Request objects from the time of purchase."),
	)

	# default targets for the FSM - can modify in settings.ORDER_WORKFLOWS
	TRANSITION_TARGETS = {
		'new': _("New order without content"),
		'created': _("Order freshly created"),
		'payment_confirmed': _("Payment confirmed"),
		'payment_declined': _("Payment declined"),
	}

	objects = OrderManager()

	class Meta:
		app_label = 'shop'
		verbose_name = _("Order")
		verbose_name_plural = _("Orders")

	def __new__(cls, name, bases, attrs):
		"""
		Add configured Workflow mixin classes to ``Order`` and ``OrderPayment``
		to customize all kinds of state transitions in a pluggable manner.
		"""
		bases = tuple(settings.ORDER_WORKFLOWS) + bases
		# merge the dicts of TRANSITION_TARGETS
		attrs.update(_transition_targets={}, _auto_transitions={})
		for b in reversed(bases):
			TRANSITION_TARGETS = getattr(b, 'TRANSITION_TARGETS', {})
			try:
				delattr(b, 'TRANSITION_TARGETS')
			except AttributeError:
				pass
			if set(TRANSITION_TARGETS.keys()).intersection(
					attrs['_transition_targets']):
				msg = "Mixin class {} already contains a transition named '{}'"
				raise ImproperlyConfigured(msg.format(b.__name__, ', '.join(
					TRANSITION_TARGETS.keys())))
			attrs['_transition_targets'].update(TRANSITION_TARGETS)
			attrs['_auto_transitions'].update(
				cls.add_to_auto_transitions(b))
		Model = super().__new__(cls, name, bases, attrs)
		return Model

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.logger = logging.getLogger('shop.order')

	def __str__(self):
		return self.get_number()

	def __repr__(self):
		return "<{}(pk={})>".format(self.__class__.__name__, self.pk)

	# required to inject OrderWorkflows
	@classmethod
	def add_to_auto_transitions(cls, base):
		result = {}
		for name, method in base.__dict__.items():
			# TODO - figure out what on earth this is doing exactly
			if callable(method) and hasattr(method, '_django_fsm'):
				for name, transition in method._django_fsm.transitions.items():
					if transition.custom.get('auto'):
						result.update({name: method})
		return result

	def get_or_assign_number(self):
		"""
		Hook to get or to assign the order number. It shall be invoked, every
		time an Order object is created. This allows us to use a naming
		convention for our order numbers instead of PKs as order numbers.

		We set a unique number to identify our Order. The first 4 digits
		represent the current year. The last five digits represent a zero-padded
		incremental counter.
		"""
		if self.number is None:
			epoch = timezone.now()
			epoch = epoch.replace(epoch.year, 1, 1, 0, 0, 0, 0)
			aggr = Order.objects.filter(number__isnull=False,
										created_at__gt=epoch).aggregate(
				models.Max('number'))
			try:
				epoc_number = int(str(aggr['number__max'])[4:]) + 1
				self.number = int('{0}{1:05d}'.format(epoch.year, epoc_number))
			except (KeyError, ValueError):
				# the first order this year
				self.number = int('{0}00001'.format(epoch.year))
		return self.get_number()

	def get_number(self):
		"""
		Returns the order number in a more readable way.
		"""
		number = str(self.number)
		return '{}-{}'.format(number[:4], number[4:])

	def assign_secret(self):
		"""
		Hook to assign a secret to authorize access on this Order object without
		authentication.
		"""

	@property
	def secret(self):
		"""
		Hook to return a secret if available.
		"""
		return self.token

	@classmethod
	def resolve_number(cls, number):
		"""
		Return a lookup pair used to filter down a queryset.
		It reverts the effect from the above method `get_number`.
		"""
		bits = number.split('-')
		return dict(number=''.join(bits))

	@property
	def subtotal(self):
		"""
		The summed up amount for all ordered items excluding extra order lines.
		"""
		return MoneyMaker(self.currency)(self._subtotal)

	@property
	def total(self):
		"""
		The final total to charge for this order.
		"""
		return MoneyMaker(self.currency)(self._total)

	@classmethod
	def round_amount(cls, amount):
		if amount.is_finite():
			return Decimal(amount).quantize(cls.decimal_exp)

	def get_absolute_url(self):
		"""
		Returns the URL for the detail view of this order.
		"""
		url = urljoin(Order.objects.get_summary_url(), self.get_number())
		if self.token:
			if not url.endswith('/'):
				url += '/'
			url = urljoin(url, self.token)
		return url

	@transaction.atomic
	@transition(field=status, source='new', target='created')
	def populate_from_cart(self, cart, request):
		"""
		Populate the order object with the fields from the given cart.
		For each cart item a corresponding order item is created populating its
		fields and removing that cart item.
		"""
		assert hasattr(cart, 'subtotal') and hasattr(cart, 'total'), \
			"Missing total or subtotal. Did you forget to invoke " \
			"'cart.update(request)' before populating from cart?"
		self.shipping_address_text = \
			cart.shipping_address.as_text() if cart.shipping_address else ''
		self.billing_address_text = \
			cart.billing_address.as_text() if cart.billing_address else ''
		# in case one of the addresses was None, the customer presumably
		# intended to have the same shipping address and billing address
		if not self.shipping_address_text:
			self.shipping_address_text = self.billing_address_text
		if not self.billing_address_text:
			self.billing_address_text = self.shipping_address_text

		#  Transfer each cartItem to orderItem
		for cart_item in cart.items.all():
			cart_item.update(request)
			order_item = OrderItem(order=self)
			try:
				order_item.populate_from_cart_item(cart_item, request)
				order_item.save()
				cart_item.delete()
			except CartItem.DoesNotExist:
				pass

		#  Transfer cart information
		self._subtotal = Decimal(cart.subtotal)
		self._total = Decimal(cart.total)
		self.extra = dict(cart.extra)
		self.extra.update(rows=[
			(modifier, extra_row.data) for modifier, extra_row
			in cart.extra_rows.items()
		])
		self.save()

	@transaction.atomic
	def readd_to_cart(self, cart):
		"""
		Re-add the items of this order back to the cart.
		"""
		for order_item in self.items.all():
			extra = dict(order_item.extra)
			extra.pop('rows', None)
			extra.update(product_code=order_item.product_code)
			cart_item = order_item.product.is_in_cart(cart, **extra)
			if cart_item:
				cart_item.quantity = max(cart_item.quantity, order_item.quantity)
			else:
				cart_item = CartItem(cart=cart, product=order_item.product,
									 product_code=order_item.product_code,
									 quantity=order_item.quantity, extra=extra)
			cart_item.save()

	def save(self, with_notification=False, **kwargs):
		"""
		:param with_notification: If ``True``, all notifications for the state
		of this Order object are executed.
		"""
		# from shop.transition import transition_change_notification

		auto_transition = self._auto_transitions.get(self.status)
		if callable(auto_transition):
			auto_transition(self)

		# round the total to the given decimal_places
		self._subtotal = Order.round_amount(self._subtotal)
		self._total = Order.round_amount(self._total)
		super().save(**kwargs)
		if with_notification:
			# transition_change_notification(self)
			#  TODO - implement transition change notification
			pass

	@cached_property
	def amount_paid(self):
		"""
		The amount paid is the sum of related orderpayments
		"""
		amount = self.orderpayments.aggregate(amount=Sum('amount'))['amount']
		if amount is None:
			amount = MoneyMaker(self.currency)()
		return amount

	@property
	def outstanding_amount(self):
		"""
		Return the outstanding amount paid for this order
		"""
		return self.total - self.amount_paid

	def is_fully_paid(self):
		return self.amount_paid >= self.total

	@transition(
		field='status', source='*',
		target='payment_confirmed', conditions=[is_fully_paid])
	def acknowledge_payment(self, by=None):
		"""
		Change status to ``payment_confirmed``. This status code is known
		globally and can be used by all external plugins to check, if an Order
		object has been fully paid.
		"""
		self.logger.info("Acknowledge payment by user %s", by)

	def cancelable(self):
		"""
		A hook method to be overridden by mixin classes managing Order cancellations.

		:returns: ``True`` if the current Order is cancelable.
		"""
		return False

	def refund_payment(self):
		"""
		Hook to handle payment refunds.
		"""

	def withdraw_from_delivery(self):
		"""
		Hook to withdraw shipping order.
		"""

	@classmethod
	def get_all_transitions(cls):
		"""
		:returns: A generator over all transition objects for this Order model.
		"""
		return cls.status.field.get_all_transitions(Order)

	@classmethod
	def get_transition_name(cls, target):
		"""
		:returns: The verbose name for a given transition target.
		"""
		return cls._transition_targets.get(target, target)

	def status_name(self):
		"""
		:returns: The verbose name for the current transition state.
		"""
		return self._transition_targets.get(self.status, self.status)

	status_name.short_description = _("State")


class OrderPayment(models.Model):
	"""
	A model to hold received payments for a given order.
	"""
	order = models.ForeignKey(
		Order,
		on_delete=models.CASCADE,
		verbose_name=_("Order"),
		related_name='orderpayments',
	)

	amount = MoneyField(
		_("Amount paid"),
		help_text=_("How much was paid with this particular transfer."),
	)

	transaction_id = models.CharField(
		_("Transaction ID"),
		max_length=255,
		help_text=_("The transaction processor's reference"),
	)

	created_at = models.DateTimeField(
		_("Received at"),
		auto_now_add=True,
	)

	payment_method = models.CharField(
		_("Payment method"),
		max_length=50,
		help_text=_("The payment backend used to process the purchase"),
	)

	class Meta:
		app_label = 'shop'
		verbose_name = _("Order payment")
		verbose_name_plural = _("Order payments")

	def __str__(self):
		return _("Payment ID: {}").format(self.id)


class OrderItem(models.Model):
	"""
	An item for an order.
	"""
	order = models.ForeignKey(
		Order,
		on_delete=models.CASCADE,
		related_name='items',
		verbose_name=_("Order"),
	)

	quantity = models.PositiveIntegerField(_("Ordered quantity"))

	canceled = models.BooleanField(_("Item canceled "), default=False)

	product_name = models.CharField(
		_("Product name"),
		max_length=255,
		null=True,
		blank=True,
		help_text=_("Product name at the moment of purchase."),
	)

	product_code = models.CharField(
		_("Product code"),
		max_length=255,
		null=True,
		blank=True,
		help_text=_("Product code at the moment of purchase."),
	)

	product = models.ForeignKey(
		'Product',
		on_delete=models.SET_NULL,
		verbose_name=_("Product"),
		null=True,
		blank=True,
	)

	_unit_price = models.DecimalField(
		_("Unit price"),
		null=True,  # may be NaN
		help_text=_("Products unit price at the moment of purchase."),
		**Order.decimalfield_kwargs
	)

	_line_total = models.DecimalField(
		_("Line Total"),
		null=True,  # may be NaN
		help_text=_("Line total on the invoice at the moment of purchase."),
		**Order.decimalfield_kwargs
	)

	extra = JSONField(
		verbose_name=_("Extra fields"),
		help_text=_("Extra information for this order item"),
	)

	class Meta:
		app_label = 'shop'
		verbose_name = _("Ordered Item")
		verbose_name_plural = _("Ordered Items")

	def __str__(self):
		return self.product_name

	@classmethod
	def check(cls, **kwargs):
		errors = super().check(**kwargs)
		for cart_field in CartItem._meta.fields:
			if cart_field.attname == 'quantity':
				break
		else:
			msg = "Class `{}` must implement a field named `quantity`."
			errors.append(checks.Error(msg.format(CartItem.__name__)))
		for field in cls._meta.fields:
			if field.attname == 'quantity':
				if field.get_internal_type() != cart_field.get_internal_type():
					msg = "Field `{}.quantity` must be of same type as `{}.quantity`."
					errors.append(checks.Error(msg.format(cls.__name__, CartItem.__name__)))
				break
		else:
			msg = "Class `{}` must implement a field named `quantity`."
			errors.append(checks.Error(msg.format(cls.__name__)))
		return errors

	@property
	def unit_price(self):
		return MoneyMaker(self.order.currency)(self._unit_price)

	@property
	def line_total(self):
		return MoneyMaker(self.order.currency)(self._line_total)

	def populate_from_cart_item(self, cart_item, request):
		"""
		From a given cart item, populate the current order item.
		If the operation was successful, the given item shall be removed from
		the cart. If an exception of type :class:`CartItem.DoesNotExist` is
		raised, discard the order item.
		"""
		if cart_item.quantity == 0:
			raise CartItem.DoesNotExist("Cart Item is on the Wish List")
		kwargs = {'product_code': cart_item.product_code}
		kwargs.update(cart_item.extra)
		cart_item.product.deduct_from_stock(cart_item.quantity, **kwargs)
		self.product = cart_item.product
		# for historical integrity, store the product's name and price at the
		# time of purchase
		self.product_name = cart_item.product.product_name
		self.product_code = cart_item.product_code
		self._unit_price = Decimal(cart_item.unit_price)
		self._line_total = Decimal(cart_item.line_total)
		self.quantity = cart_item.quantity
		self.extra = dict(cart_item.extra)
		extra_rows = [
			(modifier, extra_row.data) for modifier, extra_row
			in cart_item.extra_rows.items()
		]
		self.extra.update(rows=extra_rows)

	def save(self, *args, **kwargs):
		"""
		Before saving the OrderItem object to the database, round the amounts to
		the given decimal places
		"""
		self._unit_price = Order.round_amount(self._unit_price)
		self._line_total = Order.round_amount(self._line_total)
		super().save(*args, **kwargs)
