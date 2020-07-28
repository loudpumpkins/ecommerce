# external
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from shared import messages
from shop.exceptions import ProductNotAvailable
from shared.money import AbstractMoney, MoneyMaker

# internal
from shop.serializers import ExtraCartRow
from shop.modifier import BaseCartModifier


class DefaultCartModifier(BaseCartModifier):
	"""
	This modifier is the first and most essential as it sets the cart items line
	total and is required for almost every shopping cart. It also handles the
	most basic calculations, ie. multiplying the items unit prices with the
	chosen quantity.
	"""
	identifier = 'default'

	def pre_process_cart_item(self, cart, cart_item, request, raise_exception=False):
		"""
		Limit the ordered quantity in the cart to the availability in the inventory.
		"""
		kwargs = {'product_code': cart_item.product_code}
		kwargs.update(cart_item.extra)
		availability = cart_item.product.get_availability(request, **kwargs)
		if cart_item.quantity > availability.quantity:
			if raise_exception:
				raise ProductNotAvailable(cart_item.product)
			cart_item.quantity = availability.quantity
			cart_item.save(update_fields=['quantity'])
			message = _("The ordered quantity for item '{product_name}' has "
						"been adjusted to {quantity} which is the maximum, "
						"currently available in stock.").format(
								product_name=cart_item.product.product_name,
								quantity=availability.quantity
							)
			messages.info(request, message, title=_("Verify Quantity"), delay=5)
		return

	def process_cart_item(self, cart_item, request):
		"""
		If configured, the starting line total for every line (unit price * quantity)
		is computed by the `DefaultCartModifier`, which is listed as the first
		modifier. Posterior	modifiers can optionally change the cart items line
		total.

		After processing all cart items with all modifiers, these line totals
		are summed up to form the carts subtotal, which is used by method
		`process_cart`.
		"""
		cart_item.unit_price = cart_item.product.get_price(request)
		cart_item.line_total = cart_item.unit_price * cart_item.quantity
		self.add_extra_cart_item_row(cart_item, request)
		return

	def process_cart(self, cart, request):
		"""
		The subtotal for the cart is already known, but the total is still unknown.
		Like for the line items, the total is expected to be calculated by the
		first cart modifier, which is the `DefaultCartModifier`. Posterior
		modifiers can optionally change the total and add additional information
		to the cart using an object of type `ExtraCartRow`.
		"""
		if not isinstance(cart.subtotal, AbstractMoney):
			Money = MoneyMaker()  # uninitialised AbstractMoney class
			# if we don't know the currency, use the default
			cart.subtotal = Money(cart.subtotal)
		cart.total = cart.subtotal
		self.add_extra_cart_row(cart, request)
		return


class CartIncludeTaxModifier(BaseCartModifier):
	"""
	This tax calculator presumes that unit prices are net prices, hence also the
	subtotal, and that the tax is added globally to the carts total.
	By placing this modifier after the shipping modifiers, one can add tax to
	the shipping costs. Otherwise shipping cost are considered tax free.
	"""
	identifier = 'taxes'  # same as 'ExcludedTaxModifier' as it's one or the other
	taxes = settings.DEFAULT_TAX_RATE / 100

	def add_extra_cart_row(self, cart, request):
		"""
		Add a field on cart.extra_price_fields:
		"""
		amount = cart.subtotal * self.taxes
		instance = {
			'label': _("plus {}% VAT").format(settings.DEFAULT_TAX_RATE),
			'amount': amount,
		}
		cart.extra_rows[self.identifier] = ExtraCartRow(instance)
		cart.total += amount


class CartExcludedTaxModifier(BaseCartModifier):
	"""
	This tax calculator presumes that unit prices are gross prices, hence also
	the subtotal, and that the tax is calculated per cart but not added to the
	cart.
	"""
	identifier = 'taxes'  # same as 'IncludeTaxModifier' as it's one or the other
	taxes = 1 - 1 / (1 + settings.DEFAULT_TAX_RATE / 100)

	def add_extra_cart_row(self, cart, request):
		"""
		Add a field on cart.extra_price_fields:
		"""
		amount = cart.subtotal * self.taxes
		instance = {
			'label': _("{}% VAT incl.").format(settings.DEFAULT_TAX_RATE),
			'amount': amount,
		}
		cart.extra_rows[self.identifier] = ExtraCartRow(instance)

	def add_extra_cart_item_row(self, cart_item, request):
		amount = cart_item.line_total * self.taxes
		instance = {
			'label': _("{}% VAT incl.").format(settings.DEFAULT_TAX_RATE),
			'amount': amount,
		}
		cart_item.extra_rows[self.identifier] = ExtraCartRow(instance)
