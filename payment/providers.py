from django.core.exceptions import ImproperlyConfigured

# internal
from shop.models import Order
from shop.modifier import PaymentProvider


class ForwardFundPayment(PaymentProvider):
	"""
	Provides a simple prepayment payment provider.
	"""
	namespace = 'forward-fund-payment'

	def __init__(self):
		if (not (callable(getattr(Order, 'no_payment_required', None)) and callable(
				getattr(Order, 'awaiting_payment', None)))):
			msg = "Missing methods in Order model. Add 'shop.payment.workflows" \
                  ".ManualPaymentWorkflowMixin' to SHOP_ORDER_WORKFLOWS."
			raise ImproperlyConfigured(msg)
		super().__init__()

	def get_payment_request(self, cart, request):
		order = Order.objects.create_from_cart(cart, request)
		order.populate_from_cart(cart, request)
		if order.total == 0:
			order.no_payment_required()
		else:
			order.awaiting_payment()
		order.save(with_notification=True)
		return 'window.location.href="{}";'.format(order.get_absolute_url())
