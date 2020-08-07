# external
from rest_framework import renderers
from rest_framework.utils import encoders

# internal
from shared.money import AbstractMoney


class HTMLRenderer(renderers.TemplateHTMLRenderer):
	"""
	Modified TemplateHTMLRenderer, which shall be used to render templates used
	for the desktop version of the shop. Uses alternative implementation of
	`get_template_context` to place the serialized data into a `data` attribute
	by default or `context_data_name` value from the View. Avoids pollution of
	the root template context scope.

	Allows extra context to be placed into template_context data by adding it
	to the views `get_renderer_context`. eg:

	def get_renderer_context(self):
		renderer_context = super().get_renderer_context()
		if renderer_context['request'].accepted_renderer.format == 'html':
			renderer_context.update(
				product=self.get_object(),
			)
		return renderer_context

	Instead of accessing {{ field1 }}, you would access {{ data.field1 }} in the
	templates.
	"""
	def get_template_context(self, data, renderer_context):
		response = renderer_context['response']
		if response.exception:
			return dict(data, status_code=response.status_code)
		else:
			view = renderer_context['view']
			key = getattr(view, 'context_data_name', 'data')
			data = {key: data}
			# append none default attributes from renderer_context to the data
			for k, v in renderer_context.items():
				if k not in ['view', 'args', 'kwargs', 'request']:
					data[k] = v
			return data


class JSONEncoder(encoders.JSONEncoder):
	"""JSONEncoder subclass that knows how to encode Money."""

	def default(self, obj):
		if isinstance(obj, AbstractMoney):
			return '{:f}'.format(obj)
		return super().default(obj)


class JSONRenderer(renderers.JSONRenderer):
	encoder_class = JSONEncoder