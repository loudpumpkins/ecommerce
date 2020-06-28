# external
from rest_framework import serializers

# internal
from customer.models import Customer


class CustomerSerializer(serializers.ModelSerializer):
	"""
	Customer serializer
	"""
	number = serializers.CharField(source='get_number')

	class Meta:
		model = Customer
		fields = ['number', 'first_name', 'last_name', 'email']
