import urllib

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.api import taskqueue
from mapreduce import control
from mapreduce import operation as op

from privileges import Privileges
from rate_limiter import VoteRateLimiter
from models import UserData
from models_discussion import FeedbackVote
import request_handler
import util

class VotingSortOrder:
    HighestPointsFirst = 1
    NewestFirst = 2

    @staticmethod
    def sort(entities, sort_order=-1):
        if not sort_order in (VotingSortOrder.HighestPointsFirst, VotingSortOrder.NewestFirst):
            sort_order = VotingSortOrder.HighestPointsFirst

        if sort_order == VotingSortOrder.NewestFirst:
            return sorted(entities, key=lambda entity: entity.date, reverse=True)
        else:
            return sorted(entities, key=lambda entity: entity.inner_score, reverse=True)

class UpdateQASort(request_handler.RequestHandler):
    def get(self):
        user_data = UserData.current()
        sort = self.request_int("sort", default=VotingSortOrder.HighestPointsFirst)

        if user_data:
            user_data.question_sort_order = sort
            user_data.put()

        readable_id = self.request_string("readable_id", default="")
        playlist_title = self.request_string("playlist_title", default="")

        if readable_id and playlist_title:
            self.redirect("/video/%s?playlist=%s&sort=%s" % (urllib.quote(readable_id), urllib.quote(playlist_title), sort))
        else:
            self.redirect("/")

class VoteEntity(request_handler.RequestHandler):
    def post(self):
        # You have to be logged in to vote
        user_data = UserData.current()
        if not user_data:
            return

        vote_type = self.request_int("vote_type", default=FeedbackVote.ABSTAIN)

        if vote_type == FeedbackVote.UP and not Privileges.can_up_vote(user_data):
            self.render_json({"error": Privileges.need_points_desc(Privileges.UP_VOTE_THRESHOLD, "up vote")})
            return
        elif vote_type == FeedbackVote.DOWN and not Privileges.can_down_vote(user_data):
            self.render_json({"error": Privileges.need_points_desc(Privileges.DOWN_VOTE_THRESHOLD, "down vote")})
            return

        entity_key = self.request_string("entity_key", default="")
        if entity_key:
            entity = db.get(entity_key)
            if entity and entity.authored_by(user_data):
                self.render_json({"error": "You cannot vote for your own posts."})
                return

        if vote_type != FeedbackVote.ABSTAIN:
            limiter = VoteRateLimiter(user_data)
            if not limiter.increment():
                self.render_json({"error": limiter.denied_desc()})
                return

        # We kick off a taskqueue item to perform the actual vote insertion
        # so we don't have to worry about fast writes to the entity group 
        # causing contention problems for the HR datastore, because
        # the taskqueue will just retry w/ exponential backoff.
        taskqueue.add(url='/admin/discussion/finishvoteentity', queue_name='voting-queue', 
                params={
                    "email": user_data.email,
                    "vote_type": self.request_int("vote_type", default=FeedbackVote.ABSTAIN),
                    "entity_key": entity_key
                }
        )

class FinishVoteEntity(request_handler.RequestHandler):
    def post(self):

        user_data = self.request_user_data("email")

        vote_type = self.request_int("vote_type", default=FeedbackVote.ABSTAIN)

        key = self.request_string("entity_key", default="")
        if key:
            entity = db.get(key)
            if entity:
                entity.add_vote_by(vote_type, user_data)

class StartNewVoteMapReduce(request_handler.RequestHandler):

    def get(self):

        # Admin-only restriction is handled by /admin/* URL pattern
        # so this can be called by a cron job.

        # Start a new Mapper task for calling badge_update_map
        mapreduce_id = control.start_map(
                name = "UpdateFeedbackVotes",
                handler_spec = "discussion.voting.vote_update_map",
                reader_spec = "mapreduce.input_readers.DatastoreInputReader",
                reader_parameters = {"entity_kind": "discussion.models_discussion.Feedback"},
                queue_name = "backfill-mapreduce-queue",
                )

        self.response.out.write("OK: " + str(mapreduce_id))

def vote_update_map(feedback):
    feedback.update_votes_and_score()

def add_vote_expando_properties(feedback, dict_votes):
    feedback.up_voted = False
    feedback.down_voted = False
    if feedback.key() in dict_votes:
        vote = dict_votes[feedback.key()]
        feedback.up_voted = vote.is_up()
        feedback.down_voted = vote.is_down()
