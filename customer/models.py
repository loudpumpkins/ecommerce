import string
from importlib import import_module
import warnings
import logging

# external
from allauth.account.signals import user_signed_up
from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, DEFAULT_DB_ALIAS
from django.dispatch import receiver
from django.template.loader import select_template
from django.utils import timezone
from django.utils.functional import SimpleLazyObject
from django.utils.translation import gettext_lazy as _

# internal
from customer.managers import CustomerState, CustomerManager, AddressManager
from shared.fields import ChoiceEnumField, JSONField, CountryField


SessionStore = import_module(settings.SESSION_ENGINE).SessionStore()
logger = logging.getLogger(__name__)


class Customer(models.Model):
	"""
	Customer is a profile model that extends the django User model if a customer
	is authenticated. On checkout, a User object is created for anonymous
	customers also (with unusable password).

	If this model is materialized, then also register the corresponding serializer
	class :class:`shop.serializers.defaults.customer.CustomerSerializer`.
	"""
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		primary_key=True,
		related_name='customer',
	)

	store = models.ForeignKey(
		'shop.Store',
		on_delete=models.DO_NOTHING,
		related_name='customers',
		# default=None,
		# null=True,
		# blank=True,
	)

	number = models.PositiveIntegerField(
		_("Customer Number"),
		null=True,
		default=None,
		unique=True,
	)

	recognized = ChoiceEnumField(
		_("Recognized as"),
		enum_type=CustomerState,
		help_text=_("Designates the state the customer is recognized as."),
	)

	last_access = models.DateTimeField(
		_("Last accessed"),
		default=timezone.now,
	)

	extra = JSONField(
		editable=False,
		verbose_name=_("Extra information about this customer"),
	)

	objects = CustomerManager()

	class Meta:
		verbose_name = _("Customer")
		verbose_name_plural = _("Customers")
		# unique_together = [('store', 'user')]

	def __str__(self):
		return self.get_username()

	def get_username(self):
		return self.user.get_username()

	def get_full_name(self):
		return self.user.get_full_name()

	@property
	def first_name(self):
		return self.user.first_name

	@first_name.setter
	def first_name(self, value):
		self.user.first_name = value

	@property
	def last_name(self):
		return self.user.last_name

	@last_name.setter
	def last_name(self, value):
		self.user.last_name = value

	@property
	def email(self):
		return self.user.email

	@email.setter
	def email(self, value):
		self.user.email = value

	@property
	def date_joined(self):
		return self.user.date_joined

	@property
	def last_login(self):
		return self.user.last_login

	@property
	def groups(self):
		return self.user.groups

	@property
	def is_anonymous(self):
		# visitors are also anonymous
		return self.recognized in (CustomerState.UNRECOGNIZED, CustomerState.GUEST)

	@property
	def is_authenticated(self):
		return self.recognized in (CustomerState.SOCIAL, CustomerState.REGISTERED)

	@property
	def is_recognized(self):
		"""
		Return True if the customer is associated with a User account.
		Unrecognized customers have accessed the shop, but did not register
		an account nor declared themselves as guests.
		"""
		return self.recognized is not CustomerState.UNRECOGNIZED

	@property
	def is_guest(self):
		"""
		Return true if the customer isn't associated with valid User account,
		but declared himself as a guest, leaving their email address.
		"""
		return self.recognized is CustomerState.GUEST

	def recognize_as_guest(self, request=None, commit=True):
		"""
		Recognize the current customer as guest customer.
		"""
		if self.recognized != CustomerState.GUEST:
			self.recognized = CustomerState.GUEST
			if commit:
				self.save(update_fields=['recognized'])
			# TODO send and receive signal -- suggestion below
			# customer_recognized = Signal(providing_args=['customer', 'request'])
			# customer_recognized.send(sender=self.__class__, customer=self, request=request)

	@property
	def is_social(self):
		"""
		Return true if the customer logged in through a social platform. They
		can re-login, view orders, but cannot change passwords. They must always
		login through the same platform they originally logged in through.
		"""
		return self.recognized is CustomerState.SOCIAL

	def recognize_as_social(self, request=None, commit=True):
		"""
		Recognize the current customer as a socially logged in customer.
		"""
		if self.recognized != CustomerState.SOCIAL:
			self.recognized = CustomerState.SOCIAL
			if commit:
				self.save(update_fields=['recognized'])
			# TODO send and receive signal -- suggestion below
			# customer_recognized = Signal(providing_args=['customer', 'request'])
			# customer_recognized.send(sender=self.__class__, customer=self, request=request)

	@property
	def is_registered(self):
		"""
		Return true if the customer has registered himself.
		"""
		return self.recognized is CustomerState.REGISTERED

	def recognize_as_registered(self, request=None, commit=True):
		"""
		Recognize the current customer as registered customer.
		"""
		if self.recognized != CustomerState.REGISTERED:
			self.recognized = CustomerState.REGISTERED
			if commit:
				self.save(update_fields=['recognized'])
			# TODO send and receive signal -- suggestion below
			# customer_recognized = Signal(providing_args=['customer', 'request'])
			# customer_recognized.send(sender=self.__class__, customer=self, request=request)

	@property
	def is_visitor(self):
		"""
		Always False for instantiated Customer objects.
		"""
		return False

	@property
	def is_expired(self):
		"""
		Return True if the session of an unrecognized customer expired or is not
		decodable.
		Registered customers never expire.
		Guest customers only expire, if they failed to fulfil the purchase.
		"""
		is_expired = False
		if self.recognized is CustomerState.UNRECOGNIZED:
			try:
				session_key = CustomerManager.decode_session_key(self.user.username)
				is_expired = not SessionStore.exists(session_key)
			except KeyError:
				msg = "Unable to decode username '{}' as session key"
				warnings.warn(msg.format(self.user.username))
				is_expired = True
		return is_expired

	def get_number(self):
		return self.number

	def get_or_assign_number(self):
		"""
		Hook to get or to assign the customers number. It is invoked, every time
		an Order object is created. Using a customer number, which is different
		from the primary key is useful to assign sequential numbers only to
		customers which actually bought something. Otherwise the customer number
		(primary key) is increased whenever a site visitor puts something into
		the cart. If he never proceeds to checkout, that entity expires and may
		be deleted at any time in the future.
		"""
		if self.number is None:
			aggr = Customer.objects.filter(number__isnull=False).aggregate(
				models.Max('number'))
			self.number = (aggr['number__max'] or 0) + 1
			self.save()
		return self.get_number()

	def as_text(self):
		template_names = [
			'shop/customer.txt',
		]
		template = select_template(template_names)
		return template.render({'customer': self})

	def save(self, **kwargs):
		if 'update_fields' not in kwargs:
			self.user.save(using=kwargs.get('using', DEFAULT_DB_ALIAS))
		super().save(**kwargs)

	def delete(self, *args, **kwargs):
		if self.user.is_active and self.recognized is CustomerState.UNRECOGNIZED:
			# invalid state of customer, keep the referred User
			super().delete(*args, **kwargs)
		else:
			# also delete self through cascading
			self.user.delete(*args, **kwargs)


