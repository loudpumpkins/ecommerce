# external
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

# internal
from shop.models import Product, ProductImage


class ProductImageInline(admin.StackedInline):
    """Product Images addition to Products"""
    model = ProductImage
    extra = 1
    ordering = ['order']


# @admin.register(Product)  # registered in __init__.py
class ProductAdmin(admin.ModelAdmin):
    base_model = Product
    list_display = ['product_name', 'product_code', 'get_price',
                    'get_store_name', 'active']
    list_display_links = ['product_name']
    list_filter = ['store__domain', 'active']
    list_per_page = 250
    list_max_show_all = 1000
    search_fields = ['product_name']
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': [
                ('product_name', 'slug'),
                ('product_code', 'unit_price'),
                ('quantity', 'active', 'order'),
                ('store', ),
            ],
        }),
        (_("Text Fields"), {
            'fields': ['caption', 'description'],
        }),
        (_("Meta Fields"), {
            'fields': ['meta_keywords', 'meta_description'],
        }),
        (_("JSON Field"), {
            'fields': ['extra'],
        }),
        (_("Dates"), {
            'fields': ['created_at', 'updated_at'],
        }),
    )
    inlines = [ProductImageInline]
    prepopulated_fields = {'slug': ['product_name', 'product_code']}

    def get_price(self, obj):
        return str(obj.get_price(None))
    get_price.short_description = _("Price")

    def get_store_name(self, obj):
        return obj.store.name
    get_store_name.short_description = _("Store")
