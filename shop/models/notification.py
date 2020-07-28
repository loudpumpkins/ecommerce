# external
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from filer.fields.file import FilerFileField


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


class NotificationAttachment(models.Model):
	notification = models.ForeignKey(
		Notification,
		on_delete=models.CASCADE,
	)

	attachment = FilerFileField(
		on_delete=models.SET_NULL,
		related_name='email_attachment',
		null=True,
		blank=True,
	)

	class Meta:
		app_label = 'shop'
