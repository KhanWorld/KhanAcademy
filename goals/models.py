# -*- coding: utf-8 -*-

from __future__ import absolute_import
from datetime import datetime

from google.appengine.ext import db

from object_property import ObjectProperty
from templatefilters import timesince_ago, seconds_to_time_string

from models import Exercise, UserVideo, Video


class Goal(db.Model):
    # data
    title = db.StringProperty(indexed=False)
    objectives = ObjectProperty()

    # a goal is 'completed' if it's finished or abandoned. This property is
    # indexed so that we can quickly fetch currently open goals
    completed = db.BooleanProperty(default=False)
    completed_on = db.DateTimeProperty(indexed=False)

    # we distinguish finished and abandoned goals with this property
    abandoned = db.BooleanProperty(indexed=False)

    created_on = db.DateTimeProperty(auto_now_add=True, indexed=False)
    updated_on = db.DateTimeProperty(auto_now=True, indexed=False)

    def get_visible_data(self, user_exercise_graph=None):
        data = dict(
            id=self.key().id(),
            title=self.title,
            created=self.created_on,
            created_ago=timesince_ago(self.created_on),
            updated=self.updated_on,
            updated_ago=timesince_ago(self.updated_on),
            completed=self.completed_on,
            abandoned=self.abandoned,
        )

        if self.completed:
            data['completed_ago'] = timesince_ago(self.completed_on)
            td = self.completed_on - self.created_on
            completed_seconds = (td.seconds + td.days * 24 * 3600)
            data['completed_time'] = seconds_to_time_string(completed_seconds)

        data['objectives'] = [dict(
                type=obj.__class__.__name__,
                description=obj.description,
                progress=obj.progress,
                url=obj.url(),
                internal_id=obj.internal_id(),
                status=obj.get_status(user_exercise_graph=user_exercise_graph),
            ) for obj in self.objectives]

        return data

    def record_complete(self):
        if all([o.completed for o in self.objectives]):
            self.completed = True
            self.completed_on = datetime.now()

    def abandon(self):
        self.completed = True
        self.completed_on = datetime.now()
        self.abandoned = True

    def just_watched_video(self, user_data, user_video, just_finished):
        changed = False
        for objective in self.objectives:
            if isinstance(objective, GoalObjectiveWatchVideo):
                if objective.record_progress(user_data, user_video):
                    changed = True

        if just_finished:
            any_videos = [o for o in self.objectives
                if isinstance(o, GoalObjectiveAnyVideo)]
            found = user_video.video.key() in [o.video_key for o in any_videos]
            if not found:
                for vid_obj in any_videos:
                    if not vid_obj.completed:
                        vid_obj.record_complete(user_video.video)
                        changed = True
                        break

        if changed:
            self.record_complete()

        return changed

    def just_did_exercise(self, user_data, user_exercise, became_proficient):
        changed = False
        for ex_obj in self.objectives:
            if isinstance(ex_obj, GoalObjectiveExerciseProficiency):
                if ex_obj.record_progress(user_data, user_exercise):
                    changed = True

        if became_proficient:
            any_exercises = [o for o in self.objectives
                if isinstance(o, GoalObjectiveAnyExerciseProficiency)]
            found = user_exercise.exercise in [o.exercise_name for o in
                any_exercises]
            if not found:
                for ex_obj in any_exercises:
                    if not ex_obj.completed:
                        ex_obj.record_complete(user_exercise.exercise_model)
                        changed = True
                        break

        if changed:
            self.record_complete()

        return changed

# todo: think about moving these static methods to UserData. Almost all have
# user_data as the first argument.
class GoalList(object):
    # might need to request_cache this
    @staticmethod
    def get_current_goals(user_data):
        if user_data and user_data.has_current_goals:
            query = GoalList.get_goals_query(user_data)
            query.filter('completed = ', False)
            return query.fetch(100)
        else:
            return []

    @staticmethod
    def get_all_goals(user_data):
        if user_data:
            return GoalList.get_goals_query(user_data).fetch(1000)
        else:
            return []

    @staticmethod
    def get_goals_query(user_data):
        query = Goal.all()
        query.ancestor(user_data)
        return query

    @staticmethod
    def delete_all_goals(user_data):
        if not user_data:
            return

        query = Goal.all(keys_only=True)
        query.ancestor(user_data)
        goal_keys = query.fetch(1000)
        db.delete(goal_keys)

    @staticmethod
    def exercises_in_current_goals(user_data):
        goals = GoalList.get_current_goals(user_data)
        return [obj.exercise_name for g in goals for obj in g.objectives
            if obj.__class__.__name__ == 'GoalObjectiveExerciseProficiency']

    @staticmethod
    def videos_in_current_goals(user_data):
        goals = GoalList.get_current_goals(user_data)
        return [obj.video_readable_id for g in goals for obj in g.objectives
            if obj.__class__.__name__ == 'GoalObjectiveWatchVideo']

    @staticmethod
    def update_goals(user_data, activity_fn):
        if not user_data.has_current_goals:
            return False

        goals = GoalList.get_current_goals(user_data)
        changes = []
        for goal in goals:
            if activity_fn(goal):
                changes.append(goal)
        if changes:
            # check to see if all goals are closed
            user_changes = []
            if all([g.completed for g in goals]):
                user_data.has_current_goals = False
                user_changes = [user_data]
            db.put(changes + user_changes)
        return changes


