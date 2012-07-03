from badges import BadgeCategory
from exercise_badges import ExerciseBadge

# All badges awarded for just barely missing proficiency even though most
# questions are being answered correctly inherit from this class
class UnfinishedExerciseBadge(ExerciseBadge):

    def is_satisfied_by(self, *args, **kwargs):
        user_data = kwargs.get("user_data", None)
        user_exercise = kwargs.get("user_exercise", None)
        action_cache = kwargs.get("action_cache", None)

        if user_data is None or user_exercise is None or action_cache is None:
            return False

        # Make sure they've done the required minimum of problems in this exercise
        if user_exercise.total_done < self.problems_required:
            return False

        # Make sure they haven't yet reached proficiency
        if user_data.is_proficient_at(user_exercise.exercise):
            return False

        c_logs = len(action_cache.problem_logs)

        # We need a history of at least 10 problem_logs in the action cache
        if c_logs < 10:
            return False

        # Make sure the last problem is from this exercise and that they got it right
        last_problem_log = action_cache.get_problem_log(c_logs - 1)
        if (last_problem_log.exercise != user_exercise.exercise or not last_problem_log.correct):
            return False

        c_correct = 0
        c_total = 0
        c_logs_examined = min(50, c_logs)

        # Look through the last 50 problems. If they've done at least 10 in the exercise
        # and gotten at least 75% correct, give 'em the badge.
        for i in range(c_logs_examined):

            problem_log = action_cache.get_problem_log(c_logs - i - 1)

            if problem_log.exercise == user_exercise.exercise:
                c_total += 1
                if problem_log.correct:
                    c_correct += 1

        # Make sure they've done at least 10 problems in this exercise out of their last 50
        if c_total < 10:
            return False

        # Make sure they've gotten at least 75% of their recent answers correct
        if (float(c_correct) / float(c_total)) < 0.75:
            return False

        return True

    def extended_description(self):
        return "Answer more than %d problems mostly correctly in an exercise before becoming proficient" % self.problems_required

class SoCloseBadge(UnfinishedExerciseBadge):

    def __init__(self):
        UnfinishedExerciseBadge.__init__(self)
        self.problems_required = 30
        self.description = "Perseverance"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 0

class KeepFightingBadge(UnfinishedExerciseBadge):

    def __init__(self):
        UnfinishedExerciseBadge.__init__(self)
        self.problems_required = 40
        self.description = "Steadfastness"
        self.badge_category = BadgeCategory.SILVER
        self.points = 0

class UndeterrableBadge(UnfinishedExerciseBadge):

    def __init__(self):
        UnfinishedExerciseBadge.__init__(self)
        self.problems_required = 50
        self.description = "Tenacity"
        self.badge_category = BadgeCategory.SILVER
        self.points = 0

