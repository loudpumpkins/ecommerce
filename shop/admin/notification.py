from collections import OrderedDict

# external
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.forms import fields, models, widgets
from django.utils.translation import gettext_lazy as _

# internal
from fsm import RETURN_VALUE
from shop.models.notification import Notification, NotificationAttachment
from shop.models import Order


class NotificationAttachmentAdmin(admin.TabularInline):
    """
    Inline attachment add-on
    """
    model = NotificationAttachment
    extra = 0


class NotificationForm(models.ModelForm):
    notify_recipient = fields.ChoiceField(label=_("Recipient"))

    class Meta:
        model = Notification
        exclude = ['notify', 'recipient']
        widgets = {
            'transition_target': widgets.Select(),
            'notify_recipient': widgets.Select(),
        }

    def __init__(self, *args, **kwargs):
        if kwargs.get('instance'):
            initial = kwargs.get('initial', {})
            if kwargs['instance'].notify == Notification.Notify.RECIPIENT.value:
                initial['notify_recipient'] = kwargs['instance'].recipient_id
            else:
                initial['notify_recipient'] = kwargs['instance'].notify
            kwargs.update(initial=initial)
        super().__init__(*args, **kwargs)
        self.fields['transition_target'].widget.choices = \
                                                self.get_transition_choices()
        self.fields['notify_recipient'].choices = self.get_recipient_choices()

    def get_transition_choices(self):
        choices = OrderedDict()
        for transition in Order.get_all_transitions():
            if isinstance(transition.target, str):
                choices[transition.target] = \
                    Order.get_transition_name(transition.target)
            elif isinstance(transition.target, RETURN_VALUE):
                for target in transition.target.allowed_states:
                    choices[target] = Order.get_transition_name(target)
        return choices.items()

    def get_recipient_choices(self):
        """
        Instead of offering one field for the recipient and one for whom to
        notify, we merge staff users with the context dependent recipients.
        """
        choices = [(membr.value, membr.label) for membr in Notification.Notify
                   if membr is not Notification.Notify.RECIPIENT]
        for user in get_user_model().objects.filter(is_staff=True):
            email = '{0} <{1}>'.format(user.get_full_name(), user.email)
            choices.append((user.id, email))
        return choices

    def save(self, commit=True):
        obj = super().save(commit=commit)
        #  self.cleaned_data['notify_recipient'] eg: 'vendor' or '11' for a user
        try:
            obj.recipient = get_user_model().objects.get(
                                    pk=self.cleaned_data['notify_recipient'])
            obj.notify = Notification.Notify.RECIPIENT
        except (ValueError, get_user_model().DoesNotExist):
            obj.recipient = None
            obj.notify = self.cleaned_data['notify_recipient']
        return obj


# @admin.register(Notification)  # registered in __init__.py
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['name', 'transition_name', 'get_recipient', 'mail_template',
                    'num_attachments']
    inlines = (NotificationAttachmentAdmin,)
    form = NotificationForm
    save_as = True

    def transition_name(self, obj):
        return Order.get_transition_name(obj.transition_target)
    transition_name.short_description = _("Event")

    def num_attachments(self, obj):
        return obj.notificationattachment_set.count()
    num_attachments.short_description = _("Attachments")

    def get_recipient(self, obj):
        if obj.notify == Notification.Notify.RECIPIENT.value:
            return '{0} <{1}>'.format(obj.recipient.get_full_name(),
                                      obj.recipient.email)
        else:
            return str(obj.notify)
    get_recipient.short_description = _("Mail Recipient")
