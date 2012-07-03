import datetime
import sys

from google.appengine.api import taskqueue
from mapreduce import control

import models
import badges
import models_badges
import last_action_cache

import custom_badges
import streak_badges
import timed_problem_badges
import exercise_completion_badges
import exercise_completion_count_badges
import playlist_time_badges
import power_time_badges
import recovery_problem_badges
import unfinished_exercise_badges
import points_badges
import tenure_badges
import video_time_badges
import consecutive_activity_badges

import fast_slow_queue

import layer_cache
import request_handler

import logging

# Authoritative list of all badges
@layer_cache.cache()
def all_badges():
    list_badges = [
        exercise_completion_count_badges.GettingStartedBadge(),
        exercise_completion_count_badges.MakingProgressBadge(),
        exercise_completion_count_badges.HardAtWorkBadge(),
        exercise_completion_count_badges.WorkHorseBadge(),
        exercise_completion_count_badges.MagellanBadge(),
        exercise_completion_count_badges.CopernicusBadge(),
        exercise_completion_count_badges.AtlasBadge(),

        points_badges.TenThousandaireBadge(),
        points_badges.HundredThousandaireBadge(),
        points_badges.FiveHundredThousandaireBadge(),
        points_badges.MillionaireBadge(),
        points_badges.TenMillionaireBadge(),

        streak_badges.NiceStreakBadge(),
        streak_badges.GreatStreakBadge(),
        streak_badges.AwesomeStreakBadge(),
        streak_badges.RidiculousStreakBadge(),
        streak_badges.LudicrousStreakBadge(),

        playlist_time_badges.NicePlaylistTimeBadge(),
        playlist_time_badges.GreatPlaylistTimeBadge(),
        playlist_time_badges.AwesomePlaylistTimeBadge(),
        playlist_time_badges.RidiculousPlaylistTimeBadge(),
        playlist_time_badges.LudicrousPlaylistTimeBadge(),

        timed_problem_badges.NiceTimedProblemBadge(),
        timed_problem_badges.GreatTimedProblemBadge(),
        timed_problem_badges.AwesomeTimedProblemBadge(),
        timed_problem_badges.RidiculousTimedProblemBadge(),
        timed_problem_badges.LudicrousTimedProblemBadge(),

        recovery_problem_badges.RecoveryBadge(),
        recovery_problem_badges.ResurrectionBadge(),

        unfinished_exercise_badges.SoCloseBadge(),
        unfinished_exercise_badges.KeepFightingBadge(),
        unfinished_exercise_badges.UndeterrableBadge(),

        power_time_badges.PowerFifteenMinutesBadge(),
        power_time_badges.PowerHourBadge(),
        power_time_badges.DoublePowerHourBadge(),

        exercise_completion_badges.LevelOneArithmeticianBadge(),
        exercise_completion_badges.LevelTwoArithmeticianBadge(),
        exercise_completion_badges.LevelThreeArithmeticianBadge(),
        exercise_completion_badges.TopLevelArithmeticianBadge(),

        exercise_completion_badges.LevelOneTrigonometricianBadge(),
        exercise_completion_badges.LevelTwoTrigonometricianBadge(),
        exercise_completion_badges.LevelThreeTrigonometricianBadge(),
        exercise_completion_badges.TopLevelTrigonometricianBadge(),

        exercise_completion_badges.LevelOnePrealgebraistBadge(),
        exercise_completion_badges.LevelTwoPrealgebraistBadge(),
        exercise_completion_badges.LevelThreePrealgebraistBadge(),
        exercise_completion_badges.TopLevelPrealgebraistBadge(),

        exercise_completion_badges.LevelOneAlgebraistBadge(),
        exercise_completion_badges.LevelTwoAlgebraistBadge(),
        exercise_completion_badges.LevelThreeAlgebraistBadge(),
        exercise_completion_badges.LevelFourAlgebraistBadge(),
        exercise_completion_badges.LevelFiveAlgebraistBadge(),
        exercise_completion_badges.TopLevelAlgebraistBadge(),

        tenure_badges.YearOneBadge(),
        tenure_badges.YearTwoBadge(),
        tenure_badges.YearThreeBadge(),

        video_time_badges.ActOneSceneOneBadge(),

        consecutive_activity_badges.FiveDayConsecutiveActivityBadge(),
        consecutive_activity_badges.FifteenDayConsecutiveActivityBadge(),
        consecutive_activity_badges.ThirtyDayConsecutiveActivityBadge(),
        consecutive_activity_badges.HundredDayConsecutiveActivityBadge(),

    ]

    list_badges.extend(custom_badges.CustomBadge.all())
    return list_badges

@layer_cache.cache()
def all_badges_dict():
    dict_badges = {}
    for badge in all_badges():
        dict_badges[badge.name] = badge
    return dict_badges

def badges_with_context_type(badge_context_type):
    return filter(lambda badge: badge.badge_context_type == badge_context_type, all_badges())

