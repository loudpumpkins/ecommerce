from urllib.parse import urlparse
import logging

# external
from django.contrib.auth.models import AnonymousUser
from django.db import models
from django.http.request import HttpRequest

# internal
from customer.serializers import CustomerSerializer
from customer.models import Customer
from shared.email import send_mail
from shared.util import get_filename_from_path
from shop.models import Notification, Order
from shop.serializers import (DeliverySerializer, OrderDetailSerializer,
							  StoreSerializer)


logger = logging.getLogger('shop')


class EmulateHttpRequest(HttpRequest):
	"""
	Use this class to emulate a HttpRequest object, when templates must be rendered
	asynchronously, for instance when an email must be generated out of an Order
	object.
	"""
	def __init__(self, customer, stored_request):
		super().__init__()
		parsedurl = urlparse(stored_request.get('absolute_base_uri'))
		self.path = self.path_info = parsedurl.path
		self.environ = {}
		self.META['PATH_INFO'] = parsedurl.path
		self.META['SCRIPT_NAME'] = ''
		self.META['HTTP_HOST'] = parsedurl.netloc
		self.META['HTTP_X_FORWARDED_PROTO'] = parsedurl.scheme
		self.META['QUERY_STRING'] = parsedurl.query
		self.META['HTTP_USER_AGENT'] = stored_request.get('user_agent')
		self.META['REMOTE_ADDR'] = stored_request.get('remote_ip')
		self.method = 'GET'
		self.LANGUAGE_CODE = self.COOKIES['django_language'] = stored_request.get('language')
		self.customer = customer
		self.user = customer.is_anonymous and AnonymousUser or customer.user
		self.current_page = None


def transition_change_notification(order):
	"""
	This function shall be called after an Order object performed a transition
	change. `order` parameter is the latest `Order` model instance after all
	modifications.
	"""
	if not isinstance(order, Order):
		raise TypeError("Object order must be an Order model object")
	notifications = Notification.objects.filter(transition_target=order.status)
	for notification in notifications:
		recipient = notification.get_recipient(order)
		if recipient is None:
			continue

		# emulate a request object which behaves similar to that one, when the
		# customer submitted its order
		emulated_request = EmulateHttpRequest(order.customer, order.stored_request)
		customer_serializer = CustomerSerializer(order.customer)
		render_context = {'request': emulated_request, 'render_label': 'email'}
		order_serializer = OrderDetailSerializer(order, context=render_context)
		store_serializer = StoreSerializer(order.store)
		language = order.stored_request.get('language')
		context = {
			'customer': customer_serializer.data,
			'order': order_serializer.data,
			'store': store_serializer.data,
			'ABSOLUTE_BASE_URI': emulated_request.build_absolute_uri().rstrip('/'),
			'render_language': language,
		}
		try:
			latest_delivery = order.delivery_set.latest()
			context['latest_delivery'] = \
				DeliverySerializer(latest_delivery, context=render_context).data
		except (AttributeError, models.ObjectDoesNotExist):
			pass
		template = notification.mail_template
		attachments = {}
		for notiatt in notification.attachments.all():
			filename = get_filename_from_path(notiatt.attachment.name)
			attachments[filename] = notiatt.attachment.file
		logger.debug('Sending email. [to=%s, event=%s, template=%s, context=%s]'
		             % (recipient, order.status, template, context.keys()))
		send_mail(recipient, template=template, context=context, files=attachments)
	else:
		logger.warning('Attempted to send `%s` notification, but no Notifications '
						'were found in the DB for the given event.' % order.status)


def _customer_notification(customer, action, extra_context=None):
	"""
	This function shall be called after a Customer made an account change.
	`order` parameter is the latest `Order` model instance after all
	modifications.
	"""
	if action not in Notification.extra_events():
		raise AttributeError("Action '%s' is not a registered event that "
		                     "`Notification` can handle. Valid choices are: %s."
		                     % (action, Notification.extra_events().keys()))
	if not isinstance(customer, Customer):
		raise TypeError("Object customer must be a Customer model object")
	notifications = Notification.objects.filter(transition_target=action)
	for notification in notifications:
		recipient = notification.get_recipient(customer)
		if recipient is None:
			continue

		customer_serializer = CustomerSerializer(customer)
		store_serializer = StoreSerializer(customer.store)
		context = {
			'customer': customer_serializer.data,
			'store': store_serializer.data,
			**(extra_context or {})
		}
		template = notification.mail_template
		attachments = {}
		for notiatt in notification.attachments.all():
			filename = get_filename_from_path(notiatt.attachment.name)
			attachments[filename] = notiatt.attachment.file
		logger.debug('Sending email. [to=%s, event=%s, template=%s, context=%s]'
		             % (recipient, action, template, context.keys()))
		send_mail(recipient, template=template, context=context, files=attachments)
	else:
		logger.warning('Attempted to send `%s` notification, but no Notifications '
		               'were found in the DB for the given event.' % action)


def user_registration_notification(customer, context=None):
	"""
	Send email to all recipients upon new user registration. All customer driven
	notifications will have a `customer` and `store` serialized data appended
	to the provided context.

	Password reset template variables:
	'customer', 'store'
	"""
	_customer_notification(customer, 'user_registered', extra_context=context)


def password_reset_notification(customer, context=None):
	"""
	Send email to all recipients upon password reset request. All customer driven
	notifications will have a `customer` and `store` serialized data appended
	to the provided context.

	Expected context eg: {
		'email': 'myemail@hotmail.com',
		'site_name': 'localhost',
		'reset_link': 'http://localhost/auth/password/reset/confirm/NDk/5jha25e'
	}

	Password reset template variables:
	'email', 'site_name', 'reset_link', 'customer', 'store'
	"""
	for key in ['email', 'site_name', 'reset_link']:
		assert key in context, "'%s' is a mandatory field that's missing from " \
		                       "context."
	_customer_notification(customer, 'password_reset', extra_context=context)
