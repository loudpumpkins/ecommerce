import logging

# internal
from customer.managers import VisitingCustomer
from customer.models import Customer
from shop.models.cart import Cart
from shop.models.store import Store
from shop.serializers.cart import CartSerializer
from shop.serializers.store import StoreSerializer

logger = logging.getLogger(__name__)


def add_customer(request):
	"""
	Add the customer `python object` to the RequestContext
	"""
	assert hasattr(request, 'customer'), ("The request object does not contain a "
		"customer object. Add 'shop.middlerware.CustomerMiddleware' into "
		"MIDDLEWARE_CLASSES.")

	customer = request.customer
	if request.user.is_superuser:
		try:
			# set an emulate_user_id in admin's session to act as a specific user
			customer = Customer.objects.get(pk=request.session['emulate_user_id'])
		except Customer.DoesNotExist:
			# set invalid user id in emulate_user_id to act as visitor
			customer = VisitingCustomer()
		except (AttributeError, KeyError):
			pass
	return {'customer': customer}


def add_cart(request):
	"""
	Add the cart `serialized data` to the RequestContext
	"""
	assert hasattr(request, 'customer'), ("The request object does not contain a "
		"customer object. Add 'shop.middlerware.CustomerMiddleware' into "
		"MIDDLEWARE_CLASSES.")

	data = {'is_cart_filled': False}
	emulated_context = {'request': request}
	try:
		cart = Cart.objects.get_from_request(request)
		data['is_cart_filled'] = cart.items.exists()
		cart_serializer = CartSerializer(cart, context=emulated_context, label='cart')
		data['cart'] = cart_serializer.data
	except (KeyError, AttributeError, Cart.DoesNotExist) as e:
		logger.debug('Not able to load `cart` into template context. (%s)' % e)
	return data


def add_store(request):
	"""
	Add the store `serialized data` to the RequestContext
	"""
	store = Store.objects.get_current(request)
	store_serializer = StoreSerializer(store)
	return {'store': store_serializer.data}
