# external
from django.urls import path
from django.views.generic import TemplateView
from dj_rest_auth.views import LogoutView, PasswordChangeView
from dj_rest_auth.registration.views import RegisterView

# internal
from customer.views import LoginView, FacebookLogin
from customer.serializers import RegisterSerializer, GuestSerializer

app_name = 'customer'
urlpatterns = [
	# Views - w/ templates
	path('password/change/', TemplateView.as_view(
		template_name='customer/password_change.html'),
		name='password-change'),
	path('register/', TemplateView.as_view(
		template_name='customer/register.html'),
	     name='register'),

	# Views - Social Login
	path('facebook/', FacebookLogin.as_view(), name='fb_login'),

	# API - Post Endpoints (no token)
	path('api/login/', LoginView.as_view(),
		name='login-api'),
	path('api/register/', RegisterView.as_view(serializer_class=RegisterSerializer),
		name='register-api'),
	path('api/regis-guest/', RegisterView.as_view(serializer_class=GuestSerializer),
		name='register-guest-api'),

	# API - Post Endpoints (need token)
	path('api/logout/', LogoutView.as_view(),
		name='logout-api'),
	path('api/password/change/', PasswordChangeView.as_view(),
		name='password-change-api'),
	# path('password/reset/', PasswordResetRequestView.as_view(),
	# 	name='password-reset-request'),
]
