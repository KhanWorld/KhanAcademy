from google.appengine.ext import db

class CustomRedirect(db.Model):
    redirect_from = db.StringProperty()
    redirect_to = db.StringProperty()

    @staticmethod
    def get_key_name(redirect_from):
        return "custom_redirect:%s" % redirect_from

    @property
    def relative_url(self):
        return "/r/%s" % self.redirect_from
