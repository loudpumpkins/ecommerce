import os
import logging
from urllib.parse import urlsplit

# external
from django.db import models
from django.http.response import HttpResponseRedirect
from django.http.request import QueryDict
from django.shortcuts import get_object_or_404
from django.utils.cache import add_never_cache_headers
from django.utils.encoding import force_str

from rest_framework import generics, pagination, status, views
from rest_framework.renderers import BrowsableAPIRenderer, TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param

# internal
from shared.rest_renderers import HTMLRenderer, JSONRenderer
from shop.models import Product, Store
from shop.serializers import AddToCartSerializer
from shop.serializers import ProductSerializer, ProductSummarySerializer

################################################################################
# shop.views.product.py -- Support

logger = logging.getLogger(__name__)


class ProductListPagination(pagination.LimitOffsetPagination):
	"""
	If the catalog's list is rendered with manual pagination, typically we want
	to render all rows without "widow" items (single items spawning a new row).
	By using a limit of 16 items per page, we can render 2 and 4 columns without
	problem, however whenever we need 3 or 5 columns, there is one widow item,
	which breaks the layout. This pagination class will prevent this problem.
	Add to ``ProductListView``. It behaves so that the last product items of a
	page, reappear on the next page. The number of reappearing items can be
	modified by changing ``overlapping``.

	By virtue, the rendering view can not know the current media breakpoint, and
	hence the number of columns. Therefore simply hide (with ``display: none;``)
	potential widow items. Exp:

	.shop-catalog-list {
		@include media-breakpoint-only(md) {
			.shop-list-item:nth-child(n+15):nth-last-child(1) {
				display: none;
			}
		}
		@include media-breakpoint-only(xl) {
			.shop-list-item:nth-child(n+15):nth-last-child(1) {
				display: none;
			}
		}
	}

	Since the last product items overlap with the first ones on the next page,
	no items are lost.
	This allows us to switch between layouts with different number of columns,
	keeping the last row of each page in balance.
	"""
	template = 'shop/templatetags/paginator.html'
	default_limit = 16
	overlapping = 1

	def adjust_offset(self, url, page_offset):
		if url is None:
			return
		(scheme, netloc, path, query, fragment) = urlsplit(force_str(url))
		query_dict = QueryDict(query)
		try:
			offset = pagination._positive_int(
				query_dict[self.offset_query_param],
			)
		except (KeyError, ValueError):
			pass
		else:
			if offset > page_offset:
				url = replace_query_param(url, self.offset_query_param,
				                          max(0, offset - self.overlapping))
			elif offset < page_offset:
				url = replace_query_param(url, self.offset_query_param,
				                          offset + self.overlapping)
		return url

	def get_html_context(self):
		context = super().get_html_context()
		page_offset = self.get_offset(self.request)
		context['previous_url'] = self.adjust_offset(context['previous_url'], page_offset)
		context['next_url'] = self.adjust_offset(context['next_url'], page_offset)
		for k, pl in enumerate(context['page_links']):
			url = self.adjust_offset(pl.url, page_offset)
			page_link = pagination.PageLink(url=url, number=pl.number,
			                                is_active=pl.is_active, is_break=pl.is_break)
			context['page_links'][k] = page_link
		return context


################################################################################
# shop.views.product.py -- Views


