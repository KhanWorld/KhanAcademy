import logging
import urllib
import urllib2

import simplejson
from google.appengine.api import memcache

from custom_exceptions import TumblrException
from app import App
from about import util_about

TUMBLR_URL = "http://khanacademy.tumblr.com"
POSTS_PER_PAGE = 5

class BlogPost:
    def __init__(self, json):
        self.post_id = json["id"]
        self.title = json["regular-title"]
        self.body = json["regular-body"]
        self.dt = json["date"]
        self.url = json["url-with-slug"]
        self.slug = json["slug"]

    def local_url(self):
        if not self.post_id:
            return "/about/blog"
        return "/about/blog/post/%s/%s" % (self.post_id, self.slug)

class TumblrDownBlogPost(BlogPost):
    def __init__(self):
        self.post_id = ""
        self.title = "Temporarily unavailable"
        self.body = "Our blog is temporarily unavailable but will be back soon."
        self.dt = ""
        self.url = "/about/blog"
        self.slug = ""

def strip_json(json):

    json = json.strip()

    if not json.startswith("{"):
        json = json[json.index("{"):]

    if not json.endswith("}"):
        json = json[:json.rindex("}") + 1]

    return json

def get_posts(offset = 0, post_id = None, force_refresh = False):

    json = ""

    params = {"start": offset, "num": POSTS_PER_PAGE + 1, "type": "text"}
    if post_id:
        params = {"id": post_id}

    params_encoded = urllib.urlencode(params)

    memcache_key = "blog_posts_%s" % params_encoded
    posts = memcache.get(memcache_key, namespace=App.version)

    if not posts or force_refresh:
        try:
            request = urllib2.urlopen("%s/api/read/json" % TUMBLR_URL, params_encoded)
            json = request.read()
        except:
            raise TumblrException("Error while grabbing blog posts from Tumblr.")

        posts = []

        try:
            json = strip_json(json)
            posts = parse_json_posts(json)
        except:
            raise TumblrException("Error while parsing blog posts from Tumblr")

        if posts:
            # Cache for an hour
            memcache.set(memcache_key, posts, time=60 * 60, namespace=App.version)

    return posts

def get_single_post(post_id, force_refresh = False):
    posts = get_posts(0, post_id, force_refresh)
    if len(posts):
        return posts[0]
    return None

def parse_json_posts(json):

    dict_json = None
    dict_json = simplejson.loads(json)

    if not dict_json:
        return []

    posts = []
    for json_post in dict_json["posts"]:
        post = BlogPost(json_post)
        posts.append(post)

    return posts

class ViewBlog(util_about.AboutRequestHandler):

    def get(self):

        offset = self.request_int("offset", default=0)
        force_refresh = self.request_bool("force_refresh", default=False)

        posts = []
        try:
            posts = get_posts(offset, None, force_refresh)
        except TumblrException:
            posts = [TumblrDownBlogPost()]

        has_prev = offset > 0
        has_next = len(posts) > POSTS_PER_PAGE
        prev_offset = max(0, offset - POSTS_PER_PAGE)
        next_offset = offset + POSTS_PER_PAGE

        posts = posts[:POSTS_PER_PAGE]

        dict_context = {
                "posts": posts, 
                "has_prev": has_prev, 
                "has_next": has_next, 
                "prev_offset": prev_offset,
                "next_offset": next_offset,
                "selected_id": "blog",
        }

        self.render_jinja2_template('about/viewblog.html', dict_context)

class ViewBlogPost(util_about.AboutRequestHandler):

    def get(self):
        post_id = None

        path = self.request.path
        partition = path.rpartition('/')

        try:
            post_id = int(partition[2])
        except ValueError:
            pass

        if not post_id:
            partition = partition[0].rpartition('/')
            try:
                post_id = int(partition[2])
            except ValueError:
                pass

        if not post_id:
            self.redirect("/about/blog")
            return

        force_refresh = self.request_bool("force_refresh", default=False)

        try:
            post = get_single_post(post_id, force_refresh)
        except TumblrException:
            post = TumblrDownBlogPost()

        self.render_jinja2_template('about/viewblogpost.html', {"post": post, "selected_id": "blog"})
