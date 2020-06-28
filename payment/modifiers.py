from shop.modifiers import BaseCartModifier


class PaymentCartModifier(BaseCartModifier):
	"""
	See shop.modifiers.BaseCartModifier for usage details

	The methods defined here are called in the following sequence:
	1. `pre_process_cart`
	1a. `pre_process_cart_item`
	2. `process_cart_item`
	2a. `add_extra_cart_item_row`
	3. `process_cart`
	3a. `add_extra_cart_row`
	4.  `post_process_cart`

	Each method accepts the HTTP ``request`` object. It shall be used to let
	implementations determine their prices, availability, taxes, discounts, etc.
	according to the identified customer, the originating country, and other
	request information.
	"""
	identifier = 'payment'

	# TODO - implement a payment cart modifier