class GoalObjective(object):
    # Objective status
    progress = 0.0
    description = None

    def __init__(self, description):
        self.description = description

    def url():
        '''url to which the objective points when used as a nav bar.'''
        raise Exception

    def record_progress(self):
        return False

    def record_complete(self):
        self.progress = 1.0

    @property
    def completed(self):
        return self.progress >= 1.0

    def get_status(self, **kwargs):
        if self.completed:
            return "proficient"

        if self.progress > 0:
            return "started"

        return ""

    @staticmethod
    def from_descriptors(descriptors, user_data):
        objs = []
        for desc in descriptors:
            if desc['type'] == 'GoalObjectiveExerciseProficiency':
                objs.append(GoalObjectiveExerciseProficiency(desc['exercise'],
                    user_data))
            elif desc['type'] == 'GoalObjectiveWatchVideo':
                objs.append(GoalObjectiveWatchVideo(desc['video'], user_data))
            elif desc['type'] == "GoalObjectiveAnyExerciseProficiency":
                objs.append(GoalObjectiveAnyExerciseProficiency(
                    description="Any exercise"))
            elif desc['type'] == "GoalObjectiveAnyVideo":
                objs.append(GoalObjectiveAnyVideo(description="Any video"))
        return objs


class GoalObjectiveExerciseProficiency(GoalObjective):
    # Objective definition (Chosen at goal creation time)
    exercise_name = None

    def __init__(self, exercise, user_data):
        self.exercise_name = exercise.name
        self.description = exercise.display_name
        self.progress = user_data.get_or_insert_exercise(exercise).progress

    def url(self):
        exercise = Exercise.get_by_name(self.exercise_name)
        return exercise.relative_url

    def internal_id(self):
        return self.exercise_name

    def record_progress(self, user_data, user_exercise):
        if self.exercise_name == user_exercise.exercise:
            if user_data.is_proficient_at(user_exercise.exercise):
                self.progress = 1.0
            else:
                self.progress = user_exercise.progress
            return True

        return False

    def get_status(self, user_exercise_graph=None):
        if not user_exercise_graph:
            # fall back to ['', 'started', 'proficient']
            return super(GoalObjectiveExerciseProficiency, self).get_status()

        graph_dict = user_exercise_graph.graph_dict(self.exercise_name)
        status = ""
        if graph_dict["proficient"]:
            status = "proficient"
        elif graph_dict["struggling"]:
            status = "struggling"
        elif graph_dict["total_done"] > 0:
            status = "started"
        return status

class GoalObjectiveAnyExerciseProficiency(GoalObjective):
    # which exercise fulfilled this objective, set upon completion
    exercise_name = None

    def url(self):
        if self.exercise_name:
            return Exercise.get_relative_url(self.exercise_name)
        else:
            return "/exercisedashboard"

    def internal_id(self):
        return ''

    def record_complete(self, exercise):
        super(GoalObjectiveAnyExerciseProficiency, self).record_complete()
        self.exercise_name = exercise.name
        self.description = exercise.display_name
        return True

class GoalObjectiveWatchVideo(GoalObjective):
    # Objective definition (Chosen at goal creation time)
    video_key = None
    video_readable_id = None

    def __init__(self, video, user_data):
        self.video_key = video.key()
        self.video_readable_id = video.readable_id
        self.description = video.title

        user_video = UserVideo.get_for_video_and_user_data(video, user_data)
        if user_video:
            self.progress = user_video.progress
        else:
            self.progress = 0.0

    def url(self):
        return Video.get_relative_url(self.video_readable_id)

    def internal_id(self):
        return self.video_readable_id

    def record_progress(self, user_data, user_video):
        obj_key = self.video_key
        video_key = UserVideo.video.get_value_for_datastore(user_video)
        if obj_key == video_key:
            self.progress = user_video.progress
            return True
        return False

class GoalObjectiveAnyVideo(GoalObjective):
    # which video fulfilled this objective, set upon completion
    video_key = None
    video_readable_id = None

    def url(self):
        if self.video_readable_id:
            return Video.get_relative_url(self.video_readable_id)
        else:
            return "/#browse"

    def internal_id(self):
        return ''

    def record_complete(self, video):
        super(GoalObjectiveAnyVideo, self).record_complete()
        self.video_key = video.key()
        self.video_readable_id = video.readable_id
        self.description = video.title
        return True
