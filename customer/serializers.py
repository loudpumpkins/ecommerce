# external
from django.conf import settings
from django.contrib.auth import get_user_model
from dj_rest_auth.registration.serializers import \
	(RegisterSerializer as OriginalRegisterSerializer)
from rest_framework import serializers

# internal
from customer.models import Customer


class CustomerSerializer(serializers.ModelSerializer):
	"""
	Customer serializer
	"""
	number = serializers.CharField(source='get_number')

	class Meta:
		model = Customer
		fields = ['number', 'first_name', 'last_name', 'email']


class RegisterSerializer(OriginalRegisterSerializer):
	"""
	Register user with a unique email. Username is removed as a session-based
	username is created when the serializer is saved.
	"""
	username = None  # remove parent's need for a username. Set in `self.save()`
	email = serializers.EmailField(required=True)
	password1 = serializers.CharField(write_only=True)
	password2 = serializers.CharField(write_only=True)

	def save(self, request):
		# creating a customer also creates a user. We return that user to login
		# and return tokens.
		if request.customer.is_visitor:
			customer = Customer.objects.get_or_create_from_request(request)
		else:
			customer = request.customer
		self.cleaned_data = self.get_cleaned_data()
		customer.recognize_as_registered(request)
		customer.user.is_active = True
		customer.user.email = self.cleaned_data['email']
		customer.user.set_password(self.cleaned_data['password1'])
		customer.user.save()
		return customer.user


class GuestSerializer(OriginalRegisterSerializer):
	"""
	Fieldless serializer for creating guest users with a session-based
	username and random password.
	"""
	username = None  # remove parent's need for a username. Set in `self.save()`
	email = None
	password1 = None
	password2 = None

	def validate(self, data):
		# no validation is required
		return data

	def save(self, request):
		# creating a customer also creates a user. We return that user to login
		# and return tokens.
		if request.customer.is_visitor:
			customer = Customer.objects.get_or_create_from_request(request)
		else:
			customer = request.customer
		customer.recognize_as_guest(request)
		customer.user.is_active = settings.GUEST_IS_ACTIVE_USER
		if customer.user.is_active:
			# set a usable password, otherwise the user later can not reset its password
			password = get_user_model().objects.make_random_password(length=30)
			customer.user.set_password(password)
		customer.user.save()
		return customer.user
