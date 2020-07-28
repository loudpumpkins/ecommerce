# external
from django.contrib import admin

# internal
from shop.admin.delivery import DeliveryOrderAdminMixin
from shop.admin.notification import NotificationAdmin
from shop.admin.order import PrintInvoiceAdminMixin, BaseOrderAdmin
from shop.admin.product import ProductAdmin
from shop.admin.store import StoreAdmin
from shop.models.notification import Notification
from shop.models.order import Order
from shop.models.product import Product
from shop.models.store import Store


admin.site.site_header = "e-Commerce API"


admin.site.register(Notification, NotificationAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Store, StoreAdmin)


@admin.register(Order)
class OrderAdmin(PrintInvoiceAdminMixin, DeliveryOrderAdminMixin, BaseOrderAdmin):
	pass
