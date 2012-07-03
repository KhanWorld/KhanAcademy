import os

try:
    import secrets
except:
    class secrets(object):
        facebook_app_id = '312005312199613'
        facebook_app_secret = '2fb89d2e44c7483ccd949a722772c7c7'
        google_consumer_key = None
        google_consumer_secret = None
        remote_api_secret = None
        constant_contact_api_key = None
        constant_contact_username = None
        constant_contact_password = None
        flask_secret_key = None
        dashboard_secret = None
        khanbugz_passwd = None

# A singleton shared across requests
class App(object):
    # This gets reset every time a new version is deployed on
    # a live server.  It has the form major.minor where major
    # is the version specified in app.yaml and minor auto-generated
    # during the deployment process.  Minor is always 1 on a dev
    # server.
    version = os.environ.get('CURRENT_VERSION_ID')

    # khanacademy.org
    facebook_app_id = secrets.facebook_app_id
    facebook_app_secret = secrets.facebook_app_secret

    google_consumer_key = secrets.google_consumer_key
    google_consumer_secret = secrets.google_consumer_secret

    remote_api_secret = secrets.remote_api_secret

    constant_contact_api_key = secrets.constant_contact_api_key
    constant_contact_username = secrets.constant_contact_username
    constant_contact_password = secrets.constant_contact_password

    flask_secret_key = secrets.flask_secret_key

    dashboard_secret = secrets.dashboard_secret

    khanbugz_passwd = secrets.khanbugz_passwd

    root = os.path.dirname(__file__)

    is_dev_server = os.environ["SERVER_SOFTWARE"].startswith('Development')

    accepts_openid = True
    offline_mode = False
