"""
Django settings for ecommerce project.

Generated by 'django-admin startproject' using Django 3.0.7.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
# \\Django\ecommerce\ecommerce
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Root directory for this django project
# \\Django\ecommerce
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, os.path.pardir))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '1g6q%!tyz4)9dye5*$0amaa(bqn9=i9+4p7^%220vjpo$$u@ae'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']
INTERNAL_IPS = ['127.0.0.1']  # for debug toolbar
SITE_ID = 1

# Application definition

INSTALLED_APPS = [

	# main
	'customer',
	'ecommerce',  # declared to load `custom commands`
	'fsm',
	'payment',
	'shop',

	# 3rd party
	'allauth',
	'allauth.account',
	'allauth.socialaccount',
	'allauth.socialaccount.providers.facebook',
	'allauth.socialaccount.providers.instagram',
	'easy_thumbnails',  # https://github.com/SmileyChris/easy-thumbnails
	'easy_thumbnails.optimize',
	'rest_framework',
	'rest_framework.authtoken',
	'dj_rest_auth',
	'dj_rest_auth.registration',

	# django
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.sites',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'debug_toolbar',
]

MIDDLEWARE = [
	'debug_toolbar.middleware.DebugToolbarMiddleware',
	'django.middleware.security.SecurityMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
	'shop.middleware.CustomerMiddleware',
	'shop.middleware.StoreMiddleware',
]

ROOT_URLCONF = 'ecommerce.urls'

TEMPLATES = [
	{
		'BACKEND': 'django.template.backends.django.DjangoTemplates',
		'DIRS': [],
		'APP_DIRS': True,
		'OPTIONS': {
			'context_processors': [
				'django.template.context_processors.debug',
				'django.template.context_processors.request',
				'django.contrib.auth.context_processors.auth',
				'django.contrib.messages.context_processors.messages',
				'shop.context_processors.add_customer',
				'shop.context_processors.add_cart',
				'shop.context_processors.add_store',
			],
		},
	},
]

AUTHENTICATION_BACKENDS = [
	# Needed to login by username in Django admin, regardless of `allauth`
	'django.contrib.auth.backends.ModelBackend',

	# `allauth` specific authentication methods, such as login by e-mail
	'allauth.account.auth_backends.AuthenticationBackend',
]

WSGI_APPLICATION = 'ecommerce.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.sqlite3',
		'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
	}
}


# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
	{
		'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
	},
]


# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = False  # no translation support

USE_L10N = True  # Datetime format to local

USE_TZ = True

# SESSIONS

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
# SESSION_SAVE_EVERY_REQUEST = True

################################################################################
# Logging

LOGGING = {
	'version': 1,
	'disable_existing_loggers': True,
	'loggers': {
		'customer': {
			'handlers': ['developer-console'],
			'level': 'DEBUG',
			'propagate': False,
		},
		'shop': {
			'handlers': ['developer-console'],
			'level': 'DEBUG',
			'propagate': False,
		},
		'django': {
			'handlers': ['console'],
			'level': 'INFO',
			'propagate': False,
		},
		# 'django.request': {
		# 	'handlers': ['file'],
		# 	'level': 'WARNING',  # HTTP 5XX = ERROR, 4XX = WARNING, rest = INFO
		# 	'propagate': True,  # let log record propagate to 'django' logger
		# },
	},
	'handlers': {
		'developer-console': {
			'level': 'DEBUG',
			'class': 'logging.StreamHandler',
			'formatter': 'colour',
		},
		'console': {
			'level': 'INFO',
			'class': 'logging.StreamHandler',
			'formatter': 'simple',
		},
		# 'file': {
		# 	'level': 'WARNING',
		# 	'class': 'logging.FileHandler',  # maybe set to 'socket'
		# 	'filename': '/log/debug.log',
		# 	'formatter': 'verbose',
		# },
	},
	'filters': {
		'require_debug_false': {
			'()': 'django.utils.log.RequireDebugFalse'
		}
	},
	'formatters': {
		'simple': {
			'format': '[%(asctime)s %(module)s] %(levelname)s: %(message)s'
		},
		'verbose': {
			'format': '[%(asctime)s] %(name)s::%(funcName)s::line %(lineno)d - '
					  '%(levelname)s - %(message)s'
		},
		'colour': {
			'()': 'ecommerce.settings.logger.DjangoColorsFormatter',  # colored output
			'format': '[%(asctime)s] %(name)s::%(funcName)s::line %(lineno)d - '
					  '%(levelname)s - %(message)s'
		}
	},


}

################################################################################
# STATIC / MEDIA

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

# Absolute path to the directory that holds static files for collectstatic.
# Example: "/home/path/to/app/static/"
# STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')

# Additional paths to look for static files.
STATICFILES_DIRS = [
	os.path.join(PROJECT_ROOT, 'static'),
]

# URL that handles the static files served from STATIC_ROOT.
# Example: "http://app.com/static/"
STATIC_URL = '/static/'

# Absolute path to the directory that holds media.
# Example: "/home/path/to/app/media/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://app.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

################################################################################
# REST FRAMEWORK / DJ REST AUTH / DJ ALL AUTH

REST_FRAMEWORK = {
	'DEFAULT_RENDERER_CLASSES': [
		'shared.rest_renderers.JSONRenderer',
		'rest_framework.renderers.BrowsableAPIRenderer',  # disable in production
	],
	# 'DEFAULT_FILTER_BACKENDS': [
	# 	'django_filters.rest_framework.DjangoFilterBackend',
	# ],
	# 'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
	# 'PAGE_SIZE': 16,
}

# https://dj-rest-auth.readthedocs.io/en/latest/configuration.html
REST_AUTH_SERIALIZERS = {
	# 'LOGIN_SERIALIZER': 'customer.serializers.LoginSerializer',
}

# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_ADAPTER = 'customer.adapter.ShopAccountAdapter'
ACCOUNT_AUTHENTICATION_METHOD = 'email'  # login with email address
ACCOUNT_EMAIL_REQUIRED = True  # registration requires email (T/F)
ACCOUNT_EMAIL_VERIFICATION = 'none'  # 'none', 'option', 'mandatory'

SOCIALACCOUNT_ADAPTER = 'customer.adapter.ShopSocialAccountAdapter'
SOCIALACCOUNT_PROVIDERS = {
	# https://django-allauth.readthedocs.io/en/latest/providers.html#facebook
	'facebook': {
		# 'SDK_URL': '//connect.facebook.net/{locale}/sdk.js',
		'SCOPE': ['email', 'public_profile'],
		# 'AUTH_PARAMS': {'auth_type': 'reauthenticate'},
		# 'INIT_PARAMS': {'cookie': True},
		'FIELDS': [
			'id',
            'email',
            'first_name',
            'last_name',
			# 'name',
            # 'verified',
            # 'locale',
            # 'timezone',
            # 'link',
            # 'gender',
            # 'updated_time',
			# 'middle_name',
			# 'name_format',
			# 'picture',
		],
		# 'EXCHANGE_TOKEN': True,
		# 'VERIFIED_EMAIL': False,  # unconfirmed if it's reliable
		'VERSION': 'v8.0',
	}
}

################################################################################
# GENERAL

MASTER_EMAIL = 'admin@watermelonsalad.com'
MAX_PURCHASE_QUANTITY = 50  # prevents a user from reserving entire stock
USE_THOUSAND_SEPARATOR = True
DEFAULT_CURRENCY = 'USD'  # only used if no currency is provided to field
DEFAULT_TAX_RATE = 13  # tax rate as an int

"""
When rendering an amount of type Money, use this format.
Possible placeholders are:
* ``{symbol}``: This is replaced by €, $, £, etc.
* ``{currency}``: This is replaced by Euro, US Dollar, Pound Sterling, etc.
* ``{code}``: This is replaced by EUR, USD, GBP, etc.
* ``{amount}``: The localized amount.
* ``{minus}``: Only for negative amounts, where to put the ``-`` sign.

