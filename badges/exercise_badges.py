import models
from badges import Badge, BadgeContextType

# All badges that may be awarded once-per-Exercise inherit from ExerciseBadge
class ExerciseBadge(Badge):

    def __init__(self):
        Badge.__init__(self)
        self.badge_context_type = BadgeContextType.EXERCISE

    def is_already_owned_by(self, user_data, *args, **kwargs):
        user_exercise = kwargs.get("user_exercise", None)
        if user_exercise is None:
            return False

        return self.name_with_target_context(models.Exercise.to_display_name(user_exercise.exercise)) in user_data.badges

    def award_to(self, user_data, *args, **kwargs):
        user_exercise = kwargs.get("user_exercise", None)
        if user_exercise is None:
            return False

        self.complete_award_to(user_data, user_exercise.exercise_model, models.Exercise.to_display_name(user_exercise.exercise))

