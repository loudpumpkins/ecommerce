from .base import *

if base.DEBUG:
	# from .local import *
	pass # delete this soon
else:
	from .production import *