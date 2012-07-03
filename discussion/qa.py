import os
import logging

from google.appengine.api import users
from google.appengine.ext import db
from mapreduce import control
from mapreduce import operation as op

from collections import defaultdict

import models
import models_discussion
import notification
import util_discussion
import app
import util
import request_handler
import privileges
import voting
from phantom_users.phantom_util import disallow_phantoms
from rate_limiter import FlagRateLimiter

class ModeratorList(request_handler.RequestHandler):
    def get(self):

        # Must be an admin to change moderators
        if not users.is_current_user_admin():
            return

        mods = models.UserData.gql("WHERE moderator = :1", True)
        self.render_jinja2_template('discussion/mod_list.html', {"mods" : mods})

    def post(self):

        # Must be an admin to change moderators
        if not users.is_current_user_admin():
            return

        user_data = self.request_user_data("user")

        if user_data:
            user_data.moderator = self.request_bool("mod")
            db.put(user_data)

        self.redirect("/discussion/moderatorlist")

class FlaggedFeedback(request_handler.RequestHandler):
    def get(self):

        if not util_discussion.is_current_user_moderator():
            self.redirect(users.create_login_url(self.request.uri))
            return

        # Show all non-deleted feedback flagged for moderator attention
        feedback_query = models_discussion.Feedback.all().filter("is_flagged = ", True).filter("deleted = ", False)

        feedback_count = feedback_query.count()
        feedbacks = feedback_query.fetch(50)

        template_content = {
                "feedbacks": feedbacks, 
                "feedback_count": feedback_count,
                "has_more": len(feedbacks) < feedback_count,
                "feedback_type_question": models_discussion.FeedbackType.Question,
                "feedback_type_comment": models_discussion.FeedbackType.Comment,
                }

        self.render_jinja2_template("discussion/flagged_feedback.html", template_content)

def feedback_flag_update_map(feedback):
    feedback.recalculate_flagged()
    yield op.db.Put(feedback)

class StartNewFlagUpdateMapReduce(request_handler.RequestHandler):
    def get(self):
        mapreduce_id = control.start_map(
                name = "FeedbackFlagUpdate",
                handler_spec = "discussion.qa.feedback_flag_update_map",
                reader_spec = "mapreduce.input_readers.DatastoreInputReader",
                reader_parameters = {"entity_kind": "discussion.models_discussion.Feedback"},
                shard_count = 64,
                queue_name = "backfill-mapreduce-queue",
                )
        self.response.out.write("OK: " + str(mapreduce_id))

class ExpandQuestion(request_handler.RequestHandler):
    def post(self):
        notification.clear_question_answers_for_current_user(self.request.get("qa_expand_key"))

class PageQuestions(request_handler.RequestHandler):
    def get(self):

        page = 0
        try:
            page = int(self.request.get("page"))
        except:
            pass

        video_key = self.request.get("video_key")
        playlist_key = self.request.get("playlist_key")
        qa_expand_key = self.request_string("qa_expand_key")
        sort = self.request_int("sort", default=-1)

        try:
            video = db.get(video_key)
        except db.BadRequestError:
            # Temporarily ignore errors caused by cached google pages of non-HR app
            return

        playlist = db.get(playlist_key)

        user_data = models.UserData.current()

        if video:
            template_values = video_qa_context(user_data, video, playlist, page, qa_expand_key, sort)
            html = self.render_jinja2_template_to_string("discussion/video_qa_content.html", template_values)
            self.render_json({"html": html, "page": page, "qa_expand_key": qa_expand_key})

        if qa_expand_key > 0:
            # If a QA question is being expanded, we want to clear notifications for its
            # answers before we render page_template so the notification icon shows
            # its updated count. 
            notification.clear_question_answers_for_current_user(qa_expand_key)

        return