For further information about formatting currency amounts, refer to
https://docs.microsoft.com/en-us/globalization/locale/currency-formatting
"""
MONEY_FORMAT = '{symbol} {minus}{amount}'  # eg.= '$ -2.00'


def GET_ORDER_WORKFLOWS():
	"""
	Specifies a list of `order-workflows`. Order workflows will inject
	`TRANSITION_TARGETS` into the order model's default finite state machine and
	the logic that allows the transitions. This prevents illegal order state
	transitions and gives a plugable way to add/remove payment/shipping methods.

	Returns a list classes [ '[..].Class1', '[..].Class2', ... ] dynamically
	imported by DJango
	"""
	from django.utils.module_loading import import_string

	order_workflows = [
		'payment.workflows.ManualPaymentWorkflowMixin',
		'payment.workflows.CancelOrderWorkflowMixin',
		'shipping.workflows.PartialDeliveryWorkflowMixin',
		# 'shop_paypal.payment.OrderWorkflowMixin',
		# 'shop_stripe.workflows.OrderWorkflowMixin',
	]
	return [import_string(wf) for wf in order_workflows]


################################################################################
# MAILGUN

MAILGUN_API = '51441d559c9261ae9585a1e95d119c26-65b08458-0d5cf2fb'
MAILGUN_API_URL = 'https://api.mailgun.net/v3/adposter.run'

################################################################################
# SMTP

# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.mailgun.org'
# EMAIL_HOST_USER = 'info@adposter.run'
# EMAIL_HOST_PASSWORD = 'be16********e-0afbfc6c-c3874ef0'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# DEFAULT_FROM_EMAIL = 'info@adposter.run'
# SERVER_EMAIL = 'info@adposter.run'

################################################################################
# THUMBNAIL - https://easy-thumbnails.readthedocs.io/en/latest/usage/

# FILER_ADMIN_ICON_SIZES = ('16', '32', '48', '80', '128')
# FILER_ALLOW_REGULAR_USERS_TO_ADD_ROOT_FOLDERS = True
# FILER_DUMP_PAYLOAD = False
# FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880
# THUMBNAIL_HIGH_RESOLUTION = False
# THUMBNAIL_PRESERVE_EXTENSIONS = True

THUMBNAIL_DEBUG = DEBUG

# https://easy-thumbnails.readthedocs.io/en/latest/ref/processors/
THUMBNAIL_PROCESSORS = (
	# 'easy_thumbnails.processors.colorspace',  # bw=False, replace_alpha=False
	# 'easy_thumbnails.processors.autocrop',  # autocrop=False
	'easy_thumbnails.processors.scale_and_crop',  # crop=F, upscale=F, zoom=None
	'easy_thumbnails.processors.filters',  # detail=False, sharpen=False
	'easy_thumbnails.processors.background',  # background=None - fill difference
)

# default thumbnail options for product images on the admin pages
THUMBNAIL_WIDGET_OPTIONS = {'size': (120, 120)}

# <img src="{{ model.image|thumbnail_url:'alias' }}" alt="">
# {% thumbnail [source] [alias] [options] as [variable] %}
# {% thumbnail [source] [alias] [options] %}
THUMBNAIL_ALIASES = {
	'': {
		'small': {
			'size': (100, 100), 'background': 'white', 'quality': 50,
		},
		'medium': {
			'size': (200, 200), 'background': 'white', 'sharpen': True,
		},
		'large': {
			'size': (400, 400), 'background': 'white', 'detail': True,
		},
	},
}

DEFAULT_THUMBNAIL_OPTIONS = {
	'cart':     {'crop': True, 'detail': True, 'size': (160, 160)},
	'catalog':  {'crop': True, 'detail': True, 'size': (160, 160)},
	'email':    {'crop': True, 'detail': True, 'size': (120, 120)},
	'order':    {'crop': True, 'detail': True, 'size': (120, 120)},
	'print':    {'crop': True, 'detail': True, 'size': (320, 320)},
	'product':  {'crop': True, 'detail': True, 'size': (120, 120)},
	'watch':    {'crop': True, 'detail': True, 'size': (160, 160)},
}
