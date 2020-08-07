import string

# external
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_delete, pre_save
from django.utils.translation import gettext_lazy as _

# internal
from shared.fields import JSONField
from shop.models.managers.store import StoreManager, STORE_CACHE


def _simple_domain_name_validator(value):
	"""
	Validate that the given value contains no whitespaces to prevent common
	typos.
	"""
	checks = ((s in value) for s in string.whitespace)
	if any(checks):
		raise ValidationError(
			_("The domain name cannot contain any spaces or tabs."),
			code='invalid',
		)


class Store(models.Model):

	domain = models.CharField(
		_('domain name'),
		max_length=100,
		validators=[_simple_domain_name_validator],
		help_text=_("Domain name 'example.com'."),
		unique=True,
	)

	name = models.CharField(
		_('display name'),
		help_text=_("Human readable store name."),
		max_length=50
	)

	slug = models.SlugField(
		_('slug name'),
		help_text=_("Used internally to identify templates to use."),
		unique=True,
	)

	bucket_name = models.CharField(
		max_length=255,
		help_text=_("Google bucket name")
	)

	email = models.CharField(
		max_length=255,
		help_text=_("The store's admin e-mail. Used in 'Contact-us'.")
	)

	address = models.TextField(
		verbose_name=_("Store Address"),
		help_text=_("The physical address of the store. Used in desktop version."),
	)

	vendor_name = models.CharField(
		_("Vendor's Name"),
		max_length=50,
	)

	vendor_email = models.CharField(
		_("Vendor's eMail"),
		max_length=255,
	)

	vendor_extra = JSONField(
		verbose_name=_("Extra Vendor Details"),
		blank=True,
		null=True,
		help_text=_("API details and more."),
	)

	meta_title = models.CharField(
		_("Meta Title"),
		max_length=255,
		help_text=_("Default title to use for pages without a title.")
	)

	meta_description = models.TextField(
		verbose_name=_("Meta Description"),
		help_text=_("Default page meta tag description."),
	)

	meta_keywords = models.TextField(
		verbose_name=_("Meta Ketwords"),
		help_text=_("Default page meta tag keywords."),
	)

	currency_code = models.CharField(
		_("Currency Code"),
		max_length=255,
		default='USD',
		help_text=_("Currency code to use for this store.")
	)

	has_filter = models.BooleanField(
		_("Has Filter"),
		default=False,
		help_text=_("Should the front-end try to provide an option to filter "
					"products for the customer."),
	)

	cart_modifiers = JSONField(
		verbose_name=_("Default Cart Modifiers"),
		blank=True,
		null=True,
		help_text=_('''Path to default cart modifiers to use for this store. Eg. 
		{
			"data": [
				"payment.modifiers.PaypalModifier",
				"payment.modifiers.StripeModifier",
				"payment.modifiers.MerchantModifier"
			]
		}
		'''),
	)

	order_workflow = JSONField(
		verbose_name=_("Order Workflow Mixins"),
		blank=True,
		null=True,
		help_text=_('''Path to workflow modifiers to use for this store. Eg. 
		{
			"data": [
				"payment.modifiers.PaypalModifier",
				"payment.modifiers.StripeModifier",
				"payment.modifiers.MerchantModifier"
			]
		}
		'''),
	)

	google_analytics = models.TextField(
		verbose_name=_("Google Analytics"),
		blank=True,
		null=True,
		help_text=_("Google analytics code snippet to inject."),
	)

	facebook_analytics = models.TextField(
		verbose_name=_("Facebook Analytics"),
		blank=True,
		null=True,
		help_text=_("Facebook analytics code snippet to inject."),
	)

	addthis_analytics = models.TextField(
		verbose_name=_("AddThis Analytics"),
		blank=True,
		null=True,
		help_text=_("AddThis analytics code snippet to inject."),
	)

	created_at = models.DateTimeField(
		_("Created at"),
		auto_now_add=True,
	)

	updated_at = models.DateTimeField(
		_("Updated at"),
		auto_now=True,
	)

	objects = StoreManager()

	class Meta:
		app_label = 'shop'
		verbose_name = _("Store")
		verbose_name_plural = _("Stores")

	def __str__(self):
		return self.domain

	@property
	def single_product(self):
		if self.num_products > 1:
			return False
		return True

	@property
	def num_products(self):
		from shop.models.product import Product
		return Product.objects.filter(store=self).count()

	def get_cart_modifiers(self):
		json = self.cart_modifiers
		if 'data' in json:
			return [modifier for modifier in json['data']]
		else:
			return []

	# def get_payment_modifiers(self):
	# 	json = self.payment_modifiers
	# 	if 'data' in json:
	# 		return [modifier for modifier in json['data']]
	# 	else:
	# 		return []

	# def get_shipping_modifiers(self):
	# 	json = self.shipping_modifiers
	# 	if 'data' in json:
	# 		return [modifier for modifier in json['data']]
	# 	else:
	# 		return []

	def get_workflows(self):
		json = self.order_workflow
		if 'data' in json:
			return [modifier for modifier in json['data']]
		else:
			return []


################################################################################
# Site Cache Management -- Signals


def clear_site_cache(sender, **kwargs):
	"""
	Clear the cache (if primed) each time a site is saved or deleted.
	"""
	instance = kwargs['instance']
	try:
		del STORE_CACHE[instance.domain]
	except KeyError:
		pass


pre_save.connect(clear_site_cache, sender=Store)
pre_delete.connect(clear_site_cache, sender=Store)
