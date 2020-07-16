from django.core.management.base import BaseCommand


class Command(BaseCommand):
	def add_arguments(self, parser):
		parser.add_argument(
			'filename',
			nargs='?',
			default='products-meta.json',
		)

	def handle(self, filename, *args, **options):
		self.stdout.write('hey')


