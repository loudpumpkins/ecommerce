# external
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.providers.facebook.views import (
            FacebookOAuth2Adapter as OriginalFacebookOAuth2Adapter)

class ShopAccountAdapter(DefaultAccountAdapter):
    """
    For inactive users, Default adapter redirects to some `account_inative` page
    defined in allauth urls. We dont want that - we just want the process to
    continue and receive a token.
    """

    def respond_user_inactive(self, request, user):
        pass


class FacebookOAuth2Adapter(OriginalFacebookOAuth2Adapter):
    pass
