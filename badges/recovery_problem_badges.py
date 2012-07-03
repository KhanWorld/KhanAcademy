from badges import BadgeCategory
from exercise_badges import ExerciseBadge

# All badges awarded for getting exercise problems correct after having some trouble inherit from RecoveryProblemBadge
class RecoveryProblemBadge(ExerciseBadge):

    def is_satisfied_by(self, *args, **kwargs):
        user_exercise = kwargs.get("user_exercise", None)
        action_cache = kwargs.get("action_cache", None)

        if user_exercise is None or action_cache is None:
            return False

        c_logs = len(action_cache.problem_logs)
        if c_logs >= self.problems_wrong_out_of:

            # Make sure they got the last problem correct in this exercise
            last_problem_log = action_cache.get_problem_log(c_logs - 1)
            if (last_problem_log.exercise != user_exercise.exercise or not last_problem_log.correct):
                return False

            # Make sure they got the second-to-last problem wrong in this exercise
            second_last_problem_log = action_cache.get_problem_log(c_logs - 2)
            if (second_last_problem_log.exercise != user_exercise.exercise or second_last_problem_log.correct):
                return False

            c_wrong = 0

            for i in range(self.problems_wrong_out_of):

                problem_log = action_cache.get_problem_log(c_logs - i - 1)

                # Make sure they stick with the same exercise and aren't jumping around
                if problem_log.exercise != user_exercise.exercise:
                    return False

                if not problem_log.correct:
                    c_wrong += 1

            return c_wrong >= self.problems_wrong

        return False

    def extended_description(self):
        return "Answer an exercise problem correctly after having some trouble with %s and sticking with the exercise." % self.s_problems_description

class RecoveryBadge(RecoveryProblemBadge):

    def __init__(self):
        RecoveryProblemBadge.__init__(self)
        self.problems_wrong = 5
        self.problems_wrong_out_of = 10
        self.description = "Persistence"
        self.s_problems_description = "a few problems"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 0

class ResurrectionBadge(RecoveryProblemBadge):

    def __init__(self):
        RecoveryProblemBadge.__init__(self)
        self.problems_wrong = 10
        self.problems_wrong_out_of = 20
        self.description = "Sticktoitiveness"
        self.s_problems_description = "many problems"
        self.badge_category = BadgeCategory.SILVER
        self.points = 0
