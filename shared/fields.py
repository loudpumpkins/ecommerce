import enum
from decimal import Decimal

# external
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import force_str
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

# internal
from shared.util import ISO_3166_CODES, CURRENCIES
from shared.money import MoneyMaker, AbstractMoney


postgresql_engine_names = [
	'django.db.backends.postgresql',
	'django.db.backends.postgresql_psycopg2',
]

if settings.DATABASES['default']['ENGINE'] in postgresql_engine_names:
	from django.contrib.postgres.fields import JSONField as _JSONField
else:
	from jsonfield.fields import JSONField as _JSONField


class JSONField(_JSONField):
	def __init__(self, *args, **kwargs):
		kwargs.update({'default': dict})
		super().__init__(*args, **kwargs)

	def deconstruct(self):
		name, path, args, kwargs = super().deconstruct()
		del kwargs['default']
		return name, path, args, kwargs


class ChoiceEnumMeta(enum.EnumMeta):
	def __call__(cls, value, *args, **kwargs):
		if isinstance(value, str):
			try:
				value = cls.__members__[value]
			except KeyError:
				pass  # let the super method complain
		return super().__call__(value, *args, **kwargs)

	def __new__(metacls, classname, bases, classdict):
		labels = {}
		for key in classdict._member_names:
			source_value = classdict[key]
			if isinstance(source_value, (list, tuple)):
				try:
					val, labels[key] = source_value
				except ValueError:
					raise ValueError("Invalid ChoiceEnum member '{}'".format(key))
			else:
				val = source_value
				labels[key] = key.replace("_", " ").title()
			# Use dict.__setitem__() to suppress defenses against
			# double assignment in enum's classdict
			dict.__setitem__(classdict, key, val)
		cls = super().__new__(metacls, classname, bases, classdict)
		for key, label in labels.items():
			getattr(cls, key).label = label
		return cls

	@property
	def choices(cls):
		return [(k.value, k.label) for k in cls]

	@property
	def default(cls):
		try:
			return next(iter(cls))
		except StopIteration:
			return None


class ChoiceEnum(enum.Enum, metaclass=ChoiceEnumMeta):
	"""
	Utility class to handle choices in Django model and/or form fields.
	Usage:

	class Color(ChoiceEnum):
		WHITE = 0, "White"
		RED = 1, "Red"
		GREEN = 2, "Green"
		BLUE = 3, "Blue"

	green = Color.GREEN

	color = forms.ChoiceField(
		choices=Color.choices,
		default=Color.default,
	)
	"""
	def __str__(self):
		return force_str(self.label)


class ChoiceEnumField(models.PositiveSmallIntegerField):
	description = _("Customer recognition state")

	def __init__(self, *args, **kwargs):
		self.enum_type = kwargs.pop('enum_type', ChoiceEnum)  # fallback is required form migrations
		if not issubclass(self.enum_type, ChoiceEnum):
			raise ValueError("enum_type must be a subclass of `ChoiceEnum`.")
		kwargs.update(choices=self.enum_type.choices)
		kwargs.setdefault('default', self.enum_type.default)
		super().__init__(*args, **kwargs)

	def deconstruct(self):
		name, path, args, kwargs = super().deconstruct()
		if 'choices' in kwargs:
			del kwargs['choices']
		if kwargs['default'] is self.enum_type.default:
			del kwargs['default']
		elif isinstance(kwargs['default'], self.enum_type):
			kwargs['default'] = kwargs['default'].value
		return name, path, args, kwargs

	def from_db_value(self, value, expression, connection):
		try:
			return self.enum_type(value)
		except ValueError:
			return value

	def get_prep_value(self, state):
		if isinstance(state, self.enum_type):
			return state.value
		return state

	def to_python(self, state):
		return self.enum_type(state)

	def value_to_string(self, obj):
		value = getattr(obj, self.name, obj)
		if not isinstance(value, self.enum_type):
			raise ValueError("Value must be of type {}".format(self.enum_type))
		return value.name


class CountryField(models.CharField):
	"""
	This creates a simple input field to choose a country.
	"""
	def __init__(self, *args, **kwargs):
		defaults = {
			'max_length': 3,
			'choices': ISO_3166_CODES,
		}
		defaults.update(kwargs)
		super().__init__(*args, **defaults)

	def deconstruct(self):
		name, path, args, kwargs = super().deconstruct()
		if kwargs['max_length'] == 3:
			kwargs.pop('max_length')
		if kwargs['choices'] == ISO_3166_CODES:
			kwargs.pop('choices')
		return name, path, args, kwargs


