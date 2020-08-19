
import logging

# external
from rest_framework import serializers

# internal
from shop.models import Product
from shop.serializers.other import ImageThumbnailSerializer

logger = logging.getLogger(__name__)


class ProductSerializer(serializers.ModelSerializer):
	"""
	Common serializer for our product model.
	"""
	price = serializers.SerializerMethodField()
	images = ImageThumbnailSerializer(label='product', many=True)
	product_url = serializers.URLField(source='get_absolute_url', read_only=True)

	class Meta:
		model = Product
		fields = ['product_name', 'product_code', 'description', 'meta_keywords',
		          'meta_description', 'quantity', 'extra', 'updated_at', 'price',
		          'images', 'product_url', 'slug']

	def __init__(self, *args, **kwargs):
		kwargs.setdefault('label', 'catalog')
		super().__init__(*args, **kwargs)

	def get_price(self, product):
		price = product.get_price(self.context['request'])
		return '{:f}'.format(price)

	def get_all(self, product):
		images = product.images
		return images

	# def render_html(self, product, postfix):
	# 	"""
	# 	DEPRECATED! -- USE `ImageThumbnailSerializer`
	#
	# 	Return a HTML snippet containing a thumbnailed sample image:
	# 	`<img src="..." >`
	#
	# 	Usage in subclassing class of ProductSerializer:
	# 		```
	# 		thumbnail = serializers.SerializerMethodField()
	#
	# 		def get_thumbnail(self, product)
	# 			return self.render_html(product, 'thumbnail')
	# 		```
	# 	"""
	# 	from django.core import exceptions
	# 	from django.core.cache import cache
	# 	from django.template.loader import select_template
	# 	from django.utils.html import strip_spaces_between_tags
	# 	from django.utils.safestring import mark_safe
	#
	# 	if not self.label:
	# 		msg = "The Product Serializer must be configured using a `label` field."
	# 		raise exceptions.ImproperlyConfigured(msg)
	# 	request = self.context['request']
	# 	cache_key = 'product:{0}|{1}-{2}-{3}'.format(
	# 		product.id, self.label, postfix, request.accepted_renderer.format)
	# 	content = cache.get(cache_key)
	# 	if content:
	# 		logger.debug('Loading content from cache using key: [%s].', cache_key)
	# 		return mark_safe(content)
	# 	template = select_template([
	# 		'shop/products/{0}-{1}.html'.format(self.label, postfix),
	# 	])
	#
	# 	# when rendering emails, we require an absolute URI, so that media can
	# 	# be accessed from the mail client
	# 	absolute_base_uri = request.build_absolute_uri('/').rstrip('/')
	# 	context = {
	# 		'image': product.sample_image,
	# 		'ABSOLUTE_BASE_URI': absolute_base_uri
	# 	}
	# 	if request.accepted_renderer.format in ['api', 'json', 'ajax']:
	# 		context['thumbnail_size'] = getattr(request.store,
	# 		                '{label}_thumbnail_size'.format(label=self.label))
	# 		logger.debug('Set thumbnail_size to: "%s".', context['thumbnail_size'])
	# 	logger.debug('Request came in as: "%s".', request.accepted_renderer.format)
	# 	content = strip_spaces_between_tags(template.render(context, request).strip())
	# 	cache.set(cache_key, content, 86400)  # 1 day cache
	# 	return mark_safe(content)


class ProductSummarySerializer(ProductSerializer):
	"""
	Default serializer to create a summary from our Product model. This summary
	then is used to render various list views, such as the catalog-, the cart-,
	and the list of ordered items.
	"""
	images = None  # replace images with a thumbnail
	thumbnail = ImageThumbnailSerializer(source='sample_image')

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['thumbnail'].label = self.label

	class Meta(ProductSerializer.Meta):
		fields = ['product_name', 'product_code', 'caption', 'quantity', 'extra',
		          'updated_at', 'price', 'order', 'thumbnail', 'product_url']
