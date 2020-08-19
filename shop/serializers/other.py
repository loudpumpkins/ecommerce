import ast

# external
from django.conf import settings
from easy_thumbnails.files import get_thumbnailer
from rest_framework import serializers
from rest_framework.fields import empty

# internal
from shop.models.cart import Cart
from shared.rest_fields import MoneyField


class AvailabilitySerializer(serializers.Serializer):
	earliest = serializers.DateTimeField()
	latest = serializers.DateTimeField()
	quantity = serializers.ReadOnlyField()
	sell_short = serializers.BooleanField()
	limited_offer = serializers.BooleanField()


class AddToCartSerializer(serializers.Serializer):
	"""
	This serializer is used by the view class to handle the communication from
	the "Add to Cart" dialog box.

	If a product has variations, which influence the fields in the "Add to Cart"
	dialog box, then this serializer shall be overridden by a customized
	implementation. Such a customized "*Add to Cart*" serializer has to be
	connected to the `AddToCartView`. This can be achieved in the projects
	`urls.py` by changing the catalog's routing to:
	```
	urlpatterns = [
		...
		url(r'^(?P<slug>[\w-]+)/add-to-cart', AddToCartView.as_view(
			serializer_class=CustomAddToCartSerializer,
		)),
		...
	]
	```

	POST and GET are essentially the same, except that GET assumes a quantity of
	1 and POST requires user to send the requested quantity.
	Will responded with the min(requested, available, allowed) quantity, subtotal,
	availability details and more minor details.

	Can edit `extra` value to be passed to the product's get_availability(**extra).
	"""
	quantity = serializers.IntegerField(default=1, min_value=1)
	unit_price = MoneyField(read_only=True)
	subtotal = MoneyField(read_only=True)
	product = serializers.IntegerField(read_only=True, help_text="Product's PK")
	product_code = serializers.CharField(read_only=True)  # Exact product code
	extra = serializers.DictField(read_only=True, default={})  # get_availability()
	is_in_cart = serializers.BooleanField(read_only=True, default=False)
	availability = AvailabilitySerializer(read_only=True)

	def __init__(self, instance=None, data=empty, **kwargs):
		context = kwargs.get('context', {})
		if 'product' in context:
			instance = self.get_instance(context, data, kwargs)
			if data is not empty and 'quantity' in data:
				# POST
				quantity = self.fields['quantity'].to_internal_value(data['quantity'])
			else:
				# GET
				quantity = self.fields['quantity'].default
			instance.setdefault('quantity', quantity)
			super().__init__(instance, data, context=context)
		else:
			super().__init__(instance, data, **kwargs)

	def to_representation(self, instance):
		data = super().to_representation(instance)
		try:
			data['quantity'] = self._validated_data['quantity']
		except AttributeError:
			data['quantity'] = self.validate_quantity(data['quantity'])
		data['subtotal'] = MoneyField().to_representation(
            data['quantity'] * instance['unit_price']
        )
		return data

	def validate_quantity(self, quantity):
		"""
		Restrict the quantity allowed putting into the cart to the available
		quantity in stock.
		"""
		availability = self.instance['availability']
		return min(quantity, availability.quantity)

	def get_instance(self, context, data, extra_args):
		"""
		Method to store the ordered products in the cart item instance.
		Remember to override this method, if the ``product_code`` is part of the
		variation rather than being part of the product itself.
		"""
		product = context['product']
		request = context['request']
		try:
			cart = Cart.objects.get_from_request(request)
		except Cart.DoesNotExist:
			cart = None
		extra = data.get('extra', {}) if data is not empty else {}
		return {
			'product': product.id,
			'product_code': product.product_code,
			'unit_price': product.get_price(request),
			'is_in_cart': bool(product.is_in_cart(cart)),
			'extra': extra,
			'availability': product.get_availability(request, **extra),
		}


class ImageThumbnailSerializer(serializers.Serializer):
	"""
	Generates a store specific thumbnail based on the mandatory `label` provided
	as a keyword argument. Returns the thumbnail's url, dimensions and size.

	May be used as `Many=True` or `Many=False`. In either case, the queryset
	or instance provided must have a models.ImageField field named `image`.
	"""
	url = serializers.SerializerMethodField()

	width = serializers.SerializerMethodField()

	height = serializers.SerializerMethodField()

	size = serializers.SerializerMethodField()

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def get_url(self, image_model):
		if not hasattr(self, '_thumbnail_{}'.format(image_model.pk)):
			self.generate_thumbnail(image_model)
		thumbnail = getattr(self, '_thumbnail_{}'.format(image_model.pk))
		return thumbnail.url

	def get_width(self, image_model):
		if not hasattr(self, '_thumbnail_{}'.format(image_model.pk)):
			self.generate_thumbnail(image_model)
		thumbnail = getattr(self, '_thumbnail_{}'.format(image_model.pk))
		return int(thumbnail.width)

	def get_height(self, image_model):
		if not hasattr(self, '_thumbnail_{}'.format(image_model.pk)):
			self.generate_thumbnail(image_model)
		thumbnail = getattr(self, '_thumbnail_{}'.format(image_model.pk))
		return int(thumbnail.height)

	def get_size(self, image_model):
		if not hasattr(self, '_thumbnail_{}'.format(image_model.pk)):
			self.generate_thumbnail(image_model)
		thumbnail = getattr(self, '_thumbnail_{}'.format(image_model.pk))
		return int(thumbnail.size)

	def generate_thumbnail(self, image_model):
		setattr(self, '_thumbnail_{}'.format(image_model.pk), image_model.image)
		options = self._get_options()
		if options:
			thumbnailer = get_thumbnailer(image_model.image)
			setattr(self, '_thumbnail_{}'.format(image_model.pk),
			        thumbnailer.get_thumbnail(options))

	def _get_options(self):
		request = self.context['request']
		if request.accepted_renderer.format in ['api', 'json', 'ajax']:
			options_string = getattr(
				request.store, '{}_thumbnail_options'.format(self.label))
			if options_string.lower() in ['none', 'original', 'raw', '']:
				return None
			return self._convert_options_string(options_string)
		return settings.DEFAULT_THUMBNAIL_OPTIONS[self.label]

	def _convert_options_string(self, string):
		# Convert string dictionary to dictionary object
		options = ast.literal_eval(string)
		assert 'size' in options, ('Store "%s" is missing the size option in '
		    '%s_thumbnail_options.' % self.context['request'].store.name, self.label)
		if isinstance(options['size'], str):
			# 'size': '120x120' --> 'size': (120, 120)
			options['size'] = tuple(map(int, options['size'].split('x')))
		return options
