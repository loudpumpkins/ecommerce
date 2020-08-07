# external
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.aggregates import Sum
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

# internal
from shared.fields import JSONField, MoneyField
from shop.exceptions import ProductNotAvailable
from shop.models.cart import CartItem
from shop.models.product_image import ProductImage
from shop.models.managers.product import ProductManager
from shop.support import Availability


class Product(models.Model):
	"""
	Product model for the shop.

	Some attributes for this class are mandatory. They shall be implemented as
	property method. The following fields MUST be implemented:

	``product_name``: Return the pronounced name for this product in its
	localized language.

	Additionally you MUST implement the following methods
	``get_absolute_url()``	and ``get_price()``.
	"""
	active = models.BooleanField(
		_("Active"),
		default=True,
		help_text=_("Is this product publicly visible"),
	)

	store = models.ForeignKey(
		'shop.Store',
		on_delete=models.CASCADE,
		related_name='product'
	)

	product_name = models.CharField(
		max_length=255,
		verbose_name=_("Product Name"),
	)

	product_code = models.CharField(
		_("Product code"),
		max_length=255,
		# unique=True, # unique together with store
	)

	slug = models.SlugField(
		_("Slug"),
		# unique=True, # unique together with store
	)

	caption = models.TextField(
		verbose_name=_("Caption"),
		blank=True,
		null=True,
		help_text=_("Short description for the catalog list view"),
	)

	description = models.TextField(
		verbose_name=_("Description"),
		blank=True,
		null=True,
		help_text=_("Full product description for the detail view"),
	)

	meta_keywords = models.TextField(
		verbose_name=_("Meta Keywords"),
		blank=True,
		null=True,
		help_text=_("Comma separated product keyword description."),
	)

	meta_description = models.TextField(
		verbose_name=_("Meta Description"),
		blank=True,
		null=True,
		help_text=_("Full SEO friendly product description."),
	)

	unit_price = MoneyField(
		_("Unit price"),
		decimal_places=3,
		help_text=_("Net price for this product"),
	)

	order = models.PositiveIntegerField(
		verbose_name=_("Sort by"),
		db_index=True,
		help_text=_("Ascending order"),
	)

	images = models.ManyToManyField(
		'filer.Image',
		through=ProductImage,
	)

	quantity = models.PositiveIntegerField(
		_("Quantity"),
		default=0,
		validators=[MinValueValidator(0)],
		help_text=_("Available quantity in stock")
	)

	extra = JSONField(
		verbose_name=_("Extra information about this product"),
	)

	created_at = models.DateTimeField(
		_("Created at"),
		auto_now_add=True,
	)

	updated_at = models.DateTimeField(
		_("Updated at"),
		auto_now=True,
	)

	# filter expression used to search for a product item using the Select2 widget
	lookup_fields = ['product_code__startswith', 'product_name__icontains']

	objects = ProductManager()

	class Meta:
		app_label = 'shop'
		unique_together = [('store', 'product_code'), ('store', 'slug')]
		ordering = ('order',)
		verbose_name = _("Product")
		verbose_name_plural = _("Products")

	def __str__(self):
		return self.product_code

	@property
	def sample_image(self):
		return self.images.first()

	def product_type(self):
		"""
		For future alternate product types
		"""
		return "Commodity"

	product_type.short_description = _("Product type")

	@property
	def product_model(self):
		"""
		For future alternate product models - will need a polymorphic parent model
		"""
		return "Product"

	def get_absolute_url(self):
		"""
		Hook for returning the canonical Django URL of this product.
		"""
		return reverse('shop:product-detail', args=(self.slug,))

	def get_price(self, request):
		"""
		Hook for returning the current price of this product.
		The price shall be of type Money.

		Use the `request` object to vary the price according to the logged in user,
		its country code or the language.
		"""
		return self.unit_price

	def get_product_variant(self, **kwargs):
		"""
		Hook for returning the variant of a product using parameters passed in
		by **kwargs. If the product has no variants, then return the product
		itself.

		:param **kwargs: A dictionary describing the product's variations.
		"""
		return self

	def get_product_variants(self):
		"""
		Hook for returning a queryset of variants for the given product.
		If the product has no variants, then the queryset contains just itself.
		"""
		return self._meta.model.objects.filter(pk=self.pk)

	def get_availability(self, request, **kwargs):
		"""
		Returns the current available quantity for this product.

		If other customers have pending carts containing this same product, the
		quantity is adjusted accordingly.

		# TODO invalidate carts which were not converted into an order

		:param request:
			Optionally used to vary the availability according to the logged in
			user, its country code or language.

		:param **kwargs:
			Extra arguments passed to the underlying method. Useful for products
			with variations.

		:return: An object of type :class:`shop.support.Availability`.
		"""
		availability = Availability(quantity=self.quantity)
		cart_items = CartItem.objects.filter(product=self).values('quantity')
		availability.quantity -= \
			cart_items.aggregate(sum=Coalesce(Sum('quantity'), 0))['sum']
		return availability

	def managed_availability(self):
		"""
		:return True: If this product has its quantity managed by some inventory
		functionality.
		"""
		return True

	def is_in_cart(self, cart, watched=False, **kwargs):
		"""
		Checks if the current product is already in the given cart, and if so,
		returns the corresponding cart_item.

		:param watched (bool): This is used to determine if this check shall
			only be performed for the watch-list.

		:param **kwargs: Optionally one may pass arbitrary information about the
			product being looked up. This can be used to determine if a product
			with variations shall be considered equal to the same cart item,
			resulting in an increase of it's quantity, or if it shall be
			considered as a separate cart item, resulting in the creation of a
			new item.

		:returns: The cart item (of type CartItem) containing the product
			considered as equal to the current one, or ``None`` if no product
			matches in the cart.
		"""
		cart_item_qs = CartItem.objects.filter(cart=cart, product=self)
		return cart_item_qs.first()

	def deduct_from_stock(self, quantity, **kwargs):
		"""
		Hook to deduct a number of items of the current product from the stock's
		inventory.

		:param quantity: Number of items to deduct.

		:param **kwargs:
			Extra arguments passed to the underlying method. Useful for products
			with variations.
		"""
		if quantity > self.quantity:
			raise ProductNotAvailable(self)
		self.quantity -= quantity
		self.save(update_fields=['quantity'])

	def get_weight(self):
		"""
		Optional hook to return the product's gross weight in kg. This
		information is required to estimate the shipping costs.
		"""
		return 0
