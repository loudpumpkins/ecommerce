# external
from rest_framework import serializers

# internal
from shop.models import Store


class StoreSerializer(serializers.ModelSerializer):

	class Meta:
		model = Store
		fields = ['domain', 'name', 'bucket_name', 'email', 'address',
		          'meta_title', 'meta_description', 'meta_keywords', 'currency_code',
		          'google_analytics', 'facebook_analytics', 'addthis_analytics']
