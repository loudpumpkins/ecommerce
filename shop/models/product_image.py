from filer.fields import image

# external
from django.db import models
from django.utils.translation import gettext_lazy as _

# internal


class ProductImage(models.Model):
	"""
	ManyToMany relation from the Product to a set of images.
	"""
	image = image.FilerImageField(on_delete=models.CASCADE)

	product = models.ForeignKey(
		'Product',
		on_delete=models.CASCADE,
	)

	order = models.SmallIntegerField(default=0)

	class Meta:
		app_label = 'shop'
		db_table = 'shop'
		verbose_name = _("Product Image")
		verbose_name_plural = _("Product Images")
		ordering = ['order']


# from django.dispatch import receiver
# from django.db.models.signals import post_delete
#
# def get_image_filename(instance, filename):
# 	store = instance
# 	return "post_images/%s/%s" % (post_id, filename)
#
#
# class ProductImage(models.Model):
# 	product = models.ForeignKey(
# 		Product,
# 		default=None,
# 		on_delete=models.CASCADE,
# 		related_name='product_image'
# 	)
#
# 	image = models.ImageField(
# 		upload_to=get_image_filename,
# 		verbose_name='Images'
# 	)
#
# 	class Meta:
# 		app_label = 'shop'
# 		db_table = 'shop'
# 		ordering = ('order',)
# 		verbose_name = _("Product Image")
# 		verbose_name_plural = _("Product Images")
#
#
# @receiver(post_delete, sender=ProductImage)
# def submission_delete(sender, instance, **kwargs):
# 	"""
# 	Delete all image files from media when a product is deleted.
#
# 	instance.image – ensures that only the current file is affected.
#
# 	Passing “false” to instance.image.delete ensures that ImageField does
# 	not save the model.
#
# 	Unlike pre_delete, post_delete signal is sent at the end of a model’s
# 	delete() method and a queryset’s delete() method. This is safer as it does
# 	not execute unless the parent object is successfully deleted.
# 	"""
# 	instance.image.delete(False)
