# external
from django.db import models
from django.utils.translation import gettext_lazy as _

# internal


class Store(models.Model):
	pass

	class Meta:
		app_label = 'shop'
		db_table = 'shop'
		unique_together = [('store', 'master')]
		ordering = ('order',)
		verbose_name = _("Product")
		verbose_name_plural = _("Products")
