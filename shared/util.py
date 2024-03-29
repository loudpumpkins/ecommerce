import ntpath

# external
from django.utils.translation import gettext_lazy as _


def get_filename_from_path(path):
	head, tail = ntpath.split(path)
	return tail or ntpath.basename(head)


def get_client_ip(request):
	"""
	Get the client's IP address. May return a list of IPs if client uses proxies
	or if webserver has multiple proxies before it is reached by client.
	"""
	# https://stackoverflow.com/questions/4581789/how-do-i-get-user-ip-address-in-django
	x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
	if x_forwarded_for:
		# ip = x_forwarded_for.split(',')[0]
		ip = x_forwarded_for
	else:
		ip = request.META.get('REMOTE_ADDR')
	return ip


class classproperty(object):
	"""Like @property, but for classes, not just instances.

	Example usage:

		>>> from shared.util import classproperty
		>>> class A(object):
		...     @classproperty
		...     def x(cls):
		...         return 'x'
		...     @property
		...     def y(self):
		...         return 'y'
		...
		>>> A.x
		'x'
		>>> A().x
		'x'
		>>> A.y
		<property object at 0x2939628>
		>>> A().y
		'y'

	"""
	def __init__(self, fget):
		self.fget = fget

	def __get__(self, owner_self, owner_cls):
		return self.fget(owner_cls)


# Dictionary of currency representations:
# key: official ISO 4217 code
# value[0]: numeric representation
# value[1]: number of digits
# value[2]: currency symbol in UTF-8
# value[3]: textual description
CURRENCIES = {
	'AED': ('784', 2, 'د.إ', _('United Arab Emirates dirham')),
	'AUD': ('036', 2, '$', _("Australian Dollar")),
	'BHD': ('048', 3, '.د.ب', _('Bahraini dinar')),
	'BRL': ('986', 2, 'R$', _("Brazilian Real")),
	'CAD': ('124', 2, 'C$', _("Canadian Dollar")),
	'CHF': ('756', 2, 'SFr․', _("Swiss Franc")),  # Unicode 8228 as dot to prevent formatting issues
	'CNY': ('156', 2, '¥', _("Chinese Yuan")),
	'CZK': ('203', 2, 'Kč', _("Czech Koruna")),
	'EUR': ('978', 2, '€', _("Euro")),
	'GBP': ('826', 2, '£', _("Pound Sterling")),
	'HKD': ('344', 2, 'HK$', _("Hong Kong Dollar")),
	'HRK': ('191', 2, 'kn', _("Croatian kuna")),
	'HUF': ('348', 0, 'Ft', _("Hungarian Forint")),
	'ILS': ('376', 2, '₪', _("Israeli Sheqel")),
	'INR': ('356', 2, '₹', _("Indian Rupee")),
	'JPY': ('392', 0, '¥', _("Japanese Yen")),
	'KWD': ('414', 3, 'د.ك', _("Kuwaiti Dinar")),
	'OMR': ('512', 3, 'ر.ع.', _('Omani rial')),
	'QAR': ('634', 2, 'ر.ق', _('Qatari riyal')),
	'RUB': ('643', 2, '₽', _("Russian Ruble")),
	'SAR': ('682', 2, 'ر.س', _('Saudi riyal')),
	'TND': ('788', 3, 'TND', _("Tunisian Dinar")),
	'UAH': ('980', 2, '₴', _("Ukrainian Hryvnia")),
	'USD': ('840', 2, '$', _("US Dollar")),
	'SEK': ('752', 2, 'kr', _("Swedish Kronor")),
	'ZAR': ('710', 2, 'R', _("South African Rand")),
}


