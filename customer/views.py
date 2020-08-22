# external
from django.contrib.auth import logout, get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import NON_FIELD_ERRORS
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.exceptions import ErrorDetail, ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.settings import api_settings
from dj_rest_auth.views import LoginView as OriginalLoginView
from dj_rest_auth.views import PasswordChangeView as OriginalPasswordChangeView
from dj_rest_auth.registration.views import SocialLoginView

# internal
from customer.models import Customer
from shop.models import Cart


class LoginView(OriginalLoginView):
	"""
	Login as the given user, and merge the items from the current with the new
	user.
	"""
	def login(self):
		try:
			anonymous_cart = Cart.objects.get_from_request(self.request)
		except Cart.DoesNotExist:
			anonymous_cart = None
		if self.request.customer.user.is_anonymous or \
											self.request.customer.is_registered:
			previous_user = None
		else:  # guest
			previous_user = self.request.customer.user
		# rotate the session_key, set self.token and set new self.request.user
		super().login()
		authenticated_cart = Cart.objects.get_from_request(self.request)
		if anonymous_cart:
			# an anonymous customer logged in, now merge his current cart with a cart,
			# which previously might have been created under his account.
			authenticated_cart.merge_with(anonymous_cart)
		if previous_user and previous_user.is_active is False \
										and previous_user != self.request.user:
			# keep the database clean and remove this anonymous entity
			if previous_user.customer.orders.count() == 0:
				previous_user.delete()

	def post(self, request, *args, **kwargs):
		# switching users causes cart merging issues if not logged out first.
		if request.user.is_anonymous:
			return super().post(request, *args, **kwargs)

		# In practice users wont be able to 'login' if already logged in.
		message = ErrorDetail("Please log out before signing in again.")
		exc = ValidationError({api_settings.NON_FIELD_ERRORS_KEY: [message]})
		response = self.handle_exception(exc)
		self.response = self.finalize_response(request, response, *args, **kwargs)
		return self.response


class FacebookLogin(SocialLoginView):
	adapter_class = FacebookOAuth2Adapter


# class PasswordResetRequestView(GenericAPIView):
# 	"""
# 	Calls Django Auth PasswordResetRequestForm save method.
#
# 	Accepts the following POST parameters: email
# 	Returns the success/fail message.
# 	"""
# 	serializer_class = PasswordResetRequestSerializer
# 	permission_classes = (AllowAny,)
# 	form_name = 'password_reset_request_form'
#
# 	def post(self, request, *args, **kwargs):
# 		form_data = request.data.get('form_data', {})
# 		serializer = self.get_serializer(data=form_data)
# 		if not serializer.is_valid():
# 			return Response({self.form_name: serializer.errors}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
#
# 		# send email containing a reset link
# 		serializer.save()
#
# 		# trigger async email queue
# 		email_queued()
#
# 		# Return the success message with OK HTTP status
# 		msg = _("Instructions on how to reset the password have been sent to '{email}'.")
# 		response_data = {self.form_name: {
# 			'success_message': msg.format(**serializer.data),
# 		}}
# 		return Response(response_data)
#
#
# class PasswordResetConfirmView(GenericAPIView):
# 	"""
# 	Password reset e-mail link points onto a CMS page with the Page ID = 'password-reset-confirm'.
# 	This page then shall render the CMS plugin as provided by the **ShopAuthenticationPlugin** using
# 	the form "Confirm Password Reset".
# 	"""
# 	renderer_classes = (CMSPageRenderer, JSONRenderer, BrowsableAPIRenderer)
# 	serializer_class = PasswordResetConfirmSerializer
# 	permission_classes = (AllowAny,)
# 	token_generator = default_token_generator
# 	form_name = 'password_reset_confirm_form'
#
# 	def get(self, request, uidb64=None, token=None):
# 		data = {'uid': uidb64, 'token': token}
# 		serializer_class = self.get_serializer_class()
# 		password = get_user_model().objects.make_random_password()
# 		data.update(new_password1=password, new_password2=password)
# 		serializer = serializer_class(data=data, context=self.get_serializer_context())
# 		if not serializer.is_valid():
# 			return Response({'validlink': False})
# 		return Response({
# 			'validlink': True,
# 			'user_name': force_str(serializer.user),
# 			'form_name': 'password_reset_form',
# 		})
#
# 	def post(self, request, uidb64=None, token=None):
# 		try:
# 			data = dict(request.data['form_data'], uid=uidb64, token=token)
# 		except (KeyError, TypeError, ValueError):
# 			errors = {'non_field_errors': [_("Invalid POST data.")]}
# 		else:
# 			serializer = self.get_serializer(data=data)
# 			if serializer.is_valid():
# 				serializer.save()
# 				response_data = {self.form_name: {
# 					'success_message': _("Password has been reset with the new password."),
# 				}}
# 				return Response(response_data)
# 			else:
# 				errors = serializer.errors
# 		return Response({self.form_name: errors}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
#
