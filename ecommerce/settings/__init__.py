from .base import *

try:
	# from .local import *
	pass # delete this soon
except:
	from .production import *