import logging

# external
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.contrib.auth import get_user_model

# internal
from customer.models import Customer
from shop.models import Cart


logger = logging.getLogger(__name__)


class ShopAccountAdapter(DefaultAccountAdapter):
	"""
	DefaultAccountAdapter is used for regular auth process. Will translate
	API based authentication methods (login, logout, ..) into django based
	authentication methods.
	"""

	def login(self, request, user):
		"""
		Upon login, merge the user's current cart with the cart saved in the
		registered account. Also delete the anonymous user + cart upon login.
		"""
		try:
			# inactive `GUEST` or `UNRECOGNIZED` - (visitors have no cart)
			anonymous_cart = Cart.objects.get_from_request(request)
		except Cart.DoesNotExist:
			anonymous_cart = None
		if request.customer.user.is_anonymous or request.customer.is_authenticated:
			previous_user = None
		else:  # `UNRECOGNISED` user
			previous_user = request.customer.user
		super().login(request, user)  # rotate session_key, self.token, new self.request.user
		authenticated_cart = Cart.objects.get_from_request(request)
		logger.debug('Considering to merge carts: [old=%s] with [new=%s].'
		             % (anonymous_cart, authenticated_cart))
		if anonymous_cart:
			# merge GUEST's or UNRECOGNIZED cart with new user's cart
			authenticated_cart.merge_with(anonymous_cart)
		if previous_user and previous_user.is_active is False \
				and previous_user != request.user:
			# keep the database clean and remove this anonymous entity
			if previous_user.customer.orders.count() == 0:
				previous_user.delete()

	def respond_user_inactive(self, request, user):
		"""
		Prevents HTTP redirect for inactive users - aka Guest users. Allauth
		will not login inactive users which works great for us as to not flush
		session key for guest user.
		"""
		return

	def populate_username(self, request, user):
		"""
		Fills in a valid session based username for socially signed up users.
		Those are users that logged in through social platforms such as
		'Facebook'  or 'Instagram' and an account has been created for them
		based on the information provided by their social platform.
		"""
		if not request.session.session_key:
			request.session.cycle_key()
			assert request.session.session_key
		username = Customer.objects.encode_session_key(
					request.session.session_key)
		if get_user_model().objects.filter(username=username).exists():
			request.session.cycle_key()
			username = Customer.objects.encode_session_key(
						request.session.session_key)
		user.username = username


class ShopSocialAccountAdapter(DefaultSocialAccountAdapter):
	"""
	DefaultSocialAccountAdapter is used to translate social logins such as
	`login with facebook` into django based logins. Uses `AccountAdapter`
	heavily.
	"""

	def save_user(self, request, sociallogin, form=None):
		"""
		Saves a newly signed up social login. In case of auto-signup,
		the signup form is not available.
		"""
		user = sociallogin.user
		customer, _ = Customer.objects.get_or_create(user=user)
		customer.recognize_as_social(request, commit=False)
		customer.store = request.store
		customer.extra = {'social': sociallogin.account.provider,  # 'facebook'
						'social_resp': sociallogin.account.extra_data}
		customer.save()
		# super will user.save(), socialogin.save() and assign user fields.
		return super().save_user(request, sociallogin, form=None)
