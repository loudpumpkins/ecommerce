from urllib.parse import urlparse

# external
from django.contrib.auth.models import AnonymousUser
from django.db import models
from django.http.request import HttpRequest

# internal
from customer.serializers import CustomerSerializer
from shared.mailgun import send_mail
from shop.models import Notification, Order
from shop.serializers import (DeliverySerializer, OrderDetailSerializer,
							  StoreSerializer)


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
	This function shall be called, after an Order object performed a transition
	change. `order` parameter is the latest `Order` model instance after all
	modifications.
	"""
	if not isinstance(order, Order):
		raise TypeError("Object order must be an Order model object")
	notifications = Notification.objects.filter(
		transition_target=order.status, store=order.store
	)
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
		for notiatt in notification.notificationattachment_set.all():
			attachments[notiatt.attachment.original_filename] = notiatt.attachment.file.file
		send_mail(recipient, template=template, context=context, files=attachments)
