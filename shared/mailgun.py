import json
import requests
import string

from email.utils import parseaddr

# external
from django.conf import settings

requests.post(
				settings.MAILGUN_API_URL + '/messages',
				auth=("api", settings.MAILGUN_API),
				data={"from": "Support <support@adposter.run>",
					  "to": user.email,
					  "o:require-tls": True,
					  "subject": "Ad Poster | Please activate your account.",
					  "template": "activation",
					  "h:X-Mailgun-Variables": json.dumps({
						  "href": "https://%s%s" % (current_site.domain, reverse_lazy("accounts:activation", kwargs={'pk': user.id,'activation_code': user.activation_code})),
					  })
				  })

requests.post(
			settings.MAILGUN_API_URL + '/messages',
			auth=("api", settings.MAILGUN_API),
			data={"from": "Support <support@adposter.run>",
				  "to": user.email,
				  "o:require-tls": True,
				  "subject": "Ad Poster | An invoice was generated.",
				  "template": "invoice",
				  "h:X-Mailgun-Variables": json.dumps({
					  "total": payment_amount,
					  "email": kij_account.username,
					  "invoice": ipn.invoice,
					  "plan": ipn.item_name,
					  "date": str(date.today()),
				  })
			  })

requests.post(
			MAILGUN_API_URL + '/messages',
			auth=("api", MAILGUN_API),
			files=[("attachment",("error.jpg", open(ad_setup['screenshot'], "rb").read() )),],
			data={"from": "System <system@adposter.run>",
				  "to": ["support@adposter.run", ad_setup['username']],
				  "o:require-tls": True,
				  "subject": "Ad Poster | An error occurred while attempting to post your ad.",
				  "template": "error",
				  "h:X-Mailgun-Variables": json.dumps({
					  "message": "Please see the attached picture of the error for more information.",
					  "exception": ad_setup['exception'],
					  "post_id": post_id,
				  })
			})


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
	:return:
	"""
	data = {'to': to}
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
