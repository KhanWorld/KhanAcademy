from request_handler import RequestHandler
import os

class RobotsTxt(RequestHandler):
    """Dynamic robots.txt that hides staging apps from search engines"""
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write("User-agent: *\n")

        visible_domains = [
            'www.khanacademy.org',
            'smarthistory.khanacademy.org',
        ]

        if os.environ['SERVER_NAME'] in visible_domains:
            self.response.write("Disallow:")
        else:
            self.response.write("Disallow: *")
