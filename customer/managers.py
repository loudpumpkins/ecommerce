import string
from importlib import import_module
import warnings

# external
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, DEFAULT_DB_ALIAS
from django.db.models.fields import FieldDoesNotExist
from django.dispatch import receiver
from django.utils import timezone
from django.utils.functional import SimpleLazyObject
from django.utils.translation import gettext_lazy as _

# internal
from shared.fields import ChoiceEnum


class CustomerState(ChoiceEnum):
	UNRECOGNIZED = 0, _("Unrecognized")
	GUEST = 1, _("Guest")
	REGISTERED = 2, _("Registered")


class CustomerQuerySet(models.QuerySet):
	def _filter_or_exclude(self, negate, *args, **kwargs):
		"""
		Emulate filter queries on a Customer using attributes from the User object.
		Example: Customer.objects.filter(last_name__icontains='simpson') will return
		a queryset with customers whose last name contains "simpson".
		"""
		opts = self.model._meta
		lookup_kwargs = {}
		for key, lookup in kwargs.items():
			try:
				field_name = key[:key.index('__')]
			except ValueError:
				field_name = key
			if field_name == 'pk':
				field_name = opts.pk.name
			try:
				opts.get_field(field_name)
				if isinstance(lookup, get_user_model()):
					lookup.pk  # force lazy object to resolve
				lookup_kwargs[key] = lookup
			except FieldDoesNotExist as fdne:
				try:
					get_user_model()._meta.get_field(field_name)
					lookup_kwargs['user__' + key] = lookup
				except FieldDoesNotExist:
					raise fdne
				except Exception as other:
					raise other
		result = super()._filter_or_exclude(negate, *args, **lookup_kwargs)
		return result


class CustomerManager(models.Manager):
	"""
	Manager for the Customer database model. This manager can also cope with
	customers, which have an entity in the database but otherwise are considered
	as anonymous. The username of these so called unrecognized customers is a
	compact version of the session key.
	"""
	BASE64_ALPHABET = string.digits + string.ascii_uppercase + string.ascii_lowercase + '.@'
	REVERSE_ALPHABET = dict((c, i) for i, c in enumerate(BASE64_ALPHABET))
	BASE36_ALPHABET = string.digits + string.ascii_lowercase

	_queryset_class = CustomerQuerySet

	@classmethod
	def encode_session_key(cls, session_key):
		"""
		Session keys have base 36 and length 32. Since the field ``username``
		accepts only up to 30 characters, the session key is converted to a base
		64 representation, resulting in a length of approximately 28.
		"""
		return cls._encode(int(session_key[:32], 36), cls.BASE64_ALPHABET)

	@classmethod
	def decode_session_key(cls, compact_session_key):
		"""
		Decode a compact session key back to its original length and base.
		"""
		base_length = len(cls.BASE64_ALPHABET)
		n = 0
		for c in compact_session_key:
			n = n * base_length + cls.REVERSE_ALPHABET[c]
		return cls._encode(n, cls.BASE36_ALPHABET).zfill(32)

	@classmethod
	def _encode(cls, n, base_alphabet):
		base_length = len(base_alphabet)
		s = []
		while True:
			n, r = divmod(n, base_length)
			s.append(base_alphabet[r])
			if n == 0:
				break
		return ''.join(reversed(s))

	def get_queryset(self):
		"""
		Whenever we fetch from the Customer table, inner join with the User table
		to reduce the number of presumed future queries to the database.
		"""
		qs = self._queryset_class(self.model, using=self._db).select_related('user')
		return qs

	def create(self, *args, **kwargs):
		if 'user' in kwargs and kwargs['user'].is_authenticated:
			kwargs.setdefault('recognized', CustomerState.REGISTERED)
			# .setdefault will only insert data if none exists
		customer = super().create(*args, **kwargs)
		return customer

	def _get_visiting_user(self, session_key):
		"""
		Since the Customer has a 1:1 relation with the User object, look for an
		entity of a User object. As its ``username`` (which must be unique),
		using the given session key.
		"""
		username = self.encode_session_key(session_key)
		try:
			user = get_user_model().objects.get(username=username)
		except get_user_model().DoesNotExist:
			user = AnonymousUser()
		return user

	def get_from_request(self, request):
		"""
		Return an Customer object for the current User object.
		"""
		if request.user.is_anonymous and request.session.session_key:
			# the visitor is determined through the session key
			user = self._get_visiting_user(request.session.session_key)
		else:
			user = request.user
		try:
			if user.customer:
				return user.customer
		except AttributeError:
			pass
		if request.user.is_authenticated:
			customer, created = self.get_or_create(user=user)
			if created:  # `user` has been created by another app than shop
				customer.recognize_as_registered(request)
		else:
			customer = VisitingCustomer()
		return customer

	def get_or_create_from_request(self, request):
		if request.user.is_authenticated:
			user = request.user
			recognized = CustomerState.REGISTERED
		else:
			if not request.session.session_key:
				request.session.cycle_key()
				assert request.session.session_key
			username = self.encode_session_key(request.session.session_key)
			# create or get a previously created inactive intermediate user,
			# which later can declare himself as guest, or register as a valid Django user
			try:
				user = get_user_model().objects.get(username=username)
			except get_user_model().DoesNotExist:
				user = get_user_model().objects.create_user(username)
				user.is_active = False
				user.save()

			recognized = CustomerState.UNRECOGNIZED
		customer, created = self.get_or_create(user=user, recognized=recognized)
		return customer


class VisitingCustomer:
	"""
	This dummy object is used for customers which just visit the site. Whenever
	a VisitingCustomer adds something to the cart, this object is replaced
	against a real Customer object.
	"""
	user = AnonymousUser()

	def __str__(self):
		return 'Visitor'

	@property
	def email(self):
		return ''

	@email.setter
	def email(self, value):
		pass

	@property
	def is_anonymous(self):
		return True

	@property
	def is_authenticated(self):
		return False

	@property
	def is_recognized(self):
		return False

	@property
	def is_guest(self):
		return False

	@property
	def is_registered(self):
		return False

	@property
	def is_visitor(self):
		return True

	def save(self, **kwargs):
		pass


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
		qs = self.get_queryset().filter(customer=customer)
		return qs.order_by('priority').last()