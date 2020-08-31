# external
from django.urls import path
from django.views.generic import TemplateView
from dj_rest_auth.views import (LogoutView, PasswordChangeView, PasswordResetView,
                                PasswordResetConfirmView)
from dj_rest_auth.registration.views import RegisterView

# internal
from customer.views import LoginView, FacebookLoginView
from customer.serializers import (RegisterSerializer, GuestSerializer,
								  PasswordResetSerializer)

app_name = 'customer'
urlpatterns = [

	# Views - w/ templates
	path('register/', TemplateView.as_view(
		template_name='customer/register.html'),
		name='register'),

	path('password/change/', TemplateView.as_view(
		template_name='customer/password_change.html'),
		name='password-change'),

	path('password/reset/', TemplateView.as_view(
		template_name='customer/password_reset.html'),
		name='password-reset'),

	path('password/reset/confirm/<str:uidb64>/<str:token>/', TemplateView.as_view(
		template_name='customer/password_reset_confirm.html'),
		name='password-reset-confirm'),


	# API - Post Endpoints (no token)
	path('api/login/', LoginView.as_view(),
		name='login-api'),

	path('api/facebook/', FacebookLoginView.as_view(),
		 name='fb-login-api'),

	path('api/register/', RegisterView.as_view(
		serializer_class=RegisterSerializer),
		name='register-api'),

	path('api/register-guest/', RegisterView.as_view(
		serializer_class=GuestSerializer),
		name='register-guest-api'),

	path('api/password/reset/', PasswordResetView.as_view(
		serializer_class=PasswordResetSerializer),
		name='password-reset-api'),

	path('api/password/reset/confirm/', PasswordResetConfirmView.as_view(),
		name='password-reset-confirm-api'),


	# API - Post Endpoints (need token)
	path('api/logout/', LogoutView.as_view(),
		name='logout-api'),

	path('api/password/change/', PasswordChangeView.as_view(),
		name='password-change-api'),

]