class AddAnswer(request_handler.RequestHandler):
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

        answer_text = self.request.get("answer_text")
        video_key = self.request.get("video_key")
        question_key = self.request.get("question_key")

        video = db.get(video_key)
        question = db.get(question_key)

        if answer_text and video and question:

            answer = models_discussion.Feedback(parent=user_data)
            answer.set_author(user_data)
            answer.content = answer_text
            answer.targets = [video.key(), question.key()]
            answer.types = [models_discussion.FeedbackType.Answer]

            # We don't limit answer.content length, which means we're vulnerable to
            # RequestTooLargeErrors being thrown if somebody submits a POST over the GAE
            # limit of 1MB per entity.  This is *highly* unlikely for a legitimate piece of feedback,
            # and we're choosing to crash in this case until someone legitimately runs into this.
            # See Issue 841.
            answer.put()
            notification.new_answer_for_video_question(video, question, answer)

        self.redirect("/discussion/answers?question_key=%s" % question_key)

class Answers(request_handler.RequestHandler):
    def get(self):
        user_data = models.UserData.current()
        question_key = self.request.get("question_key")
        question = db.get(question_key)

        if question:
            video = question.video()
            dict_votes = models_discussion.FeedbackVote.get_dict_for_user_data_and_video(user_data, video)

            answers = models_discussion.Feedback.gql("WHERE types = :1 AND targets = :2 AND deleted = :3 AND is_hidden_by_flags = :4", models_discussion.FeedbackType.Answer, question.key(), False, False).fetch(1000)
            answers = voting.VotingSortOrder.sort(answers)

            for answer in answers:
                voting.add_vote_expando_properties(answer, dict_votes)

            template_values = {
                "answers": answers,
                "is_mod": util_discussion.is_current_user_moderator()
            }

            html = self.render_jinja2_template_to_string('discussion/question_answers_only.html', template_values)
            self.render_json({"html": html})

        return

class AddQuestion(request_handler.RequestHandler):
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

        question_text = self.request.get("question_text")
        video_key = self.request.get("video_key")
        playlist_key = self.request.get("playlist_key")
        video = db.get(video_key)
        question_key = ""

        if question_text and video:
            if len(question_text) > 500:
                question_text = question_text[0:500] # max question length, also limited by client

            question = models_discussion.Feedback(parent=user_data)
            question.set_author(user_data)
            question.content = question_text
            question.targets = [video.key()]
            question.types = [models_discussion.FeedbackType.Question]
            question.put()
            question_key = question.key()

        self.redirect("/discussion/pagequestions?video_key=%s&playlist_key=%s&qa_expand_key=%s" % 
                (video_key, playlist_key, question_key))

class EditEntity(request_handler.RequestHandler):
    @disallow_phantoms
    def post(self):
        user_data = models.UserData.current()
        if not user_data:
            return

        key = self.request.get("entity_key")
        playlist_key = self.request.get("playlist_key")
        text = self.request.get("question_text") or self.request.get("answer_text")

        if key and text:
            feedback = db.get(key)
            if feedback:
                if feedback.authored_by(user_data) or util_discussion.is_current_user_moderator():

                    feedback.content = text
                    feedback.put()

                    # Redirect to appropriate list of entities depending on type of 
                    # feedback entity being edited.
                    if feedback.is_type(models_discussion.FeedbackType.Question):

                        page = self.request.get("page")
                        video = feedback.video()
                        self.redirect("/discussion/pagequestions?video_key=%s&playlist_key=%s&page=%s&qa_expand_key=%s" % 
                                        (video.key(), playlist_key, page, feedback.key()))

                    elif feedback.is_type(models_discussion.FeedbackType.Answer):

                        question = feedback.question()
                        self.redirect("/discussion/answers?question_key=%s" % question.key())

class FlagEntity(request_handler.RequestHandler):
    @disallow_phantoms
    def post(self):
        # You have to at least be logged in to flag
        user_data = models.UserData.current()
        if not user_data:
            return

        limiter = FlagRateLimiter(user_data)
        if not limiter.increment():
            self.render_json({"error": limiter.denied_desc()})
            return

        key = self.request_string("entity_key", default="")
        flag = self.request_string("flag", default="")
        if key and models_discussion.FeedbackFlag.is_valid(flag):
            entity = db.get(key)
            if entity and entity.add_flag_by(flag, user_data):
                entity.put()

