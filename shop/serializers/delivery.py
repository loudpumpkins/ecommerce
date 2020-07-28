# external
from rest_framework import serializers

# internal
from shop.serializers.order import OrderItemSerializer
from shop.models import Delivery, DeliveryItem
from shop.modifier import cart_modifiers_pool


class DeliveryItemSerializer(serializers.ModelSerializer):
	class Meta:
		model = DeliveryItem
		exclude = ['id', 'delivery', 'item']

	def to_representation(self, instance):
		data = OrderItemSerializer(instance.item, context=self.context).data
		data['ordered_quantity'] = data.pop('quantity', None)
		data.update(super().to_representation(instance))
		return data


class DeliverySerializer(serializers.ModelSerializer):
	items = DeliveryItemSerializer(
		many=True,
		read_only=True,
	)

	number = serializers.CharField(source='get_number')
	shipping_method = serializers.SerializerMethodField()

	class Meta:
		model = Delivery
		exclude = ['id', 'order']

	def get_shipping_method(self, instance):
		for shipping_modifier in cart_modifiers_pool\
                        .get_shipping_modifiers(store=instance.order.store):
			value, label = shipping_modifier.get_choice()
			if value == shipping_modifier.identifier:
				break
		else:
			value, label = instance.shipping_method, instance.shipping_method
		return {'value': value, 'label': label}
