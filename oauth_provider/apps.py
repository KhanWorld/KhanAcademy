
from oauth_provider.models_oauth import Consumer
from oauth_provider.consts import ACCEPTED

import request_handler
import models
import util

class Register(request_handler.RequestHandler):
    def get(self):
        if models.UserData.current():
            self.render_jinja2_template("oauth_provider/register_app.html", {})
        else:
            self.redirect(util.create_login_url(self.request.uri))

    def post(self):

        user_data = models.UserData.current()
        if user_data:
            name = self.request_string("name", default="").strip()
            description = self.request_string("description", default="").strip()
            website = self.request_string("website", default="").strip()
            phone = self.request_string("phone", default="").strip()
            company = self.request_string("company", default="").strip()

            name_error = description_error = agree_error = None

            if not self.request_bool("agree", default=False):
                agree_error = "You must agree to our terms of service."

            if not name:
                name_error = "You need a name for your app."

            if not description:
                description_error = "You need to describe your app."

            if name:
                consumer = Consumer.get_by_key_name(name)
                if consumer:
                    name_error = "This name is already taken."

            if name_error or description_error or agree_error:

                self.render_jinja2_template("oauth_provider/register_app.html",
                        {
                            "name": name,
                            "description": description,
                            "website": website,
                            "phone": phone,
                            "company": company,
                            "name_error": name_error,
                            "description_error": description_error,
                            "agree_error": agree_error,
                        })

            else:

                consumer = Consumer.get_or_insert(
                        key_name = name,
                        name = name,
                        description = description,
                        website = website,
                        user = user_data.user,
                        status = ACCEPTED,
                        phone = phone,
                        company = company,
                        anointed = False
                        )
                consumer.generate_random_codes()

                self.render_jinja2_template("oauth_provider/register_app.html",
                        {
                            "consumer_key": consumer.key_,
                            "consumer_secret": consumer.secret
                        })
        else:
            self.redirect(util.create_login_url(self.request.uri))


