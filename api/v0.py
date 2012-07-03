
# This v0 API is officially deprecated as of June 2011. v1 is the new place to be.
# We're keeping it around for at least 6 months so old clients can transition to the next version.

import logging
import zlib
import os
import datetime
import urllib

import simplejson as json
from google.appengine.api import users

from app import App
import app
import util
import request_handler
import layer_cache

import coaches
from models import UserExercise, Exercise, UserData, ProblemLog, UserVideo, Playlist, VideoPlaylist, Video, ExerciseVideo, Setting    
from discussion import qa

from api import route
from api.decorators import jsonp, jsonify

from flask import request

@route("/api/playlists", methods=["GET"])
@jsonp
@jsonify
def playlists():
    return get_playlists_json()

@route("/api/playlistvideos", methods=["GET"])
@jsonp
@jsonify
def playlist_videos():
    playlist_title = request.values["playlist"]
    return get_playlist_videos_json(playlist_title)

@route("/api/videolibrary", methods=["GET"])
@jsonp
@jsonify
def video_library():
    return zlib.decompress(get_video_library_json_compressed())

@route("/api/videolibrarylastupdated", methods=["GET"])
@jsonp
@jsonify
def video_library_last_updated():
    return Setting.cached_library_content_date()

@layer_cache.cache_with_key_fxn(
        lambda: "json_playlists_%s" % Setting.cached_library_content_date(), 
        layer=layer_cache.Layers.Memcache)
def get_playlists_json():
    return json.dumps(get_playlist_api_dicts(), indent=4)

@layer_cache.cache_with_key_fxn(
        lambda playlist_title: "json_playlistvideos_%s_%s" % (playlist_title, Setting.cached_library_content_date()), 
        layer=layer_cache.Layers.Memcache)
def get_playlist_videos_json(playlist_title):
    query = Playlist.all()
    query.filter('title =', playlist_title)
    playlist = query.get()

    video_query = Video.all()
    video_query.filter('playlists = ', playlist_title)
    video_key_dict = Video.get_dict(video_query, lambda video: video.key())

    video_playlist_query = VideoPlaylist.all()
    video_playlist_query.filter('playlist =', playlist)
    video_playlist_query.filter('live_association =', True)
    video_playlist_key_dict = VideoPlaylist.get_key_dict(video_playlist_query)

    return json.dumps(get_playlist_video_api_dicts(playlist, video_key_dict, video_playlist_key_dict), indent=4)

@layer_cache.cache_with_key_fxn(
        lambda: "json_video_library_%s" % Setting.cached_library_content_date(), 
        layer=layer_cache.Layers.Memcache)
def get_video_library_json_compressed():
    playlist_api_dicts = []
    playlists = Playlist.get_for_all_topics()
    video_key_dict = Video.get_dict(Video.all(), lambda video: video.key())

    video_playlist_query = VideoPlaylist.all()
    video_playlist_query.filter('live_association =', True)
    video_playlist_key_dict = VideoPlaylist.get_key_dict(video_playlist_query)

    for playlist in playlists:
        playlist_api_dict = ApiDict.playlist(playlist)
        playlist_api_dict["videos"] = get_playlist_video_api_dicts(playlist, video_key_dict, video_playlist_key_dict)
        playlist_api_dicts.append(playlist_api_dict)

    # We compress this huge json payload so it'll fit in memcache
    return zlib.compress(json.dumps(playlist_api_dicts, indent=4))

def get_playlist_api_dicts():
    playlist_api_dicts = []
    for playlist in Playlist.get_for_all_topics():
        playlist_api_dicts.append(ApiDict.playlist(playlist))
    return playlist_api_dicts

def get_playlist_video_api_dicts(playlist, video_key_dict, video_playlist_key_dict):

    video_api_dicts = []
    video_playlists = sorted(video_playlist_key_dict[playlist.key()].values(), key=lambda video_playlist: video_playlist.video_position)
    c_videos = len(video_playlists)

    for ix in range(0, c_videos):
        video_playlist = video_playlists[ix]

        video = video_key_dict[VideoPlaylist.video.get_value_for_datastore(video_playlist)]
        video_prev = None if ix <= 0 else video_key_dict[VideoPlaylist.video.get_value_for_datastore(video_playlists[ix - 1])]# video_playlists[ix - 1].video
        video_next = None if ix + 1 >= (c_videos) else video_key_dict[VideoPlaylist.video.get_value_for_datastore(video_playlists[ix + 1])]# video_playlists[ix + 1].video

        video_api_dicts.append(ApiDict.video(video, video_playlist.video_position, playlist.title, video_prev, video_next))

    return video_api_dicts

class ApiDict():
    @staticmethod
    def video(video, video_position, playlist_title, video_prev, video_next):

        prev_video_youtube_id = ""
        next_video_youtube_id = ""
        related_video_youtube_ids = []

        if video_prev:
            prev_video_youtube_id = video_prev.youtube_id
            related_video_youtube_ids.append(prev_video_youtube_id)

        if video_next:
            next_video_youtube_id = video_next.youtube_id
            related_video_youtube_ids.append(next_video_youtube_id)

        return {
            'youtube_id':  video.youtube_id,
            'youtube_url': video.url,
            'ka_url': "http://www.khanacademy.org/video/%s?playlist=%s" % (video.readable_id, urllib.quote_plus(playlist_title)),
            'title': video.title, 
            'description': video.description,
            'keywords': video.keywords,                         
            'readable_id': video.readable_id,
            'video_position': video_position,
            'views': video.views,
            'duration': video.duration,
            'date_added': video.date_added.strftime('%Y-%m-%d %H:%M:%S'),
            'playlist_titles': video.playlists,
            'prev_video': prev_video_youtube_id,
            'next_video': next_video_youtube_id,
            'related_videos': related_video_youtube_ids,
        }

    @staticmethod
    def playlist(playlist):
        return {
            'youtube_id':  playlist.youtube_id,
            'youtube_url': playlist.url,
            'title': playlist.title, 
            'description': playlist.description,
            'videos': [],
            'api_url': "http://www.khanacademy.org/api/playlistvideos?playlist=%s" % (urllib.quote_plus(playlist.title)),
        }


