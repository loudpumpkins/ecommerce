from django.core.management.base import BaseCommand


class Command(BaseCommand):
	def add_arguments(self, parser):
		parser.add_argument(
			'filename',
			nargs='?',
			default='products-meta.json',
		)

	def handle(self, filename, *args, **options):
		from django.contrib import admin
		import inspect
		a = admin.ModelAdmin
		self.stdout.write(inspect.currentframe())
