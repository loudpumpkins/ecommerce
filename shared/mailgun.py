import json
import requests
import string

from email.utils import parseaddr

# external
from django.conf import settings

# internal
from shop.models import Notification


def format_sender(sender):
	"""
	Light email format. Turns 'name@example.com' -> 'Name <name@example.com>'
	"""
	name, email = parseaddr(sender)
	if ' ' in email:
		split_email = email.split(' ')
		email = split_email[-1]
		if name:
			name += ' '
		name += ' '.join(split_email[:-1])
	if not name:
		name = email.split('@')[0]
	return "{} <{}>".format(string.capwords(name), email)


def send_mail(to, cc=None, bcc=None, sender=None, subject=None, text=None,
			  html=None, template=None, context=None, files=None):
	"""
	Send email using mailgun services.
	Settings file must declare `MAILGUN_API_URL` and `MAILGUN_API`

	`context` keys limited to:
		'customer' -> customer serializer data
		'order' -> order detail derializer data
		'store' -> store serializer data
		'ABSOLUTE_BASE_URI' -> absolute uri
		'render_language' -> language (for future use)

	:param to: list | str - ['name@example.com', 'name@example2.com']
	:param cc: str
	:param bcc: str
	:param sender: str - 'admin@web.com' | 'Admin <admin@web.com>'
	:param subject: str
	:param text: str - content of email
	:param html: str - '<html>HTML version of the body</html>'
	:param template: str - template name
	:param context: dict - template variables - dict must be JSON convertible
	:param files: dict - { 'filename' : 'fieldfield.file.file' }
	:return -> NoReturn:
	"""
	data = {'to': to, 'o:require-tls': True}
	if cc is not None:
		data['cc'] = cc
	if bcc is not None:
		data['bcc'] = bcc
	if sender is not None:
		data['from'] = format_sender(sender)
	else:
		data['from'] = format_sender(settings.MASTER_EMAIL)
	if subject is not None:
		data['subject'] = subject
	if text is not None:
		data['text'] = text
	if html is not None:
		data['html'] = html
	if template is not None:
		assert template in Notification.MailTemplate.values, \
			"{} is not a known template".format(template)
		data['template'] = template
	if context is not None:
		# template variables
		data['h:X-Mailgun-Variables'] = json.dumps(context)
	if files is not None:
		files = [('attachment', (name, content)) for name, content in files.items()]
	else:
		files = []

	requests.post(
		settings.MAILGUN_API_URL + '/messages',
		auth=("api", settings.MAILGUN_API),
		files=files,
		data=data,
	)
