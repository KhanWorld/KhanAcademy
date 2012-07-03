import datetime
import random

from jinja2.utils import escape

import library
import request_handler
import models
import layer_cache
import templatetags
from topics_list import DVD_list
from api.auth.xsrf import ensure_xsrf_cookie
from gae_bingo.gae_bingo import bingo
from experiments import HomepageRestructuringExperiment

ITEMS_PER_SET = 4

def thumbnail_link_dict(video = None, exercise = None, thumb_url = None):

    link_dict = None

    if video:
        link_dict = {
            "href": "/video/%s" % video.readable_id,
            "thumb_urls": models.Video.youtube_thumbnail_urls(video.youtube_id),
            "title": video.title,
            "desc_html": templatetags.video_name_and_progress(video),
            "teaser_html": video.description,
            "youtube_id": video.youtube_id,
            "marquee": ("marquee" in video.keywords),
            "selected": False,
            "key": video.key(),
            "type": "video-thumb",
        }

    if exercise:
        link_dict = {
            "href": exercise.relative_url,
            "thumb_urls": {"hq": thumb_url, "sd": thumb_url},
            "desc_html": escape(exercise.display_name),
            "teaser_html": "Exercise your <em>%s</em> skills" % escape(exercise.display_name),
            "youtube_id": "",
            "marquee": False,
            "selected": False,
            "key": exercise.key(),
            "type": "exercise-thumb",
        }

    if link_dict:

        if len(link_dict["teaser_html"]) > 60:
            link_dict["teaser_html"] = link_dict["teaser_html"][:60] + "&hellip;"

        return link_dict

    return None

@layer_cache.cache_with_key_fxn(
        lambda *args, **kwargs: "new_and_noteworthy_link_sets_%s" % models.Setting.cached_library_content_date()
        )
def new_and_noteworthy_link_sets():

    playlist = models.Playlist.all().filter("title =", "New and Noteworthy").get()
    if not playlist:
        # If we can't find the playlist, just show the default TED talk.
        return []

    videos = models.VideoPlaylist.get_cached_videos_for_playlist(playlist)
    if len(videos) < 2:
        # If there's only one video, don't bother.
        return []

    exercises = []

    # We use playlist tags to identify new and noteworthy exercises
    # just so Sal has a really simple, fast, all-YouTube interface
    for tag in playlist.tags:
        exercise = models.Exercise.get_by_name(tag)
        if exercise:
            exercises.append(exercise)

    if len(exercises) == 0:
        # Temporary hard-coding of a couple exercises until Sal picks a few
        playlist.tags = ['derivative_intuition', 'inequalities_on_a_number_line', 'multiplication_4', 'solid_geometry']
        for tag in playlist.tags:
            exercise = models.Exercise.get_by_name(tag)
            if exercise:
                exercises.append(exercise)

    sets = []
    current_set = []
    next_exercise = 0

    # Randomly place exercises one per set in 2, 3, or 4
    current_set_exercise_position = random.randint(1, ITEMS_PER_SET - 1)

    exercise_icon_files = ["ex1.png", "ex2.png", "ex3.png", "ex4.png"]
    random.shuffle(exercise_icon_files)

    for video in videos:

        if len(current_set) >= ITEMS_PER_SET:
            sets.append(current_set)
            current_set = []
            current_set_exercise_position = random.randint(0, ITEMS_PER_SET - 1)

        if next_exercise < len(exercises) and len(current_set) == current_set_exercise_position:
            exercise = exercises[next_exercise]

            thumb_url = "/images/splashthumbnails/exercises/%s" % (exercise_icon_files[next_exercise % (len(exercise_icon_files))])
            current_set.append(thumbnail_link_dict(exercise = exercise, thumb_url = thumb_url))

            next_exercise += 1

        if len(current_set) >= ITEMS_PER_SET:
            sets.append(current_set)
            current_set = []
            current_set_exercise_position = random.randint(0, ITEMS_PER_SET - 1)

        current_set.append(thumbnail_link_dict(video = video))

    if len(current_set) > 0:
        sets.append(current_set)

    return sets

class ViewHomePage(request_handler.RequestHandler):

    def head(self):
        # Respond to HEAD requests for our homepage so twitter's tweet
        # counter will update:
        # https://dev.twitter.com/docs/tweet-button/faq#count-api-increment
        pass

    # See https://sites.google.com/a/khanacademy.org/forge/for-team-members/how-to-use-new-and-noteworthy-content
    # for info on how to update the New & Noteworthy videos
    @ensure_xsrf_cookie
    def get(self):

        thumbnail_link_sets = new_and_noteworthy_link_sets()

        # If all else fails, just show the TED talk on the homepage
        marquee_video = {
            "youtube_id": "gM95HHI4gLk",
            "href": "/video?v=%s" % "gM95HHI4gLk",
            "thumb_urls": models.Video.youtube_thumbnail_urls("gM95HHI4gLk"),
            "title": "Salman Khan talk at TED 2011",
            "key": "",
        }

        if len(thumbnail_link_sets) > 1:

            day = datetime.datetime.now().day

            # Switch up the first 4 New & Noteworthy videos on a daily basis
            current_link_set_offset = day % len(thumbnail_link_sets)

            # Switch up the marquee video on a daily basis
            marquee_videos = []
            for thumbnail_link_set in thumbnail_link_sets:
                marquee_videos += filter(lambda item: item["marquee"],
                                         thumbnail_link_set)

            if marquee_videos:
                marquee_video = marquee_videos[day % len(marquee_videos)]
                marquee_video["selected"] = True

            if len(thumbnail_link_sets[current_link_set_offset]) < ITEMS_PER_SET:
                # If the current offset lands on a set of videos that isn't a full set, just start
                # again at the first set, which is most likely full.
                current_link_set_offset = 0

            thumbnail_link_sets = thumbnail_link_sets[current_link_set_offset:] + thumbnail_link_sets[:current_link_set_offset]

        # Only running restructure A/B test for non-mobile clients
        render_type = 'original'
        if not self.is_mobile_capable():
            render_type = HomepageRestructuringExperiment.get_render_type()
            bingo('homepage_restructure_visits')

        if render_type == 'original':
            library_content = library.library_content_html()
        else:
            library_content = library.playlist_content_html()

        template_values = {
                            'marquee_video': marquee_video,
                            'thumbnail_link_sets': thumbnail_link_sets,
                            'library_content': library_content,
                            'DVD_list': DVD_list,
                            'is_mobile_allowed': True,
                            'approx_vid_count': models.Video.approx_count(),
                            'exercise_count': models.Exercise.get_count(),
                            'link_heat': self.request_bool("heat", default=False),
                        }

        self.render_jinja2_template('homepage.html', template_values)