class AddToCartView(views.APIView):
	"""
	Handle the "Add to Cart" DIALOG on the products detail page.

	POST and GET are essentially the same, except that GET assumes a quantity of
	1 and POST requires user to send the requested quantity.

	Will responded with the min(requested, available, allowed) quantity, subtotal,
	availability details and more minor details.

	:return exp
	{
		'quantity': 2,
		'unit_price': '€ 509.00',
		'product': 4,
		'product_code': 'sh-hd630vb',
		'extra': {},
		'is_in_cart': False,
		'availability': {
			'earliest': '0001-01-01T00:00:00Z',
			'latest': '9999-12-31T23:59:59.999999Z',
			'quantity': 5,
			'sell_short': False,
			'limited_offer': False
		},
		'subtotal': '€ 1,018.00'
	}
	"""
	renderer_classes = (JSONRenderer, BrowsableAPIRenderer)
	product_model = Product
	serializer_class = AddToCartSerializer
	lookup_field = lookup_url_kwarg = 'slug'
	limit_choices_to = models.Q()

	def get_context(self, request, **kwargs):
		assert self.lookup_url_kwarg in kwargs
		filter_kwargs = {
			self.lookup_field: kwargs.pop(self.lookup_url_kwarg),
			'store': request.store,
		}
		queryset = self.product_model.objects.filter(
									self.limit_choices_to, **filter_kwargs)
		product = get_object_or_404(queryset)
		return {'product': product, 'request': request}

	def get(self, request, *args, **kwargs):
		context = self.get_context(request, **kwargs)
		serializer = self.serializer_class(context=context, **kwargs)
		return Response(serializer.data)

	def post(self, request, *args, **kwargs):
		context = self.get_context(request, **kwargs)
		serializer = self.serializer_class(data=request.data, context=context)
		if serializer.is_valid():
			return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductListView(generics.ListAPIView):
	"""
	This view is used to list all products which shall be visible below a certain
	URL.
	```
	urlpatterns = [
		...
		path('', ProductListView.as_view(**params)),  # see **params below
		...
	]
	```
	These attributes can be added to the ``as_view(**params)`` method:

	:param `renderer_classes`: A list or tuple of REST renderer classes.

	:param `product_model`: The product model onto which the filter set is applied.

	:param `serializer_class`: The serializer class used to process the queryset
		returned by the catalog's product list view.

	:param `limit_choices_to`: Limit the queryset of product models to these
		choices.

	:param `filter_class`: A filter set which must be inherit from
		:class:`django_filters.FilterSet`.

	:param `pagination_class`: A pagination class inheriting from
		:class:`rest_framework.pagination.BasePagination`.

	:param `context_data_name`: When using HTML rendering, the serialised data
		can be accessed through 'context_data_name'.
		eg: if 'context_data_name' = 'data', use: {{ data.field1 }}
	"""
	renderer_classes = (HTMLRenderer, JSONRenderer, BrowsableAPIRenderer)
	product_model = Product
	serializer_class = ProductSummarySerializer
	limit_choices_to = models.Q()
	filter_class = None
	pagination_class = ProductListPagination
	context_data_name = 'products'

	def get(self, request, *args, **kwargs):
		if self.get_queryset().count() == 1:
			# if store has only one product, redirect to that product
			redirect_to = self.get_queryset().first().get_absolute_url()
			return HttpResponseRedirect(redirect_to)

		response = self.list(request, *args, **kwargs)
		# TODO: find a better way to invalidate the cache.
		# Simply adding a no-cache header eventually decreases the performance
		# dramatically.
		add_never_cache_headers(response)
		return response

	def get_template_names(self):
		# if a store needs custom HTML, make a new template named :
		# product-list-{domain slug}.html
		return [
			'shop/catalog/product-list-%s.html' % self.request.store.slug,
			'shop/catalog/product-list.html',
		]

	def get_renderer_context(self):
		# used in `HTMLRenderer` to append all none 'view', 'args', 'kwargs'
		# and 'request' to the template context
		renderer_context = super().get_renderer_context()
		if renderer_context['request'].accepted_renderer.format == 'html':
			renderer_context.update(
				paginator=self.paginator,
			)
		return renderer_context

	def get_queryset(self):
		qs = self.product_model.objects.filter(
				self.limit_choices_to, active=True, store=self.request.store)
		return qs


class ProductRetrieveView(generics.RetrieveAPIView):
	"""
	This view is used to retrieve and render a certain product.
	```
	urlpatterns = [
		...
		path('<slug:slug>/', ProductRetrieveView.as_view(**params)), # params below
		...
	]
	```
	These attributes can be added to the ``as_view(**params)`` method:

	:param `renderer_classes`: A list or tuple of REST renderer classes.

	:param `lookup_field`: The model field used to retrieve the product instance.

	:param `lookup_url_kwarg`: The name of the parsed URL fragment.

	:param `serializer_class`: The serializer class used to process the queryset
		returned by the catalog's product detail view.

	:param `limit_choices_to`: Limit the queryset of product models to these
		choices.

	:param `context_data_name`: When using HTML rendering, the serialised data
		can be accessed through 'context_data_name'.
		eg: if ` context_data_name = 'data' `, use: {{ data.field1 }}
	"""

	renderer_classes = (HTMLRenderer, JSONRenderer, BrowsableAPIRenderer)
	lookup_field = lookup_url_kwarg = 'slug'
	product_model = Product
	serializer_class = ProductSerializer
	limit_choices_to = models.Q()
	context_data_name = 'product'

	def get_template_names(self):
		# if a product needs custom HTML, make a new template named :
		# product-detail-{domain slug}-{product slug}.html
		# if a store needs custom product HTML, make a new template named
		# product-detail-{domain slug}.html
		product = self.get_object()
		return [
			'shop/catalog/product-detail-%s-%s.html' % (self.request.store.slug,
			                                            product.slug),
			'shop/catalog/product-detail-%s.html' % self.request.store.slug,
			'shop/catalog/product-detail.html',
		]

	def get_object(self):
		if not hasattr(self, '_product'):
			assert self.lookup_url_kwarg in self.kwargs
			filter_kwargs = {
				'active': True,
				'store': self.request.store,
				self.lookup_field: self.kwargs[self.lookup_url_kwarg],
			}
			queryset = self.product_model.objects.filter(
				self.limit_choices_to, **filter_kwargs)
			self._product = get_object_or_404(queryset)  # cache product locally
		return self._product