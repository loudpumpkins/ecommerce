# external
from django.core import exceptions
from django.core.cache import cache
from django.template import TemplateDoesNotExist
from django.template.loader import select_template
from django.utils.html import strip_spaces_between_tags
from django.utils.safestring import mark_safe, SafeText
from django.utils.translation import get_language_from_request
from rest_framework import serializers

# internal
from shop.models import Product


class ProductSerializer(serializers.ModelSerializer):
	"""
	Common serializer for our product model.
	"""
	price = serializers.SerializerMethodField()
	product_type = serializers.CharField(read_only=True)
	product_model = serializers.CharField(read_only=True)
	product_url = serializers.URLField(source='get_absolute_url', read_only=True)

	class Meta:
		model = Product
		fields = '__all__'

	def __init__(self, *args, **kwargs):
		kwargs.setdefault('label', 'catalog')
		super().__init__(*args, **kwargs)

	def get_price(self, product):
		price = product.get_price(self.context['request'])
		return '{:f}'.format(price)

	def render_html(self, product, postfix):
		"""
		Return a HTML snippet containing a rendered summary for the given
		product. This HTML snippet typically contains a ``<figure>`` element with
		a sample image ``<img src="..." >`` and a ``<figcaption>`` containing a
		short description of the product.

		Build a template search path with `postfix` distinction.
		"""
		if not self.label:
			msg = "The Product Serializer must be configured using a `label` field."
			raise exceptions.ImproperlyConfigured(msg)
		app_label = product._meta.app_label.lower()
		request = self.context['request']
		cache_key = 'product:{0}|{1}-{2}-{3}-{4}-{5}'.format(product.id, app_label,
			self.label, product.product_model, postfix,
			get_language_from_request(request))
		content = cache.get(cache_key)
		if content:
			return mark_safe(content)
		params = [
			(app_label, self.label, product.product_model, postfix),
			(app_label, self.label, 'product', postfix),
			('shop', self.label, product.product_model, postfix),
			('shop', self.label, 'product', postfix),
		]
		try:
			template = select_template(['{0}/products/{1}-{2}-{3}.html'.format(*p)
										for p in params])
		except TemplateDoesNotExist:
			return SafeText("<!-- no such template: '{0}/products/{1}-{2}-{3}.html' -->"
							.format(*params[0]))
		# when rendering emails, we require an absolute URI, so that media can
		# be accessed from the mail client
		absolute_base_uri = request.build_absolute_uri('/').rstrip('/')
		context = {'product': product, 'ABSOLUTE_BASE_URI': absolute_base_uri}
		content = strip_spaces_between_tags(template.render(context, request).strip())
		cache.set(cache_key, content, 86400)  # 1 day cache
		return mark_safe(content)


class ProductSelectSerializer(serializers.ModelSerializer):
	"""
	A simple serializer to convert the product's name and code used for rendering
	the `Select2 Widget`_'s content, while looking up for a certain product.
	This serializer shall return a list of 2-tuples, whose 1st entry is the
	primary key of the product and the second entry is the rendered name.

	.. _Select2 Widget: https://github.com/applegrew/django-select2
	"""
	text = serializers.SerializerMethodField()

	class Meta:
		model = Product
		fields = ['id', 'text']

	def get_text(self, instance):
		return instance.product_name


class ProductSummarySerializer(ProductSerializer):
	"""
	Default serializer to create a summary from our Product model. This summary
	then is used to render various list views, such as the catalog-, the cart-,
	and the list of ordered items.
	In case the Product model is polymorphic, this shall serialize the smallest
	common denominator of all product information.
	"""
	media = serializers.SerializerMethodField(
		help_text="Returns a rendered HTML snippet containing a sample image "
				  "among other elements",
	)

	caption = serializers.SerializerMethodField(
		help_text="Returns the content from caption field if available",
	)

	class Meta(ProductSerializer.Meta):
		fields = ['id', 'product_name', 'product_url', 'product_model', 'price',
				  'media', 'caption']

	def get_media(self, product):
		return self.render_html(product, 'media')

	def get_caption(self, product):
		return getattr(product, 'caption', None)
