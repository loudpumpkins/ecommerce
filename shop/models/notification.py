# external
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from filer.fields.file import FilerFileField

# internal
from shared.fields import ChoiceEnum, ChoiceEnumField


class Notify(ChoiceEnum):
	RECIPIENT = 0, _("Recipient")
	VENDOR = 1, _("Vendor")
	CUSTOMER = 2, _("Customer")
	NOBODY = 9, _("Nobody")


class MailTemplate(ChoiceEnum):
	WELCOME = 0, _("Welcome")


class Notification(models.Model):
	"""
	A task executed on receiving a signal.
	"""
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

	notify = ChoiceEnumField(
		_("Whom to notify"),
		enum_type=Notify,
	)

	recipient = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		verbose_name=_("Recipient / Staff"),
		null=True,
		limit_choices_to={'is_staff': True},
	)

	mail_template = ChoiceEnumField(
		_("Whom to notify"),
		enum_type=MailTemplate,
	)

	class Meta:
		app_label = 'shop'
		verbose_name = _("Notification")
		verbose_name_plural = _("Notifications")
		ordering = ['store', 'transition_target', 'recipient_id']

	def __str__(self):
		return self.name

	def get_recipient(self, order):
		if self.notify is Notify.RECIPIENT:
			return self.recipient.email
		if self.notify is Notify.CUSTOMER:
			return order.customer.email
		if self.notify is Notify.VENDOR:
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
