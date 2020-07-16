from django.core.management.base import BaseCommand
from shop.models.store import Store


class Command(BaseCommand):
	def handle(self, *args, **options):
		stores = Store.objects.all()
		for store in stores:
			self.stdout.write('PK: {:03d}\tStore: {}'.format(store.id, store.url))
