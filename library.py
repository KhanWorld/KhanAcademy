import datetime
import logging

import shared_jinja

from app import App
import layer_cache
from models import Video, Playlist, VideoPlaylist, Setting
from topics_list import topics_list
import request_handler
import util
import urllib2
import re
import math
import time

@layer_cache.cache(layer=layer_cache.Layers.Memcache | layer_cache.Layers.Datastore, expiration=86400)
def getSmartHistoryContent():
    request = urllib2.Request("http://smarthistory.org/khan-home.html")
    try:
        response = urllib2.urlopen(request)
        smart_history = response.read()
        smart_history = re.search(re.compile("<body>(.*)</body>", re.S), smart_history).group(1).decode("utf-8")
        smart_history.replace("script", "")
    except Exception, e:
        logging.exception("Failed fetching smarthistory playlist")
        smart_history = None
        pass
    return smart_history

@layer_cache.cache_with_key_fxn(
        lambda *args, **kwargs: "library_content_html_%s" % Setting.cached_library_content_date()
        )
def library_content_html():
    # No cache found -- regenerate HTML
    smart_history = getSmartHistoryContent()

    all_playlists = []

    dict_videos = {}
    dict_videos_counted = {}
    dict_playlists = {}
    dict_playlists_by_title = {}
    dict_video_playlists = {}

    async_queries = [
        Video.all(),
        Playlist.all(),
        VideoPlaylist.all().filter('live_association = ', True).order('video_position'),
    ]

    results = util.async_queries(async_queries)

    for video in results[0].get_result():
        dict_videos[video.key()] = video

    for playlist in results[1].get_result():
        dict_playlists[playlist.key()] = playlist
        if playlist.title in topics_list:
            dict_playlists_by_title[playlist.title] = playlist

    for video_playlist in results[2].get_result():
        playlist_key = VideoPlaylist.playlist.get_value_for_datastore(video_playlist)
        video_key = VideoPlaylist.video.get_value_for_datastore(video_playlist)

        if dict_videos.has_key(video_key) and dict_playlists.has_key(playlist_key):
            video = dict_videos[video_key]
            playlist = dict_playlists[playlist_key]
            fast_video_playlist_dict = {"video":video, "playlist":playlist}

            if dict_video_playlists.has_key(playlist_key):
                dict_video_playlists[playlist_key].append(fast_video_playlist_dict)
            else:
                dict_video_playlists[playlist_key] = [fast_video_playlist_dict]

            if dict_playlists_by_title.has_key(playlist.title):
                # Only count videos in topics_list
                dict_videos_counted[video.youtube_id] = True

    # Update count of all distinct videos associated w/ a live playlist
    Setting.count_videos(len(dict_videos_counted.keys()))

    for topic in topics_list:
        if topic in dict_playlists_by_title:
            playlist = dict_playlists_by_title[topic]
            playlist_key = playlist.key()
            playlist_videos = dict_video_playlists.get(playlist_key) or []

            if not playlist_videos:
                logging.error('Playlist %s has no videos!', playlist.title)

            playlist_data = {
                     'title': topic,
                     'topic': topic,
                     'playlist': playlist,
                     'videos': playlist_videos,
                     'next': None
                     }

            all_playlists.append(playlist_data)

    playlist_data_prev = None
    for playlist_data in all_playlists:
        if playlist_data_prev:
            playlist_data_prev['next'] = playlist_data
        playlist_data_prev = playlist_data

    # Separating out the columns because the formatting is a little different on each column
    template_values = {
        'App' : App,
        'all_playlists': all_playlists,
        'smart_history': smart_history,
        }

    html = shared_jinja.get().render_template("library_content_template.html", **template_values)

    # Set shared date of last generated content
    Setting.cached_library_content_date(str(datetime.datetime.now()))

    return html

@layer_cache.cache_with_key_fxn(
        lambda *args, **kwargs: "playlist_content_html%s" % Setting.cached_playlist_content_date()
        )
def playlist_content_html():
    """" Returns the HTML for the structure of the playlists as they will be
    populated ont he homepage. Does not actually contain the list of video
    names as those are filled in later asynchronously via the cache.
    
    """
    
    # No cache found -- regenerate HTML
    smart_history = getSmartHistoryContent()

    dict_playlists_by_title = {}
    all_playlists = []

    for playlist in Playlist.all():
        if playlist.title in topics_list:
            dict_playlists_by_title[playlist.title] = playlist

    for topic in topics_list:
        if topic in dict_playlists_by_title:
            playlist = dict_playlists_by_title[topic]
            video_count = playlist.get_video_count() 
            # 3 columns, 18px per row. This must be updated in conjunction
            # with code in homepage.js
            height = math.ceil(video_count / 3) * 18

            playlist_data = {
                             'title': topic,
                             'topic': topic,
                             'playlist': playlist,
                             'list_height': height,
                             'next': None,
                             }

            all_playlists.append(playlist_data)

    playlist_data_prev = None
    for playlist_data in all_playlists:
        if playlist_data_prev:
            playlist_data_prev['next'] = playlist_data
        playlist_data_prev = playlist_data

    timestamp = time.time()
    template_values = {
        'App' : App,
        'all_playlists': all_playlists,
        'smart_history': smart_history,
        
        # convert timestamp to a nice integer for the JS
        'timestamp': int(round(timestamp * 1000)),
        }

    html = shared_jinja.get().render_template("library_playlist_template.html",
                                              **template_values)
    Setting.cached_playlist_content_date(
            str(datetime.datetime.fromtimestamp(timestamp)))
    return html

class GenerateLibraryContent(request_handler.RequestHandler):

    def post(self):
        # We support posts so we can fire task queues at this handler
        self.get(from_task_queue = True)

    def get(self, from_task_queue = False):
        library_content_html(bust_cache=True)

        if not from_task_queue:
            self.redirect("/")

