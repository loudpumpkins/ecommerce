# external
from django.conf import settings
from django.utils import timezone

# internal


class Availability:
	"""
	Contains the currently available quantity for a given product and period.
	"""
	def __init__(self, **kwargs):
		"""
		:param earliest:
			Point in time from when this product will be available.

		:param latest:
			Point in time until this product will be available.

		:param quantity:
			Number of available items. The type of this value is the same as
			the type of ``quantity`` in :class:`shop.models.CartItemModel`.

		:param sell_short:
			If ``True``, sell the product even though it's not in stock.
			It then will be shipped at the point in time specified by
			``earliest``.

		:param limited_offer:
			If ``True``, sell the product until the point in time specified by
			``latest``. After that period, the product will not be available
			anymore.
		"""
		tzinfo = timezone.get_current_timezone()
		self.earliest = kwargs.get('earliest', timezone.datetime.min.replace(tzinfo=tzinfo))
		self.latest = kwargs.get('latest', timezone.datetime.max.replace(tzinfo=tzinfo))
		quantity = kwargs.get('quantity', settings.MAX_PURCHASE_QUANTITY)
		self.quantity = min(quantity, settings.MAX_PURCHASE_QUANTITY)
		self.sell_short = bool(kwargs.get('sell_short', False))
		self.limited_offer = bool(kwargs.get('limited_offer', False))
		self.inventory = bool(kwargs.get('inventory', None))
