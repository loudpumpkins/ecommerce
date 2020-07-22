# external
from django.utils import timezone
from rest_framework import serializers

# internal
from shared.fields import MoneyField
from shop.models import Cart, Order, OrderItem
from shop.serializers import ProductSummarySerializer
from shop.support import cart_modifiers_pool


class OrderItemSerializer(serializers.ModelSerializer):
	line_total = MoneyField()
	unit_price = MoneyField()
	product_code = serializers.CharField()
	summary = serializers.SerializerMethodField(
		help_text="Sub-serializer for fields to be shown in the product's summary.")

	class Meta:
		model = OrderItem
		fields = ['line_total', 'unit_price', 'product_code', 'quantity',
				  'summary', 'extra']

	def get_summary(self, order_item):
		label = self.context.get('render_label', 'order')
		serializer_class = ProductSummarySerializer
		serializer = serializer_class(order_item.product, context=self.context,
									  read_only=True, label=label)
		return serializer.data


class OrderListSerializer(serializers.ModelSerializer):
	number = serializers.CharField(
		source='get_number',
		read_only=True,
	)

	url = serializers.URLField(
		source='get_absolute_url',
		read_only=True,
	)

	status = serializers.CharField(
		source='status_name',
		read_only=True,
	)

	subtotal = MoneyField()
	total = MoneyField()

	class Meta:
		model = Order
		fields = ['number', 'url', 'created_at', 'updated_at', 'subtotal', 'total',
				  'status', 'shipping_address_text', 'billing_address_text']
		read_only_fields = ['shipping_address_text', 'billing_address_text']


class OrderDetailSerializer(OrderListSerializer):
	items = OrderItemSerializer(many=True, read_only=True)

	extra = serializers.DictField(read_only=True)
	amount_paid = MoneyField(read_only=True)
	outstanding_amount = MoneyField(read_only=True)
	cancelable = serializers.BooleanField(read_only=True)

	is_partially_paid = serializers.SerializerMethodField(
		method_name='get_partially_paid',
		help_text="Returns true, if order has been partially paid",
	)

	annotation = serializers.CharField(
		write_only=True,
		required=False,
	)

	reorder = serializers.BooleanField(
		write_only=True,
		default=False,
	)

	cancel = serializers.BooleanField(
		write_only=True,
		default=False,
	)

	active_payment_method = serializers.SerializerMethodField()

	active_shipping_method = serializers.SerializerMethodField()

	class Meta:
		model = Order
		exclude = ['id', 'customer', 'stored_request', '_subtotal', '_total']
		read_only_fields = ['shipping_address_text', 'billing_address_text']

	def get_partially_paid(self, order):
		return order.amount_paid > 0

	def get_active_payment_method(self, order):
		modifier = cart_modifiers_pool.get_active_payment_modifier(
											order.extra.get('payment_modifier'))
		value, label = modifier.get_choice() if modifier else (None, "")
		return {'value': value, 'label': label}

	def get_active_shipping_method(self, order):
		modifier = cart_modifiers_pool.get_active_shipping_modifier(
											order.extra.get('shipping_modifier'))
		value, label = modifier.get_choice() if modifier else (None, "")
		return {'value': value, 'label': label}

	def update(self, order, validated_data):
		order.extra.setdefault('addendum', [])
		if validated_data.get('annotation'):
			timestamp = timezone.now().isoformat()
			order.extra['addendum'].append((timestamp, validated_data['annotation']))
			order.save()
		if validated_data['reorder'] is True:
			cart = Cart.objects.get_from_request(self.context['request'])
			order.readd_to_cart(cart)
		if validated_data['cancel'] is True and order.cancelable():
			order.cancel_order()
			order.save(with_notification=True)
		return order