def get_badge_counts(user_data):

    count_dict = badges.BadgeCategory.empty_count_dict()

    if not user_data:
        return count_dict

    badges_dict = all_badges_dict()

    for badge_name_with_context in user_data.badges:
        badge_name = badges.Badge.remove_target_context(badge_name_with_context)
        badge = badges_dict.get(badge_name)
        if badge:
            count_dict[badge.badge_category] += 1

    return count_dict

def get_user_badges(user_data = None):

    if not user_data:
        user_data = models.UserData.current()

    user_badges = []
    user_badges_dict = {}

    if user_data:
        user_badges = models_badges.UserBadge.get_for(user_data)
        badges_dict = all_badges_dict()
        user_badge_last = None
        for user_badge in user_badges:
            if user_badge_last and user_badge_last.badge_name == user_badge.badge_name:
                user_badge_last.count += 1
                if user_badge_last.count > 1:
                    user_badge_last.list_context_names_hidden.append(user_badge.target_context_name)
                else:
                    user_badge_last.list_context_names.append(user_badge.target_context_name)
            else:
                user_badge.badge = badges_dict.get(user_badge.badge_name)

                if user_badge.badge:
                    user_badge.badge.is_owned = True

                user_badge.count = 1
                user_badge.list_context_names = [user_badge.target_context_name]
                user_badge.list_context_names_hidden = []
                user_badge_last = user_badge
                user_badges_dict[user_badge.badge_name] = True

    possible_badges = all_badges()
    for badge in possible_badges:
        badge.is_owned = user_badges_dict.has_key(badge.name)

    user_badges = sorted(filter(lambda user_badge: hasattr(user_badge, "badge") and user_badge.badge is not None, user_badges), reverse=True, key=lambda user_badge:user_badge.date)
    possible_badges = sorted(possible_badges, key=lambda badge:badge.badge_category)

    user_badges_normal = filter(lambda user_badge: user_badge.badge.badge_category != badges.BadgeCategory.MASTER, user_badges)
    user_badges_master = filter(lambda user_badge: user_badge.badge.badge_category == badges.BadgeCategory.MASTER, user_badges)
    user_badges_diamond = filter(lambda user_badge: user_badge.badge.badge_category == badges.BadgeCategory.DIAMOND, user_badges)
    user_badges_platinum = filter(lambda user_badge: user_badge.badge.badge_category == badges.BadgeCategory.PLATINUM, user_badges)
    user_badges_gold = filter(lambda user_badge: user_badge.badge.badge_category == badges.BadgeCategory.GOLD, user_badges)
    user_badges_silver = filter(lambda user_badge: user_badge.badge.badge_category == badges.BadgeCategory.SILVER, user_badges)
    user_badges_bronze = filter(lambda user_badge: user_badge.badge.badge_category == badges.BadgeCategory.BRONZE, user_badges)

    bronze_badges = sorted(filter(lambda badge:badge.badge_category == badges.BadgeCategory.BRONZE, possible_badges), key=lambda badge:badge.points or sys.maxint)
    silver_badges = sorted(filter(lambda badge:badge.badge_category == badges.BadgeCategory.SILVER, possible_badges), key=lambda badge:badge.points or sys.maxint)
    gold_badges = sorted(filter(lambda badge:badge.badge_category == badges.BadgeCategory.GOLD, possible_badges), key=lambda badge:badge.points or sys.maxint)
    platinum_badges = sorted(filter(lambda badge:badge.badge_category == badges.BadgeCategory.PLATINUM, possible_badges), key=lambda badge:badge.points or sys.maxint)
    diamond_badges = sorted(filter(lambda badge:badge.badge_category == badges.BadgeCategory.DIAMOND, possible_badges), key=lambda badge:badge.points or sys.maxint)
    master_badges = sorted(filter(lambda badge:badge.badge_category == badges.BadgeCategory.MASTER, possible_badges), key=lambda badge:badge.points or sys.maxint)


    return { 'possible_badges': possible_badges,
             'user_badges': user_badges,
             'user_badges_normal': user_badges_normal,
             'user_badges_master': user_badges_master,
             "badge_collections": [bronze_badges, silver_badges, gold_badges, platinum_badges, diamond_badges, master_badges],
             'bronze_badges': user_badges_bronze,
             'silver_badges': user_badges_silver,
             'gold_badges': user_badges_gold,
             'platinum_badges': user_badges_platinum,
             'diamond_badges': user_badges_diamond, }

class ViewBadges(request_handler.RequestHandler):

    def get(self):

        user_badges = get_user_badges()

        template_values = {
                "user_badges_normal": user_badges['user_badges_normal'],
                "user_badges_master": user_badges['user_badges_master'],
                "badge_collections": user_badges['badge_collections'],
                "show_badge_frequencies": self.request_bool("show_badge_frequencies", default=False)
                }

        self.render_jinja2_template('viewbadges.html', template_values)

