# external
from django.utils.translation import gettext_lazy as _

# internal
from shop.modifier import ShippingModifier


class SelfCollectionModifier(ShippingModifier):
	"""
	This modifiers has no influence on the cart final. It can be used,
	to enable the customer to pick up the products in the shop.
	"""
	identifier = 'self-collection'

	def get_choice(self):
		return (self.identifier, _("Self-collection"))

	def ship_the_goods(self, delivery):
		if not delivery.shipping_id:
			delivery.shipping_id = str(delivery.id)
		super().ship_the_goods(delivery)
