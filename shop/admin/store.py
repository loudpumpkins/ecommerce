# external
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

# internal
from shop.models.store import Store
from shop.models.product import Product


# @admin.register(Store)  # registered in __init__.py
class StoreAdmin(admin.ModelAdmin):
	base_model = Store
	list_display = ['domain', 'name', 'bucket_name', 'get_num_products']
	list_display_links = ['domain']
	list_per_page = 250
	list_max_show_all = 1000
	search_fields = ['domain']
	readonly_fields = ('created_at', 'updated_at')

	fieldsets = (
		(None, {
			'fields': [
				('domain', 'name', 'slug'),
				('bucket_name', 'currency_code', 'has_filter'),
			],
		}),
		(_("Vendor"), {
			'fields': [
				('vendor_name', 'vendor_email'),
				'vendor_extra',
			],
		}),
		(_("Meta Data"), {
			'fields': [
				('email', 'address'),
				'meta_title',
				'meta_description',
				'meta_keywords'
			],
		}),
		(_("Thumbnail options"), {
			'description': "easy_thumbnail options as a string dictionary.<br> "
			               "Or set to 'None' (or leave blank) to use original image.",
			'fields': [
				'cart_thumbnail_options',
				'catalog_thumbnail_options',
				'email_thumbnail_options',
				'order_thumbnail_options',
				'print_thumbnail_options',
				'product_thumbnail_options',
				'watch_thumbnail_options',
			],
		}),
		(_("Analytics"), {
			'fields': [
				'google_analytics',
				'facebook_analytics',
				'addthis_analytics'
			],
		}),
		(_("Modifiers"), {
			'fields': ['cart_modifiers',],
		}),
		(_("Dates"), {
			'fields': ['created_at', 'updated_at'],
		}),
	)

	prepopulated_fields = {'slug': ['domain']}

	def get_num_products(self, obj):
		return Product.objects.filter(store=obj).count()
	get_num_products.short_description = _("Products")
