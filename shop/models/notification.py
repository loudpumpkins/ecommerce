# external
from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
	"""
	Notify vendor/staff/customer with a custom email upon an event occurring such
	as an order status change or new user registration.

	example usage:

	notifications = Notification.objects.filter(
		transition_target=order.status, store=order.store
	)
	for notification in notifications:
		* send email with context *
	"""
	class Notify(models.TextChoices):
		RECIPIENT = "recipient", _("Recipient")
		VENDOR = "vendor", _("Vendor")
		CUSTOMER = "customer", _("Customer")
		NOBODY = "nobody", _("Nobody")

	class MailTemplate(models.TextChoices):
		WELCOME = "welcome", _("Welcome")

	store = models.ForeignKey(
		'shop.Store',
		on_delete=models.CASCADE,
		verbose_name=_("Store"),
	)

	name = models.CharField(
		max_length=50,
		verbose_name=_("Name"),
	)

	transition_target = models.CharField(
		max_length=50,
		verbose_name=_("Event"),
	)

	notify = models.CharField(
		_("Whom to notify"),
		max_length=20,
		choices=Notify.choices,
	)

	recipient = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		verbose_name=_("Recipient / Staff"),
		null=True,
		limit_choices_to={'is_staff': True},
	)

	mail_template = models.CharField(
		_("Template to use"),
		max_length=20,
		choices=MailTemplate.choices,
	)

	class Meta:
		app_label = 'shop'
		verbose_name = _("Notification")
		verbose_name_plural = _("Notifications")
		ordering = ['store', 'transition_target', 'recipient_id']

	def __str__(self):
		return self.name

	def get_recipient(self, order):
		if self.notify is self.Notify.RECIPIENT:
			return self.recipient.email
		if self.notify is self.Notify.CUSTOMER:
			return order.customer.email
		if self.notify is self.Notify.VENDOR:
			return order.store.vendor_email


def get_file_filename(instance, filename):
	store_slug = instance.store.slug
	return "%s/notifications/attachments/%s" % (store_slug, filename)


class NotificationAttachment(models.Model):
	notification = models.ForeignKey(
		Notification,
		on_delete=models.CASCADE,
		related_name='attachments'
	)

	attachment = models.FileField(
		upload_to=get_file_filename,
		verbose_name='Attachments',
		null=True,
		blank=True,
	)

	class Meta:
		app_label = 'shop'


@receiver(post_delete, sender=NotificationAttachment)
def submission_delete(sender, instance, **kwargs):
	"""
	Delete attachment files from media when a notification is deleted.
	"""
	instance.image.delete(False)