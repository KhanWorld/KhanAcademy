import logging
import simplejson

from flask import request

from app import App
from api.auth.auth_util import get_response

from oauth_provider.oauth import OAuthConsumer, OAuthToken, OAuthRequest, OAuthSignatureMethod_HMAC_SHA1

class GoogleOAuthClient(object):

    Consumer = OAuthConsumer(App.google_consumer_key, App.google_consumer_secret)

    def fetch_request_token(self, oauth_map):
        oauth_request = OAuthRequest.from_consumer_and_token(
                GoogleOAuthClient.Consumer,
                http_url = "http://www.khanacademy.org/_ah/OAuthGetRequestToken",
                callback = "%sapi/auth/google_token_callback?oauth_map_id=%s" % (request.host_url, oauth_map.key().id())
                )

        oauth_request.sign_request(OAuthSignatureMethod_HMAC_SHA1(), GoogleOAuthClient.Consumer, None)

        response = get_response(oauth_request.to_url())

        return OAuthToken.from_string(response)

    def fetch_access_token(self, oauth_map):

        token = OAuthToken(oauth_map.google_request_token, oauth_map.google_request_token_secret)

        oauth_request = OAuthRequest.from_consumer_and_token(
                GoogleOAuthClient.Consumer,
                token = token,
                verifier = oauth_map.google_verification_code,
                http_url = "http://www.khanacademy.org/_ah/OAuthGetAccessToken"
                )

        oauth_request.sign_request(OAuthSignatureMethod_HMAC_SHA1(), GoogleOAuthClient.Consumer, token)

        response = get_response(oauth_request.to_url())

        return OAuthToken.from_string(response)

    def access_user_id_and_email(self, oauth_map):

        token = OAuthToken(oauth_map.google_access_token, oauth_map.google_access_token_secret)

        oauth_request = OAuthRequest.from_consumer_and_token(
                GoogleOAuthClient.Consumer,
                token = token,
                http_url = "%sapi/auth/current_google_oauth_user_id_and_email" % request.host_url
                )

        oauth_request.sign_request(OAuthSignatureMethod_HMAC_SHA1(), GoogleOAuthClient.Consumer, token)

        response = get_response(oauth_request.to_url())

        try:
            obj = simplejson.loads(response)

            if len(obj) == 2:
                # (user_id, email)
                return tuple(obj)
        except simplejson.decoder.JSONDecodeError:
            logging.error("Error decoding json from current_google_oauth_user_id_and_email; json was %r", response)
            pass

        return (None, None)
