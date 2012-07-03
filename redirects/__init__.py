import user_util

from request_handler import RequestHandler
from redirects.models import CustomRedirect

class Redirect(RequestHandler):

    def get(self):

        pieces = self.request.path.split("/r/")
        
        if len(pieces) == 2:

            redirect = CustomRedirect.get_by_key_name(CustomRedirect.get_key_name(pieces[1]))
            if redirect:
                self.redirect(redirect.redirect_to)
                return

        self.redirect("/")

class List(RequestHandler):

    @user_util.developer_only
    def get(self):

        context = {
            "redirects": CustomRedirect.all().order("redirect_from")
        }

        return self.render_jinja2_template("redirects/list.html", context)

class Add(RequestHandler):

    @user_util.developer_only
    def post(self):

        redirect_from = self.request_string("redirect_from")
        redirect_to = self.request_string("redirect_to")

        if redirect_from and redirect_to:

            if "://" not in redirect_to:
                redirect_to = "http://%s" % redirect_to

            CustomRedirect(
                    key_name = CustomRedirect.get_key_name(redirect_from),
                    redirect_from = redirect_from,
                    redirect_to = redirect_to,
            ).put()

        self.redirect("/redirects")

class Remove(RequestHandler):

    @user_util.developer_only
    def post(self):

        redirect_from = self.request_string("redirect_from")

        if redirect_from:
            redirect = CustomRedirect.get_by_key_name(CustomRedirect.get_key_name(redirect_from))

            if redirect:
                redirect.delete()

        self.redirect("/redirects")
