import os

from google.appengine.api import users
from google.appengine.ext import db

import simplejson

import models
import models_discussion
import util_discussion
import app
import util
import request_handler
import voting
from phantom_users.phantom_util import disallow_phantoms

class PageComments(request_handler.RequestHandler):
    def get(self):
        page = 0
        try:
            page = int(self.request.get("page"))
        except:
            pass

        video_key = self.request.get("video_key")
        playlist_key = self.request.get("playlist_key")
        sort_order = self.request_int("sort_order", default=voting.VotingSortOrder.HighestPointsFirst)

        try:
            video = db.get(video_key)
        except db.BadRequestError:
            # Temporarily ignore errors caused by cached google pages of non-HR app
            return

        playlist = db.get(playlist_key)

        if video:
            comments_hidden = self.request_bool("comments_hidden", default=True)
            template_values = video_comments_context(video, playlist, page, comments_hidden, sort_order)

            html = self.render_jinja2_template_to_string("discussion/video_comments_content.html", template_values)
            json = simplejson.dumps({"html": html, "page": page}, ensure_ascii=False)
            self.response.out.write(json)

class AddComment(request_handler.RequestHandler):
    @disallow_phantoms
    def post(self):
        user_data = models.UserData.current()

        if not user_data:
            self.redirect(util.create_login_url(self.request.uri))
            return

        if not util_discussion.is_honeypot_empty(self.request):
            # Honeypot caught a spammer (in case this is ever public or spammers
            # have google accounts)!
            return

        comment_text = self.request.get("comment_text")
        comments_hidden = self.request.get("comments_hidden")
        video_key = self.request.get("video_key")
        playlist_key = self.request.get("playlist_key")
        video = db.get(video_key)

        if comment_text and video:
            if len(comment_text) > 300:
                comment_text = comment_text[0:300] # max comment length, also limited by client

            comment = models_discussion.Feedback(parent=user_data)
            comment.set_author(user_data)
            comment.content = comment_text
            comment.targets = [video.key()]
            comment.types = [models_discussion.FeedbackType.Comment]
            comment.put()

        self.redirect("/discussion/pagecomments?video_key=%s&playlist_key=%s&page=0&comments_hidden=%s&sort_order=%s" % 
                (video_key, playlist_key, comments_hidden, voting.VotingSortOrder.NewestFirst))

def video_comments_context(video, playlist, page=0, comments_hidden=True, sort_order=voting.VotingSortOrder.HighestPointsFirst):

    user_data = models.UserData.current()

    if page > 0:
        comments_hidden = False # Never hide questions if specifying specific page
    else:
        page = 1

    limit_per_page = 10
    limit_initially_visible = 2 if comments_hidden else limit_per_page

    comments = util_discussion.get_feedback_by_type_for_video(video, models_discussion.FeedbackType.Comment, user_data)
    comments = voting.VotingSortOrder.sort(comments, sort_order=sort_order)

    count_total = len(comments)
    comments = comments[((page - 1) * limit_per_page):(page * limit_per_page)]

    dict_votes = models_discussion.FeedbackVote.get_dict_for_user_data_and_video(user_data, video)
    for comment in comments:
        voting.add_vote_expando_properties(comment, dict_votes)

    count_page = len(comments)
    pages_total = max(1, ((count_total - 1) / limit_per_page) + 1)
    return {
            "is_mod": util_discussion.is_current_user_moderator(),
            "video": video,
            "playlist": playlist,
            "comments": comments,
            "count_total": count_total,
            "comments_hidden": count_page > limit_initially_visible,
            "limit_initially_visible": limit_initially_visible,
            "pages": range(1, pages_total + 1),
            "pages_total": pages_total,
            "prev_page_1_based": page - 1,
            "current_page_1_based": page,
            "next_page_1_based": page + 1,
            "show_page_controls": pages_total > 1,
           }
