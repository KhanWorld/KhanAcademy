from badges import Badge, BadgeContextType

# All badges that may be awarded once-per-Playlist inherit from PlaylistBadge
class PlaylistBadge(Badge):

    def __init__(self):
        Badge.__init__(self)
        self.badge_context_type = BadgeContextType.PLAYLIST

    def is_already_owned_by(self, user_data, *args, **kwargs):
        user_playlist = kwargs.get("user_playlist", None)
        if user_playlist is None:
            return False

        return self.name_with_target_context(user_playlist.title) in user_data.badges

    def award_to(self, user_data, *args, **kwargs):
        user_playlist = kwargs.get("user_playlist", None)
        if user_playlist is None:
            return False

        self.complete_award_to(user_data, user_playlist.playlist, user_playlist.playlist.title)

