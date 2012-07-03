import logging

import request_handler
import library
from badges import util_badges

class Warmup(request_handler.RequestHandler):

    def get(self):

        logging.info("Warmup: loading homepage html")
        library.library_content_html()

        logging.info("Warmup: loading badges")
        util_badges.all_badges()
        util_badges.all_badges_dict()

