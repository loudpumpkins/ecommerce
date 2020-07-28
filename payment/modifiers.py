# external
from django.utils.translation import gettext_lazy as _

# internal
from payment.providers import ForwardFundPayment
from shop.modifier import PaymentModifier


class PayInAdvanceModifier(PaymentModifier):
	"""
	This modifiers has no influence on the cart final. It can be used,
	to enable the customer to pay the products on delivery.
	"""
	payment_provider = ForwardFundPayment()

	def get_choice(self):
		return (self.payment_provider.namespace, _("Pay in advance"))
