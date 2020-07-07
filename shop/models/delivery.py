# external
from django.core import checks
from django.db import models
from django.utils.translation import gettext_lazy as _

# internal
from shop.models.order import OrderItem
from shop.support import cart_modifiers_pool


class Delivery(models.Model):
	"""
	Shipping provider to keep track on each delivery.
	"""
	order = models.ForeignKey(
		'Order',
		on_delete=models.CASCADE,
		related_name='deliveries'
	)

	shipping_id = models.CharField(
		_("Shipping ID"),
		max_length=255,
		null=True,
		blank=True,
		help_text=_("The transaction processor's reference"),
	)

	fulfilled_at = models.DateTimeField(
		_("Fulfilled at"),
		null=True,
		blank=True,
		help_text=_("Timestamp of delivery fulfillment"),
	)

	shipped_at = models.DateTimeField(
		_("Shipped at"),
		null=True,
		blank=True,
		help_text=_("Timestamp of delivery shipment"),
	)

	shipping_method = models.CharField(
		_("Shipping method"),
		max_length=50,
		help_text=_("The shipping backend used to deliver items of this order"),
	)

	class Meta:
		app_label = 'shop'
		db_table = 'shop'
		unique_together = ['shipping_method', 'shipping_id']
		get_latest_by = 'shipped_at'
		verbose_name = _("Delivery")
		verbose_name_plural = _("Deliveries")

	def __str__(self):
		return _("Delivery ID: {}").format(self.id)

	@classmethod
	def check(cls, **kwargs):
		errors = super().check(**kwargs)
		for field in OrderItem._meta.fields:
			if field.attname == 'canceled' and \
					field.get_internal_type() == 'BooleanField':
				break
		else:
			msg = "Class `{}` must implement a `BooleanField` named `canceled`, " \
				  "if used in combination with a Delivery model."
			errors.append(checks.Error(msg.format(OrderItem.__name__)))
		return errors

	def clean(self):
		if self.order._fsm_requested_transition == ('status', 'ship_goods') \
				and not self.shipped_at:
			shipping_modifier = \
				cart_modifiers_pool.get_active_shipping_modifier(self.shipping_method)
			shipping_modifier.ship_the_goods(self)

	def get_number(self):
		"""
		Hook to get the delivery number. May transform this into a string which
		is better readable.
		"""
		if self.order.allow_partial_delivery:
			for part, delivery in enumerate(self.order.deliveries.all(), 1):
				if delivery.pk == self.pk:
					return "{} / {}".format(self.order.get_number(), part)
		return self.order.get_number()


class DeliveryItem(models.Model):
	"""
	Model to keep track on the delivered quantity for each ordered item. Since the
	quantity can be any numerical value, it has to be defined by the class
	implementing this model.
	"""
	delivery = models.ForeignKey(
		'Delivery',
		verbose_name=_("Delivery"),
		on_delete=models.CASCADE,
		related_name='items',
		help_text=_("Refer to the shipping provider used to ship this item"),
	)

	item = models.ForeignKey(
		'OrderItem',
		on_delete=models.CASCADE,
		related_name='deliver_item',
		verbose_name=_("Ordered item"),
	)

	quantity = models.IntegerField(
		_("Delivered quantity"),
		default=0,
	)

	class Meta:
		app_label = 'shop'
		db_table = 'shop'
		verbose_name = _("Deliver item")
		verbose_name_plural = _("Deliver items")

	@classmethod
	def check(cls, **kwargs):
		errors = super().check(**kwargs)
		for order_field in OrderItem._meta.fields:
			if order_field.attname == 'quantity':
				break
		else:
			msg = "Class `{}` must implement a field named `quantity`."
			errors.append(checks.Error(msg.format(OrderItem.__name__)))
		for deliver_field in OrderItem._meta.fields:
			if deliver_field.attname == 'quantity':
				break
		else:
			msg = "Class `{}` must implement a field named `quantity`."
			errors.append(checks.Error(msg.format(cls.__name__)))
		if order_field.get_internal_type() != deliver_field.get_internal_type():
			msg = "Field `{}.quantity` must be of one same type `{}.quantity`."
			errors.append(checks.Error(msg.format(cls.__name__, OrderItem.__name__)))
		return errors
