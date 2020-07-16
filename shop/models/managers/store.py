# external
from django.db import models
from django.http.request import split_domain_port

# internal


STORE_CACHE = {}


class StoreManager(models.Manager):
	"""
	Get store details based on request's domain name.
	Usage `Products.objects.filter(store=Store.objects.get_current(request)`
	"""
	def get_current(self, request):
		host = request.get_host()
		try:
			# First attempt to look up the site by host with or without port.
			if host not in STORE_CACHE:
				STORE_CACHE[host] = self.get(domain__iexact=host)
			return STORE_CACHE[host]
		except:
			# Fallback to looking up site after stripping port from the host.
			domain, port = split_domain_port(host)
			if domain not in STORE_CACHE:
				STORE_CACHE[domain] = self.get(domain__iexact=domain)
			return STORE_CACHE[domain]

	def clear_cache(self):
		"""
		Clear the ``Store`` object cache.
		"""
		global STORE_CACHE
		STORE_CACHE = {}
