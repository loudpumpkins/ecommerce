# external
from allauth.account.adapter import DefaultAccountAdapter


class ShopAccountAdapter(DefaultAccountAdapter):
    """
    For inactive users, Default adapter redirects to some `account_inative` page
    defined in allauth urls. We dont want that - we just want the process to
    continue and receive a token.
    """

    def respond_user_inactive(self, request, user):
        pass
