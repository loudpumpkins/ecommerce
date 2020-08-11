# external
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

# internal


def get_image_filename(instance, filename):
	product = instance.product
	store = product.store
	return "%s/products/%s/%s" % (store.slug, product.slug, filename)


class ProductImage(models.Model):
	product = models.ForeignKey(
		'shop.Product',
		default=None,
		on_delete=models.CASCADE,
		related_name='images'
	)

	image = models.ImageField(
		upload_to=get_image_filename,
		verbose_name='Images'
	)

	order = models.SmallIntegerField(default=0)

	class Meta:
		app_label = 'shop'
		ordering = ('order',)
		verbose_name = _("Product Image")
		verbose_name_plural = _("Product Images")


@receiver(post_delete, sender=ProductImage)
def submission_delete(sender, instance, **kwargs):
	"""
	Delete all image files from media when a product is deleted.

	instance.image – ensures that only the current file is affected.

	Passing “false” to instance.image.delete ensures that ImageField does
	not save the model.

	Unlike pre_delete, post_delete signal is sent at the end of a model’s
	delete() method and a queryset’s delete() method. This is safer as it does
	not execute unless the parent object is successfully deleted.
	"""
	instance.image.delete(False)
