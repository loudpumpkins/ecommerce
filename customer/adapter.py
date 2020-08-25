import logging

# external
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.providers.facebook.views import (
            FacebookOAuth2Adapter as OriginalFacebookOAuth2Adapter)


logger = logging.getLogger(__name__)


class ShopAccountAdapter(DefaultAccountAdapter):
    """
    For inactive users, Default adapter redirects to some `account_inative` page
    defined in allauth urls. We dont want that - we just want the process to
    continue and receive a token.
    """

    def respond_user_inactive(self, request, user):
        pass


class FacebookOAuth2Adapter(OriginalFacebookOAuth2Adapter):
    """
    Append the login response `extra_data` to the user's `extra` JSON field
    """

    def complete_login(self, request, app, access_token, **kwargs):
        social_login = super().complete_login(request, app, access_token, **kwargs)
        social_login.user.extra = {
            'social': 'facebook',
            'social_resp': social_login.account.extra_data,
        }
        if not social_login.user.email:
            logger.warning('No email received in the given social login. '
                           '(user=%s, response=`%s`)' % (social_login.user,
                                                 social_login.account.extra_data))
        else:
            logger.debug('Social login SUCCESS. (%s)' % social_login.account.extra_data)
        return social_login
