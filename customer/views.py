# external
from allauth.account.adapter import get_adapter
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from rest_framework.exceptions import ErrorDetail, ValidationError
from rest_framework.settings import api_settings
from dj_rest_auth.registration.serializers import SocialLoginSerializer
from dj_rest_auth.views import LoginView as OriginalLoginView

# internal
from customer.serializers import LoginSerializer


class LoginView(OriginalLoginView):
	"""
	Login as the given user and merge the items from the previous UNRECOGNIZED
	or GUEST user with the new user.

	Basic flow:
		1) post() calls serializer.is_valid() -> checks credentials
		2) post() calls login() -> assigns auth tokens to self
		3) login() calls process_login() -> calls ShopAdapter.login()
		4) ShopAdapter.login() -> merge anonymous cart with registered cart
		5) DefaultAccountAdapter.login() -> tries to use allauth backend to auth user
	"""
	serializer_class = LoginSerializer

	def post(self, request, *args, **kwargs):
		# switching users causes cart merging issues if not logged out first.
		if request.user.is_anonymous:
			# in case of an exception, look into resp.text found in:
			# `allauth\socialaccount\providers\facebook\views.py` under:
			# `fb_complete_login` for server response message
			return super().post(request, *args, **kwargs)

		# In practice users wont be able to 'login' if already logged in.
		message = ErrorDetail("Please log out before signing in again.")
		exc = ValidationError({api_settings.NON_FIELD_ERRORS_KEY: [message]})
		response = self.handle_exception(exc)
		self.response = self.finalize_response(request, response, *args, **kwargs)
		return self.response

	def process_login(self):
		# replace user.backend with allauth backend and merge carts
		get_adapter(self.request).login(self.request, self.user)


class SocialLoginView(LoginView):
	"""
	from dj_rest_auth.registration.views import SocialLoginView
	Essentially `SocialLoginView` from `dj_rest_auth`, but needs inherit's
	new `LoginView` instead of the `OriginalLoginView`.

	NOTE: dj_rest_auth's SocialLogin serializer will login the user, so we remove
	the view's inherited ability to login (process_login(): return)

	class used for social authentications
	example usage for facebook with access_token
	-------------
	from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter

	class FacebookLogin(SocialLoginView):
		adapter_class = FacebookOAuth2Adapter
	-------------

	example usage for facebook with code

	-------------
	from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
	from allauth.socialaccount.providers.oauth2.client import OAuth2Client

	class FacebookLogin(SocialLoginView):
		adapter_class = FacebookOAuth2Adapter
		client_class = OAuth2Client
		callback_url = 'localhost:8000'
	-------------
	Basic flow:
		1) post() calls serializer.is_valid() -> checks credentials
		2) serializer -> creates sociallogin and token -> calls adapter.login()
		3) adapter.login() -> login user and merge anonymous cart with new user
		4) post() calls login() -> assigns auth tokens to self (DOES NOT RE-LOGIN)
		5) login() calls process_login() -> does nothing as user already logined
	"""
	serializer_class = SocialLoginSerializer

	def process_login(self):
		# SocialLoginSerializer will login upon form validation
		return


class FacebookLoginView(SocialLoginView):
	"""
	FacebookOAuth2Adapter will login using facebook API. `Client id` and
	`Secret key` are mandatory in admin. The `Secret key` is used to generate
	proof of `Client id` ownership.
	(Social Accounts › Social applications › facebook)

	#TODO: sync social_login_facebook config with settings config (template tags)
	Configure facebook SDK in templates/customer/snippet/social_login_facebook.html
	AND settings.py
	"""
	adapter_class = FacebookOAuth2Adapter  # adapter class used in Serializer
