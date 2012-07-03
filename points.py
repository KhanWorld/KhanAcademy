import math
import consts
from accuracy_model.accuracy_model import AccuracyModel

MIN_STREAK_TILL_PROFICIENCY = AccuracyModel.min_streak_till_threshold(consts.PROFICIENCY_ACCURACY_THRESHOLD)

# user_exercise is a user_exercise object
# suggested and proficient are both bools
# offset is used to derive a point value for the nth + offset problem (i.e. to get the current or last point value)
# with offset = 0, ExercisePointCalculator yields the point value for the *next* correct exercise.
# with offset = -1, ExercisePointCalculator yields the point value for the last correct exercise.
def ExercisePointCalculator(user_exercise, suggested, proficient, offset=0):

    points = 0
    
    required_streak = MIN_STREAK_TILL_PROFICIENCY
    degrade_threshold = required_streak + consts.DEGRADING_EXERCISES_AFTER_PROFICIENCY

    if user_exercise.longest_streak + offset <= required_streak:
        # Have never hit a streak, higher base than normal
        points = consts.INCOMPLETE_EXERCISE_POINTS_BASE
    elif user_exercise.longest_streak + offset < degrade_threshold:
        # Significantly past hitting a streak, start to degrade points
        points = degrade_threshold - user_exercise.longest_streak - offset

    if (points < consts.EXERCISE_POINTS_BASE):
        # Never award less than a few points
        points = consts.EXERCISE_POINTS_BASE
    
    if user_exercise.summative:
        # Slightly higher rewards for summative exercises
        points = points * consts.SUMMATIVE_EXERCISE_MULTIPLIER

    if suggested:
        # Higher awards for suggested
        points = points * consts.SUGGESTED_EXERCISE_MULTIPLIER

    if not proficient:
        # Higher awards for not being currently proficient
        points = points * consts.INCOMPLETE_EXERCISE_MULTIPLIER

    if not user_exercise.summative and user_exercise.total_done >= consts.LIMIT_EXERCISES_NON_SUMMATIVE:
        # Non-summative exercises can be gamed by getting 9 correct, then 1 wrong. Put an upper limit
        # on the number of problems that continue to award useful points for non-summative.
        points = consts.EXERCISE_POINTS_BASE

    return int(math.ceil(points))

def VideoPointCalculator(user_video):
    if user_video.duration is None or user_video.duration <= 0:
        return 0
    
    seconds_credit = min(user_video.seconds_watched, user_video.duration)

    credit_multiplier = float(seconds_credit) / float(user_video.duration)
    if credit_multiplier >= consts.REQUIRED_PERCENTAGE_FOR_FULL_VIDEO_POINTS:
        credit_multiplier = 1.0

    points = consts.VIDEO_POINTS_BASE * credit_multiplier

    return int(math.ceil(points))
