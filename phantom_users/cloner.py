import request_handler

class Clone(request_handler.RequestHandler):
    def get(self):
        title = "Please wait while we copy your data to your new account."
        message_html = "We're in the process of copying over all of the progress you've made. You may access your account once the transfer is complete."
        sub_message_html = "This process can take a long time, thank you for your patience."
        cont = self.request_string('continue', default = "/")
        self.render_jinja2_template('phantom_users/transfer.html',
            {'title': title, 'message_html':message_html,"sub_message_html":sub_message_html, "dest_url":cont})
