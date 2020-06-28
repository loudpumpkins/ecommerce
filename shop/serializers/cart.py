# external
from rest_framework import serializers

# internal
from shared.fields import MoneyField


class ExtraCartRow(serializers.Serializer):
	"""
	This data structure holds extra information for each item, or for the whole
	cart, while processing the cart using their modifiers.
	"""
	label = serializers.CharField(
		read_only=True,
		help_text="A short description of this row in a natural language.",
	)

	amount = MoneyField(
		help_text="The price difference, if applied.",
	)