ISO_3166_CODES = [
	('AF', _("Afghanistan")),
	('AX', _("Aland Islands")),
	('AL', _("Albania")),
	('DZ', _("Algeria")),
	('AS', _("American Samoa")),
	('AD', _("Andorra")),
	('AO', _("Angola")),
	('AI', _("Anguilla")),
	('AQ', _("Antarctica")),
	('AG', _("Antigua And Barbuda")),
	('AR', _("Argentina")),
	('AM', _("Armenia")),
	('AW', _("Aruba")),
	('AU', _("Australia")),
	('AT', _("Austria")),
	('AZ', _("Azerbaijan")),
	('BS', _("Bahamas")),
	('BH', _("Bahrain")),
	('BD', _("Bangladesh")),
	('BB', _("Barbados")),
	('BY', _("Belarus")),
	('BE', _("Belgium")),
	('BZ', _("Belize")),
	('BJ', _("Benin")),
	('BM', _("Bermuda")),
	('BT', _("Bhutan")),
	('BO', _("Bolivia, Plurinational State Of")),
	('BQ', _("Bonaire, Saint Eustatius And Saba")),
	('BA', _("Bosnia And Herzegovina")),
	('BW', _("Botswana")),
	('BV', _("Bouvet Island")),
	('BR', _("Brazil")),
	('IO', _("British Indian Ocean Territory")),
	('BN', _("Brunei Darussalam")),
	('BG', _("Bulgaria")),
	('BF', _("Burkina Faso")),
	('BI', _("Burundi")),
	('KH', _("Cambodia")),
	('CM', _("Cameroon")),
	('CA', _("Canada")),
	('CV', _("Cape Verde")),
	('KY', _("Cayman Islands")),
	('CF', _("Central African Republic")),
	('TD', _("Chad")),
	('CL', _("Chile")),
	('CN', _("China")),
	('CX', _("Christmas Island")),
	('CC', _("Cocos (Keeling) Islands")),
	('CO', _("Colombia")),
	('KM', _("Comoros")),
	('CG', _("Congo")),
	('CD', _("Congo, The Democratic Republic Of The")),
	('CK', _("Cook Islands")),
	('CR', _("Costa Rica")),
	('HR', _("Croatia")),
	('CU', _("Cuba")),
	('CW', _("Curacao")),
	('CY', _("Cyprus")),
	('CZ', _("Czech Republic")),
	('DK', _("Denmark")),
	('DJ', _("Djibouti")),
	('DM', _("Dominica")),
	('DO', _("Dominican Republic")),
	('EC', _("Ecuador")),
	('EG', _("Egypt")),
	('SV', _("El Salvador")),
	('GQ', _("Equatorial Guinea")),
	('ER', _("Eritrea")),
	('EE', _("Estonia")),
	('ET', _("Ethiopia")),
	('FK', _("Falkland Islands (Malvinas)")),
	('FO', _("Faroe Islands")),
	('FJ', _("Fiji")),
	('FI', _("Finland")),
	('FR', _("France")),
	('GF', _("French Guiana")),
	('PF', _("French Polynesia")),
	('TF', _("French Southern Territories")),
	('GA', _("Gabon")),
	('GM', _("Gambia")),
	('DE', _("Germany")),
	('GH', _("Ghana")),
	('GI', _("Gibraltar")),
	('GR', _("Greece")),
	('GL', _("Greenland")),
	('GD', _("Grenada")),
	('GP', _("Guadeloupe")),
	('GU', _("Guam")),
	('GT', _("Guatemala")),
	('GG', _("Guernsey")),
	('GN', _("Guinea")),
	('GW', _("Guinea-Bissau")),
	('GY', _("Guyana")),
	('HT', _("Haiti")),
	('HM', _("Heard Island and McDonald Islands")),
	('VA', _("Holy See (Vatican City State)")),
	('HN', _("Honduras")),
	('HK', _("Hong Kong")),
	('HU', _("Hungary")),
	('IS', _("Iceland")),
	('IN', _("India")),
	('ID', _("Indonesia")),
	('IR', _("Iran, Islamic Republic Of")),
	('IQ', _("Iraq")),
	('IE', _("Ireland")),
	('IL', _("Israel")),
	('IT', _("Italy")),
	('CI', _("Ivory Coast")),
	('JM', _("Jamaica")),
	('JP', _("Japan")),
	('JE', _("Jersey")),
	('JO', _("Jordan")),
	('KZ', _("Kazakhstan")),
	('KE', _("Kenya")),
	('KI', _("Kiribati")),
	('KP', _("Korea, Democratic People's Republic Of")),
	('KR', _("Korea, Republic Of")),
	('KS', _("Kosovo")),
	('KW', _("Kuwait")),
	('KG', _("Kyrgyzstan")),
	('LA', _("Lao People's Democratic Republic")),
	('LV', _("Latvia")),
	('LB', _("Lebanon")),
	('LS', _("Lesotho")),
	('LR', _("Liberia")),
	('LY', _("Libyan Arab Jamahiriya")),
	('LI', _("Liechtenstein")),
	('LT', _("Lithuania")),
	('LU', _("Luxembourg")),
	('MO', _("Macao")),
	('MK', _("Macedonia")),
	('MG', _("Madagascar")),
	('MW', _("Malawi")),
	('MY', _("Malaysia")),
	('MV', _("Maldives")),
	('ML', _("Mali")),
	('ML', _("Malta")),
	('MH', _("Marshall Islands")),
	('MQ', _("Martinique")),
	('MR', _("Mauritania")),
	('MU', _("Mauritius")),
	('YT', _("Mayotte")),
	('MX', _("Mexico")),
	('FM', _("Micronesia")),
	('MD', _("Moldova")),
	('MC', _("Monaco")),
	('MN', _("Mongolia")),
	('ME', _("Montenegro")),
	('MS', _("Montserrat")),
	('MA', _("Morocco")),
	('MZ', _("Mozambique")),
	('MM', _("Myanmar")),
	('NA', _("Namibia")),
	('NR', _("Nauru")),
	('NP', _("Nepal")),
	('NL', _("Netherlands")),
	('AN', _("Netherlands Antilles")),
	('NC', _("New Caledonia")),
	('NZ', _("New Zealand")),
	('NI', _("Nicaragua")),
	('NE', _("Niger")),
	('NG', _("Nigeria")),
	('NU', _("Niue")),
	('NF', _("Norfolk Island")),
	('MP', _("Northern Mariana Islands")),
	('NO', _("Norway")),
	('OM', _("Oman")),
	('PK', _("Pakistan")),
	('PW', _("Palau")),
	('PS', _("Palestinian Territory, Occupied")),
	('PA', _("Panama")),
	('PG', _("Papua New Guinea")),
	('PY', _("Paraguay")),
	('PE', _("Peru")),
	('PH', _("Philippines")),
	('PN', _("Pitcairn")),
	('PL', _("Poland")),
	('PT', _("Portugal")),
	('PR', _("Puerto Rico")),
	('QA', _("Qatar")),
	('RE', _("Reunion")),
	('RO', _("Romania")),
	('RU', _("Russian Federation")),
	('RW', _("Rwanda")),
	('BL', _("Saint Barthelemy")),
	('SH', _("Saint Helena, Ascension & Tristan Da Cunha")),
	('KN', _("Saint Kitts and Nevis")),
	('LC', _("Saint Lucia")),
	('MF', _("Saint Martin (French Part)")),
	('PM', _("Saint Pierre and Miquelon")),
	('VC', _("Saint Vincent And The Grenadines")),
	('WS', _("Samoa")),
	('SM', _("San Marino")),
	('ST', _("Sao Tome And Principe")),
	('SA', _("Saudi Arabia")),
	('SN', _("Senegal")),
	('RS', _("Serbia")),
	('SC', _("Seychelles")),
	('SL', _("Sierra Leone")),
	('SG', _("Singapore")),
	('SX', _("Sint Maarten (Dutch Part)")),
	('SK', _("Slovakia")),
	('SI', _("Slovenia")),
	('SB', _("Solomon Islands")),
	('SO', _("Somalia")),
	('ZA', _("South Africa")),
	('GS', _("South Georgia And The South Sandwich Islands")),
	('ES', _("Spain")),
	('LK', _("Sri Lanka")),
	('SD', _("Sudan")),
	('SR', _("Suriname")),
	('SJ', _("Svalbard And Jan Mayen")),
	('SZ', _("Swaziland")),
	('SE', _("Sweden")),
	('CH', _("Switzerland")),
	('SY', _("Syrian Arab Republic")),
	('TW', _("Taiwan")),
	('TJ', _("Tajikistan")),
	('TZ', _("Tanzania")),
	('TH', _("Thailand")),
	('TL', _("Timor-Leste")),
	('TG', _("Togo")),
	('TK', _("Tokelau")),
	('TO', _("Tonga")),
	('TT', _("Trinidad and Tobago")),
	('TN', _("Tunisia")),
	('TR', _("Turkey")),
	('TM', _("Turkmenistan")),
	('TC', _("Turks And Caicos Islands")),
	('TV', _("Tuvalu")),
	('UG', _("Uganda")),
	('UA', _("Ukraine")),
	('AE', _("United Arab Emirates")),
	('GB', _("United Kingdom")),
	('US', _("United States")),
	('UM', _("United States Minor Outlying Islands")),
	('UY', _("Uruguay")),
	('UZ', _("Uzbekistan")),
	('VU', _("Vanuatu")),
	('VE', _("Venezuela, Bolivarian Republic Of")),
	('VN', _("Viet Nam")),
	('VG', _("Virgin Islands, British")),
	('VI', _("Virgin Islands, U.S.")),
	('WF', _("Wallis and Futuna")),
	('EH', _("Western Sahara")),
	('YE', _("Yemen")),
	('ZM', _("Zambia")),
	('ZW', _("Zimbabwe")),
]
