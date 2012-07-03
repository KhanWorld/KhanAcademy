from google.appengine.api import users

# If using the default should_profile implementation, the profiler
# will only be enabled for requests made by the following GAE users.
enabled_profiler_emails = [
    "benkomalo@gmail.com",
    "davidhu91@gmail.com",
    "dmnd@desmondbrand.com",
    "jace.kohlmeier@gmail.com",
    "jasonrosoff@gmail.com",
    "joelburget@gmail.com",
    "kamens@gmail.com",
    "marcia.lee@gmail.com",
    "marcos@khanacademy.org",
    "netzen@gmail.com", # Brian Bondy
    "ParkerKuivila@gmail.com",
    "spicyjalapeno@gmail.com", # Ben Alpert
    "tallnerd@gmail.com", # James Irwin
    "tom@khanacademy.org",
    "sundar@khanacademy.org",
    "shantanu@khanacademy.org",
]

# Customize should_profile to return true whenever a request should be profiled.
# This function will be run once per request, so make sure its contents are fast.
class ProfilerConfigProduction:
    @staticmethod
    def should_profile(environ):
        user = users.get_current_user()
        return user and user.email() in enabled_profiler_emails

class ProfilerConfigDevelopment:
    @staticmethod
    def should_profile(environ):
        return users.is_current_user_admin()
