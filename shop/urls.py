# external
from django.urls import path

# internal
from shop.views import ProductListView, ProductRetrieveView, AddToCartView

app_name = 'shop'
urlpatterns = [
	# views.order.py
	# views.product.py
	path('', ProductListView.as_view(), name='product-list'),
	path('<slug:slug>/', ProductRetrieveView.as_view(), name='product-detail'),
	path('<slug:slug>/add-to-cart/', AddToCartView.as_view()),
]
