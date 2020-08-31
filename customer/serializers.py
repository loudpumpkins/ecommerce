import logging

# external
from django.contrib.auth.forms import \
	(PasswordResetForm as OriginalPasswordResetForm)
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from dj_rest_auth.serializers import \
	(LoginSerializer as OriginalLoginSerializer)
from dj_rest_auth.serializers import \
	(PasswordResetSerializer as OriginalPasswordResetSerializer)
from dj_rest_auth.registration.serializers import \
	(RegisterSerializer as OriginalRegisterSerializer)
from rest_framework import serializers

# internal
from customer.models import Customer


logger = logging.getLogger(__name__)


class CustomerSerializer(serializers.ModelSerializer):
	"""
	Customer serializer
	"""
	number = serializers.CharField(source='get_number')

	class Meta:
		model = Customer
		fields = ['number', 'first_name', 'last_name', 'email']


class LoginSerializer(OriginalLoginSerializer):
	"""
	Assert that a socially logged in customer doesn't try to login using the
	standard login process - socially registered users should login using their
	social account (eg: login with facebook)
	"""
	def validate(self, attrs):
		attrs = super().validate(attrs)
		user = attrs['user']
		try:
			social_account = user.customer.extra['social']
		except (Customer.DoesNotExist, KeyError):
			# No customer or No 'social' key in extra means NOT a social login.
			# green light to proceed
			return attrs
		raise serializers.ValidationError(_("Customer signed up using a social "
		                "platform. Please 'login with %s'.") % social_account)


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
		# only visitors can continue as Guests.
		if not self.context['request']._request.customer.is_visitor:
			raise serializers.ValidationError(_("Registered customers don't have to "
			                                    "register as guests."))
		return data

	def save(self, request):
		# creating a customer also creates a user. We return that user to login
		# and return tokens.
		if request.customer.is_visitor:
			customer = Customer.objects.get_or_create_from_request(request)
		else:
			customer = request.customer
		customer.recognize_as_guest(request)
		customer.user.is_active = False
		# if customer.user.is_active:
		# 	# set usable password, otherwise the user later can not reset its password
		# 	password = get_user_model().objects.make_random_password(length=30)
		# 	customer.user.set_password(password)
		customer.user.save()
		return customer.user


class PasswordResetForm(OriginalPasswordResetForm):
	"""
	Override Django send_mail function to use our email API.
	"""
	def send_mail(self, subject_template_name, email_template_name,
	              context, from_email, to_email, html_email_template_name=None):
		from shared.notifications import password_reset_notification
		context['reset_link'] = "%(protocol)s://%(domain)s%(url)s" % {
			'protocol': context.pop('protocol'),
			'domain': context.pop('domain'),
			'url': reverse('customer:password-reset-confirm', kwargs={
			              'uidb64': context.pop('uid'),
			              'token': context.pop('token'),
		              }),
		}
		user = context.pop('user')
		password_reset_notification(user.customer, context)


class PasswordResetSerializer(OriginalPasswordResetSerializer):

	password_reset_form_class = PasswordResetForm

	def validate_email(self, value):
		"""
		Make sure the password reset is not for a social account.
		"""
		value = super().validate_email(value)
		try:
			customer = Customer.objects.get(user__email=value)
			social = customer.extra['social']
			if social:
				# user signed up using a social login -- no password resets
				msg = _("This email is assigned to a password-less %s user.") % social
				raise serializers.ValidationError(msg)
		except Customer.DoesNotExist:
			logger.warning('Password reset requested for an unknown email [%s].' % value)
		except KeyError:
			pass

		return value

	def get_email_options(self):
		"""change default e-mail options"""
		request = self.context.get('request')
		return {'from_email': request.store.email}
