# external
from django.db import models
from django.utils.translation import gettext_lazy as _


# internal
from shop.models.product import Product


class Store(models.Model):
	url = models.CharField(
		max_length=255,
		unique=True,
		help_text=_("Hostname with domain. 'https://example.com'")
	)

	bucket_name = models.CharField(
		max_length=255,
		help_text=_("Google bucket name")
	)

	name = models.CharField(
		max_length=255,
		help_text=_("The store's name")
	)

	email = models.CharField(
		max_length=255,
		help_text=_("The store's admin e-mail. Used in 'Contact-us'")
	)

	address = models.TextField(
		verbose_name=_("Store Address"),
		help_text=_("The physical address of the store. Used in desktop version."),
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

	cart_modifiers = models.TextField(
		verbose_name=_("Default Cart Modifiers"),
		blank=True,
		null=True,
		help_text=_("Path to default cart modifiers to use for this store. "
					"Delimated by newline.\n"
					"'shop_modifiers.DefaultCartModifier'"),
	)

	payment_modifiers = models.TextField(
		verbose_name=_("Payment Cart Modifiers"),
		blank=True,
		null=True,
		help_text=_("Path to payment cart modifiers to use for this store. "
					"Delimated by newline.\n"
					"'shop.paypal.modifiers.PaymentModifier'\n"
					"'shop.modifiers.StripePaymentModifier'"),
	)

	shipping_modifiers = models.TextField(
		verbose_name=_("Shipping Cart Modifiers"),
		blank=True,
		null=True,
		help_text=_("Path to shipping cart modifiers to use for this store. "
					"Delimated by newline.\n"
					"'shop.paypal.modifiers.PaymentModifier'\n"
					"'shop.modifiers.StripePaymentModifier'"),
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

	class Meta:
		app_label = 'shop'
		db_table = 'shop'
		verbose_name = _("Store")
		verbose_name_plural = _("Stores")

	@property
	def single_product(self):
		if self.num_products > 1:
			return False
		return True

	@property
	def num_products(self):
		return Product.objects.filter(store=self).count()