class MoneyFieldWidget(forms.widgets.NumberInput):
	"""
	Replacement for NumberInput widget adding the currency suffix.
	"""
	def __init__(self, attrs=None):
		defaults = {'style': 'width: 75px; text-align: right'}
		try:
			self.currency_code = attrs.pop('currency_code')
			defaults.update(attrs)
		except (KeyError, TypeError):
			raise ValueError("MoneyFieldWidget must be instantiated with a currency_code.")
		super().__init__(defaults)

	def render(self, name, value, attrs=None, renderer=None):
		input_field = super().render(name, value, attrs, renderer)
		return format_html('{} <strong>{}</strong>', input_field, self.currency_code)


class MoneyFormField(forms.DecimalField):
	"""
	Use this field type in Django Forms instead of a DecimalField, whenever a input field for
	the Money representation is required.
	"""
	def __init__(self, money_class=None, **kwargs):
		if money_class is None:
			money_class = MoneyMaker()
		if not issubclass(money_class, AbstractMoney):
			raise AttributeError("Given `money_class` does not declare a valid money type")
		self.Money = money_class
		if 'widget' not in kwargs:
			kwargs['widget'] = MoneyFieldWidget(attrs={'currency_code': money_class.currency})
		super().__init__(**kwargs)

	def prepare_value(self, value):
		if isinstance(value, AbstractMoney):
			return Decimal(value)
		return value

	def to_python(self, value):
		value = super().to_python(value)
		return self.Money(value)

	def validate(self, value):
		if value.currency != self.Money.currency:
			raise ValidationError("Can not convert different Money types.")
		super().validate(Decimal(value))
		return value


class MoneyField(models.DecimalField):
	"""
	A MoneyField shall be used to store money related amounts in the database,
	keeping track of the used currency. Accessing a model field of type MoneyField,
	returns a MoneyIn<CURRENCY> type.
	"""
	description = _("Money in %(currency_code)s")

	def __init__(self, *args, **kwargs):
		self.currency_code = kwargs.pop('currency', settings.DEFAULT_CURRENCY)
		self.Money = MoneyMaker(self.currency_code)
		defaults = {
			'max_digits': 30,
			'decimal_places': CURRENCIES[self.currency_code][1],
		}
		defaults.update(kwargs)
		super().__init__(*args, **defaults)

	def deconstruct(self):
		name, path, args, kwargs = super(MoneyField, self).deconstruct()
		if kwargs['max_digits'] == 30:
			kwargs.pop('max_digits')
		if kwargs['decimal_places'] == CURRENCIES[self.currency_code][1]:
			kwargs.pop('decimal_places')
		return name, path, args, kwargs

	def to_python(self, value):
		if isinstance(value, AbstractMoney):
			return value
		if value is None:
			return self.Money('NaN')
		value = super().to_python(value)
		return self.Money(value)

	def get_prep_value(self, value):
		# force to type Decimal by using grandparent super
		value = super(models.DecimalField, self).get_prep_value(value)
		return super().to_python(value)

	def from_db_value(self, value, expression, connection):
		if value is None:
			return
		if isinstance(value, float):
			value = str(value)
		return self.Money(value)

	def get_db_prep_save(self, value, connection):
		if isinstance(value, Decimal) and value.is_nan():
			return None
		return super().get_db_prep_save(value, connection)

	def get_prep_lookup(self, lookup_type, value):
		if isinstance(value, AbstractMoney):
			if value.get_currency() != self.Money.get_currency():
				msg = "This field stores money in {}, but the lookup amount is in {}"
				raise ValueError(msg.format(value.get_currency(), self.Money.get_currency()))
			value = value.as_decimal()
		result = super().get_prep_lookup(lookup_type, value)
		return result

	def value_to_string(self, obj):
		value = self._get_val_from_obj(obj)
		# grandparent super
		value = super(models.DecimalField, self).get_prep_value(value)
		return self.to_python(value)

	def formfield(self, **kwargs):
		widget = MoneyFieldWidget(attrs={'currency_code': self.Money.currency})
		defaults = {'form_class': MoneyFormField, 'widget': widget, 'money_class': self.Money}
		defaults.update(**kwargs)
		formfield = super().formfield(**defaults)
		return formfield
