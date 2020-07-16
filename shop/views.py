from django.shortcuts import render
from django.http import HttpResponse

from shop.models import Store


def test(request):
	store = Store.objects.get_current(request)
	mylist = store.get_cart_modifiers()
	print(mylist)
	html = "<html><body>%s</body></html>" % (mylist)
	return HttpResponse(html)
