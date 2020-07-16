from functools import reduce
import operator

# external
from django.db import models


class ProductManager(models.Manager):
	"""
	ModelManager for searching products
	"""
	def from_store(self, request):
		"""
		Use this to limit objects to those associated with the current store
		`Product.objects.from_store(request).filter(name='name')`
		"""
		from shop.models.store import Store  # declared inside to avoid circular

		queryset = \
			self.get_queryset().filter(store=Store.objects.get_current(request))
		return queryset

	def select_lookup(self, search_term):
		"""
		Returning a queryset containing the products matching the declared lookup
		fields together with the given search term provided by user or view.
		Each product subclass can define its own lookup fields using the member
		list or tuple `lookup_fields`.
		"""
		filter_by_term = \
			(models.Q((sf, search_term)) for sf in self.model.lookup_fields)
		queryset = \
			self.get_queryset().filter(reduce(operator.or_, filter_by_term))
		return queryset

	def indexable(self):
		"""
		Return a queryset of indexable Products.
		"""
		queryset = self.get_queryset().filter(active=True)
		return queryset