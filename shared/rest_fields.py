from collections import OrderedDict

# external
from rest_framework import renderers
from rest_framework import serializers
from rest_framework.utils import encoders

# internal
from shared.money import AbstractMoney


class OrderedDictField(serializers.Field):
	"""
	Serializer field which transparently bypasses the internal representation of an OrderedDict.
	"""
	def to_representation(self, obj):
		return OrderedDict(obj)

	def to_internal_value(self, data):
		return OrderedDict(data)


class JSONSerializerField(serializers.Field):
	"""
	Serializer field which transparently bypasses its object instead of serializing/deserializing.
	"""
	def __init__(self, encoder=None, **kwargs):
		super().__init__(**kwargs)

	def to_representation(self, obj):
		return obj

	def to_internal_value(self, data):
		return data


class JSONEncoder(encoders.JSONEncoder):
	"""JSONEncoder subclass that knows how to encode Money."""

	def default(self, obj):
		if isinstance(obj, AbstractMoney):
			return '{:f}'.format(obj)
		return super().default(obj)


class JSONRenderer(renderers.JSONRenderer):
	encoder_class = JSONEncoder


class MoneyField(serializers.Field):
	"""Money objects are serialized into their readable notation."""

	def __init__(self, *args, **kwargs):
		kwargs.update(read_only=True)
		super().__init__(*args, **kwargs)

	def to_representation(self, obj):
		return '{:f}'.format(obj)