class ClearFlags(request_handler.RequestHandler):
    def post(self):
        if not util_discussion.is_current_user_moderator():
            return

        key = self.request.get("entity_key")
        if key:
            entity = db.get(key)
            if entity:
                entity.clear_flags()
                entity.put()

        self.redirect("/discussion/flaggedfeedback")

class ChangeEntityType(request_handler.RequestHandler):
    def post(self):
        # Must be a moderator to change types of anything
        if not util_discussion.is_current_user_moderator():
            return

        key = self.request.get("entity_key")
        target_type = self.request.get("target_type")
        if key and models_discussion.FeedbackType.is_valid(target_type):
            entity = db.get(key)
            if entity:
                entity.types = [target_type]

                if self.request_bool("clear_flags", default=False):
                    entity.clear_flags()

                entity.put()

        self.redirect("/discussion/flaggedfeedback")

class DeleteEntity(request_handler.RequestHandler):
    @disallow_phantoms
    def post(self):
        user_data = models.UserData.current()
        if not user_data:
            return

        key = self.request.get("entity_key")
        if key:
            entity = db.get(key)
            if entity:
                # Must be a moderator or author of entity to delete
                if entity.authored_by(user_data) or util_discussion.is_current_user_moderator():
                    entity.deleted = True
                    entity.put()

        self.redirect("/discussion/flaggedfeedback")

def video_qa_context(user_data, video, playlist=None, page=0, qa_expand_key=None, sort_override=-1):
    limit_per_page = 5

    if page <= 0:
        page = 1

    sort_order = voting.VotingSortOrder.HighestPointsFirst
    if user_data:
        sort_order = user_data.question_sort_order
    if sort_override >= 0:
        sort_order = sort_override

    questions = util_discussion.get_feedback_by_type_for_video(video, models_discussion.FeedbackType.Question, user_data)
    questions = voting.VotingSortOrder.sort(questions, sort_order=sort_order)

    if qa_expand_key:
        # If we're showing an initially expanded question,
        # make sure we're on the correct page
        question = models_discussion.Feedback.get(qa_expand_key)
        if question:
            count_preceding = 0
            for question_test in questions:
                if question_test.key() == question.key():
                    break
                count_preceding += 1
            page = 1 + (count_preceding / limit_per_page)

    answers = util_discussion.get_feedback_by_type_for_video(video, models_discussion.FeedbackType.Answer, user_data)
    answers.reverse() # Answers are initially in date descending -- we want ascending before the points sort
    answers = voting.VotingSortOrder.sort(answers)

    dict_votes = models_discussion.FeedbackVote.get_dict_for_user_data_and_video(user_data, video)

    count_total = len(questions)
    questions = questions[((page - 1) * limit_per_page):(page * limit_per_page)]

    dict_questions = {}
    # Store each question in this page in a dict for answer population
    for question in questions:
        voting.add_vote_expando_properties(question, dict_votes)
        dict_questions[question.key()] = question

    # Just grab all answers for this video and cache in page's questions
    for answer in answers:
        # Grab the key only for each answer, don't run a full gql query on the ReferenceProperty
        question_key = answer.question_key()
        if (dict_questions.has_key(question_key)):
            question = dict_questions[question_key]
            voting.add_vote_expando_properties(answer, dict_votes)
            question.children_cache.append(answer)

    count_page = len(questions)
    pages_total = max(1, ((count_total - 1) / limit_per_page) + 1)
    return {
            "is_mod": util_discussion.is_current_user_moderator(),
            "video": video,
            "playlist": playlist,
            "questions": questions,
            "count_total": count_total,
            "pages": range(1, pages_total + 1),
            "pages_total": pages_total,
            "prev_page_1_based": page - 1,
            "current_page_1_based": page,
            "next_page_1_based": page + 1,
            "show_page_controls": pages_total > 1,
            "qa_expand_key": qa_expand_key,
            "sort_order": sort_order,
           }

def add_template_values(dict, request):
    dict["comments_page"] = int(request.get("comments_page")) if request.get("comments_page") else 0
    dict["qa_page"] = int(request.get("qa_page")) if request.get("qa_page") else 0
    dict["qa_expand_key"] = request.get("qa_expand_key")
    dict["sort"] = int(request.get("sort")) if request.get("sort") else -1

    return dict
