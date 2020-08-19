# external
from django.urls import path
from dj_rest_auth.views import LogoutView

# internal
# from customer.forms import RegisterUserForm, ContinueAsGuestForm
from customer.views import LoginView, PasswordChangeView

app_name = 'customer'
urlpatterns = [
	path('login/', LoginView.as_view(),
		name='login'),
	# path('register/', AuthFormsView.as_view(form_class=RegisterUserForm),
	# 	name='register-user'),
	# path('continue/', AuthFormsView.as_view(form_class=ContinueAsGuestForm),
	# 	name='continue-as-guest'),

	path('logout/', LogoutView.as_view(),
		name='logout'),
	path('password/change/', PasswordChangeView.as_view(),
		name='password-change'),
	# path('password/reset/', PasswordResetRequestView.as_view(),
	# 	name='password-reset-request'),
]