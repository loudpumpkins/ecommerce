import logging

# external
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject
from django.utils import timezone

# internal
from customer.models import Customer
from shop.models.store import Store

logger = logging.getLogger(__name__)


def get_customer(request):
	"""
	See: 'django.contrib.auth.middleware.AuthenticationMiddleware'
	"""
	if not hasattr(request, '_cached_customer'):
		request._cached_customer = Customer.objects.get_from_request(request)
	return request._cached_customer


def get_store(request):
	"""
	See: 'django.contrib.auth.middleware.AuthenticationMiddleware'
	"""
	if not hasattr(request, '_cached_store'):
		request._cached_store = Store.objects.get_current(request)
	return request._cached_store


class CustomerMiddleware(MiddlewareMixin):
	"""
	Inject the customer python object into the request. We use the same method
	django used to inject the user object to the request in:
	'django.contrib.auth.middleware.AuthenticationMiddleware'
	"""
	def process_request(self, request):
		assert hasattr(request, 'session'), ("The `CustomerMiddleware` middleware "
			"requires session middleware to be installed. Add "
			"'django.contrib.sessions.middleware.SessionMiddleware' to "
			"MIDDLEWARE_CLASSES.")
		assert hasattr(request, 'user'), ("The `CustomerMiddleware` middleware "
		    "requires an authentication middleware to be installed. Add "
		    "'django.contrib.auth.middleware.AuthenticationMiddleware' "
		    "to MIDDLEWARE_CLASSES.")
		request.customer = SimpleLazyObject(lambda: get_customer(request))

	def process_response(self, request, response):
		content_type = response.get('content-type')
		try:
			if content_type.startswith('text/html'):
				request.customer.last_access = timezone.now()
				request.customer.save(update_fields=['last_access'])
		except (AttributeError, ValueError):
			pass
		return response


class StoreMiddleware(MiddlewareMixin):
	"""
	Inject the store python object into the request.
	"""
	def process_request(self, request):
		request.store = SimpleLazyObject(lambda: get_store(request))