class BaseAddress(models.Model):
	customer = models.ForeignKey(
		Customer,
		on_delete=models.CASCADE,
		related_name='+',
	)

	priority = models.SmallIntegerField(
		default=0,
		db_index=True,
		help_text=_("Priority for using this address"),
	)

	name = models.CharField(
		_("Full name"),
		max_length=1024,
	)

	address1 = models.CharField(
		_("Address line 1"),
		max_length=1024,
	)

	address2 = models.CharField(
		_("Address line 2"),
		max_length=1024,
		blank=True,
		null=True,
	)

	zip_code = models.CharField(
		_("ZIP / Postal code"),
		max_length=12,
	)

	city = models.CharField(
		_("City"),
		max_length=1024,
	)

	country = CountryField(_("Country"))

	objects = AddressManager()

	def as_text(self):
		"""
		Return the address as plain text to be used for printing, etc.
		"""
		template_names = [
			'shop/address.txt',
		]
		template = select_template(template_names)
		return template.render({'address': self})

	class Meta:
		abstract = True


class ShippingAddress(BaseAddress):
	address_type = 'shipping'

	class Meta:
		verbose_name = _("Shipping Address")
		verbose_name_plural = _("Shipping Addresses")


class BillingAddress(BaseAddress):
	address_type = 'billing'

	class Meta:
		verbose_name = _("Billing Address")
		verbose_name_plural = _("Billing Addresses")


@receiver(user_logged_in)
def handle_customer_login(sender, **kwargs):
	"""
	When the user is logged in, subsequent calls to request.customer will refer
	to previous Customer (likely visitor customer). So we update request.customer
	to an authenticated Customer upon login.

	NOTE: inactive users such as Guest users are NOT logged in.
	"""
	try:
		kwargs['request'].customer = kwargs['user'].customer
		logger.debug("A user [%s] logged in. Assigned the current user's "
		             "`Customer` to the request. (request.Customer)" % kwargs['user'])
	except (AttributeError, ObjectDoesNotExist) as e:
		kwargs['request'].customer = SimpleLazyObject(
			lambda: Customer.objects.get_from_request(kwargs['request']))
		logger.debug("Was not able to set 'request.customer' for the new logged "
		               "in user. (%s)" % e)


@receiver(user_logged_out)
def handle_customer_logout(sender, **kwargs):
	"""
	Update request.customer to a visiting Customer
	"""
	# defer assignment to anonymous customer, since the session_key is not yet
	# rotated
	kwargs['request'].customer = SimpleLazyObject(
		lambda: Customer.objects.get_from_request(kwargs['request']))
	logger.debug("User logged out. Set `Customer` to `get_from_request(request)`.")


@receiver(user_signed_up)
def handle_customer_signup(sender, **kwargs):
	"""
	Send welcome message - registration notification
	:param sender: User
	:param kwargs: request, user, [sociallogin (if social account only)]
	"""
	from shared.notifications import user_registration_notification
	customer = kwargs.get('user').customer
	user_registration_notification(customer)
