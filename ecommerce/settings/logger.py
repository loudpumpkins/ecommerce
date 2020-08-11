import sys
import logging

from django.core.management.color import color_style, make_style

'''
Adds colour to the logger. use 'color_style()' to set colour safely. 
`make_style()' is unsafe as it does not check to see if the terminal supports 
colours or not, however, `color_style()` does a rudimentary test. Meaning 
that some terminal that support colours will be falsly flagged as 
'non-colorable'

Configure 'COLOURS' variable for functionality. See:
https://docs.djangoproject.com/en/dev/ref/django-admin/#syntax-coloring

Base colour palettes:

    'light'
    
        DEBUG = green/yellow
        INFO = white
        WARNING = red
        ERROR = red/bold
        CRITICAL = magenta
    
    'dark'
    
        DEBUG = cyan/blue
        INFO = white/bold
        WARNING = yellow
        ERROR = red/bold
        CRITICAL = magenta/bold

level

    error - A major error.
    notice - A minor error.
    success - A success.
    warning - A warning.

possible colours:

    black
    red
    green
    yellow
    blue
    magenta
    cyan
    white

possible options on the colours:

    bold
    underscore
    blink
    reverse
    conceal

CONFIG = '{base palette};{level}={colour[/colour]}[,options];[...]'

eg: CONFIG = 'light;error=yellow/blue,blink;notice=magenta'
'''

COLOURS = "dark;error=red/yellow,bold"
FORCE_COLOUR = True  # `True` may cause errors in some terminals


class DjangoColorsFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super(DjangoColorsFormatter, self).__init__(*args, **kwargs)

        self.style = self.configure_style(
            make_style(config_string=COLOURS) if FORCE_COLOUR else color_style()
        )

    def configure_style(self, style):

        style.DEBUG = style.HTTP_NOT_MODIFIED
        style.INFO = style.HTTP_INFO
        style.WARNING = style.HTTP_NOT_FOUND
        style.ERROR = style.ERROR
        style.CRITICAL = style.HTTP_SERVER_ERROR
        return style

    def format(self, record):
        message = logging.Formatter.format(self, record)
        colorizer = getattr(self.style, record.levelname, self.style.HTTP_SUCCESS)
        return colorizer(message)
