from badges import BadgeCategory
from playlist_badges import PlaylistBadge
from templatefilters import seconds_to_time_string

# All badges awarded for watching a specific amount of playlist time inherit from PlaylistTimeBadge
class PlaylistTimeBadge(PlaylistBadge):

    def is_satisfied_by(self, *args, **kwargs):
        user_playlist = kwargs.get("user_playlist", None)

        if user_playlist is None:
            return False

        return user_playlist.seconds_watched >= self.seconds_required

    def extended_description(self):
        return "Watch %s of video in a single playlist" % seconds_to_time_string(self.seconds_required)

class NicePlaylistTimeBadge(PlaylistTimeBadge):
    def __init__(self):
        PlaylistTimeBadge.__init__(self)
        self.seconds_required = 60 * 15
        self.description = "Nice Listener"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 0

class GreatPlaylistTimeBadge(PlaylistTimeBadge):
    def __init__(self):
        PlaylistTimeBadge.__init__(self)
        self.seconds_required = 60 * 30
        self.description = "Great Listener"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 0

class AwesomePlaylistTimeBadge(PlaylistTimeBadge):
    def __init__(self):
        PlaylistTimeBadge.__init__(self)
        self.seconds_required = 60 * 60
        self.description = "Awesome Listener"
        self.badge_category = BadgeCategory.SILVER
        self.points = 0

class RidiculousPlaylistTimeBadge(PlaylistTimeBadge):
    def __init__(self):
        PlaylistTimeBadge.__init__(self)
        self.seconds_required = 60 * 60 * 4
        self.description = "Ridiculous Listener"
        self.badge_category = BadgeCategory.GOLD
        self.points = 0

class LudicrousPlaylistTimeBadge(PlaylistTimeBadge):
    def __init__(self):
        PlaylistTimeBadge.__init__(self)
        self.seconds_required = 60 * 60 * 10
        self.description = "Ludicrous Listener"
        self.badge_category = BadgeCategory.PLATINUM
        self.points = 0