# /admin/badgestatistics is called periodically by a cron job
class BadgeStatistics(request_handler.RequestHandler):

    def get(self):
        # Admin-only restriction is handled by /admin/* URL pattern
        # so this can be called by a cron job.
        taskqueue.add(url='/admin/badgestatistics', queue_name='badge-statistics-queue', params={'start': '1'})
        self.response.out.write("Badge statistics task started.")

    def post(self):
        if not self.request_bool("start", default=False):
            return

        for badge in all_badges():

            badge_stat = models_badges.BadgeStat.get_or_insert_for(badge.name)

            if badge_stat and badge_stat.needs_update():
                badge_stat.update()
                badge_stat.put()

# /admin/startnewbadgemapreduce is called periodically by a cron job
class StartNewBadgeMapReduce(request_handler.RequestHandler):

    def get(self):

        # Admin-only restriction is handled by /admin/* URL pattern
        # so this can be called by a cron job.

        # Start a new Mapper task for calling badge_update_map
        mapreduce_id = control.start_map(
                name = "UpdateUserBadges",
                handler_spec = "badges.util_badges.badge_update_map",
                reader_spec = "mapreduce.input_readers.DatastoreInputReader",
                reader_parameters = {"entity_kind": "models.UserData"},
                mapreduce_parameters = {"processing_rate": 250},
                shard_count = 64,
                queue_name = fast_slow_queue.QUEUE_NAME,
                )

        self.response.out.write("OK: " + str(mapreduce_id))

def is_badge_review_waiting(user_data):
    if not user_data:
        return False

    if not user_data.user:
        return False

    if not user_data.user_id:
        logging.error("UserData with user and no current_user: %s" % user_data.email)
        return False

    if user_data.is_phantom:
        # Don't bother doing overnight badge reviews for phantom users -- we're not that worried about it,
        # and it reduces task queue stress.
        return False

    if not user_data.last_activity or (user_data.last_badge_review and user_data.last_activity <= user_data.last_badge_review):
        # No activity since last badge review, skip
        return False

    return True

@fast_slow_queue.handler(is_badge_review_waiting)
def badge_update_map(user_data):
    action_cache = last_action_cache.LastActionCache.get_for_user_data(user_data)

    # Update all no-context badges
    update_with_no_context(user_data, action_cache=action_cache)

    # Update all exercise-context badges
    for user_exercise in models.UserExercise.get_for_user_data(user_data):
        update_with_user_exercise(user_data, user_exercise, action_cache=action_cache)

    # Update all playlist-context badges
    for user_playlist in models.UserPlaylist.get_for_user_data(user_data):
        update_with_user_playlist(user_data, user_playlist, action_cache=action_cache)

    user_data.last_badge_review = datetime.datetime.now()
    user_data.put()

# Award this user any earned no-context badges.
def update_with_no_context(user_data, action_cache = None):
    possible_badges = badges_with_context_type(badges.BadgeContextType.NONE)
    action_cache = action_cache or last_action_cache.LastActionCache.get_for_user_data(user_data)

    awarded = False
    for badge in possible_badges:
        if not badge.is_already_owned_by(user_data=user_data):
            if badge.is_satisfied_by(user_data=user_data, action_cache=action_cache):
                badge.award_to(user_data=user_data)
                awarded = True

    return awarded

# Award this user any earned Exercise-context badges for the provided UserExercise.
def update_with_user_exercise(user_data, user_exercise, include_other_badges = False, action_cache = None):
    possible_badges = badges_with_context_type(badges.BadgeContextType.EXERCISE)
    action_cache = action_cache or last_action_cache.LastActionCache.get_for_user_data(user_data)

    awarded = False
    for badge in possible_badges:
        # Pass in pre-retrieved user_exercise data so each badge check doesn't have to talk to the datastore
        if not badge.is_already_owned_by(user_data=user_data, user_exercise=user_exercise):
            if badge.is_satisfied_by(user_data=user_data, user_exercise=user_exercise, action_cache=action_cache):
                badge.award_to(user_data=user_data, user_exercise=user_exercise)
                awarded = True

    if include_other_badges:
        awarded = update_with_no_context(user_data, action_cache=action_cache) or awarded

    return awarded

# Award this user any earned Playlist-context badges for the provided UserPlaylist.
def update_with_user_playlist(user_data, user_playlist, include_other_badges = False, action_cache = None):
    possible_badges = badges_with_context_type(badges.BadgeContextType.PLAYLIST)
    action_cache = action_cache or last_action_cache.LastActionCache.get_for_user_data(user_data)

    awarded = False
    for badge in possible_badges:
        # Pass in pre-retrieved user_playlist data so each badge check doesn't have to talk to the datastore
        if not badge.is_already_owned_by(user_data=user_data, user_playlist=user_playlist):
            if badge.is_satisfied_by(user_data=user_data, user_playlist=user_playlist, action_cache=action_cache):
                badge.award_to(user_data=user_data, user_playlist=user_playlist)
                awarded = True

    if include_other_badges:
        awarded = update_with_no_context(user_data, action_cache=action_cache) or awarded

    return awarded

