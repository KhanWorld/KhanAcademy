#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import urllib
import urlparse
import logging
import re

from google.appengine.runtime.apiproxy_errors import CapabilityDisabledError
from google.appengine.api import users
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

import webapp2

import devpanel
import bulk_update.handler
import request_cache
from gae_mini_profiler import profiler
from gae_bingo.middleware import GAEBingoWSGIMiddleware
import autocomplete
import coaches
import knowledgemap
import consts
import youtube_sync
import warmup
import library
import homepage
import nl
import nl_report

import search

import request_handler
from app import App
import util
import user_util
import exercise_statistics
import activity_summary
import exercises
import dashboard
import exercisestats.report
import exercisestats.report_json
import github
import paypal
import smarthistory
import goals.handlers

import models
from models import UserData, Video, Playlist, VideoPlaylist, ExerciseVideo, UserVideo, VideoLog
from discussion import comments, notification, qa, voting
from about import blog, util_about
from phantom_users import util_notify
from badges import util_badges, custom_badges
from mailing_lists import util_mailing_lists
from profiles import util_profile
from custom_exceptions import MissingVideoException
from templatetags import user_points
from oauth_provider import apps as oauth_apps
from phantom_users.phantom_util import create_phantom, get_phantom_user_id_from_cookies
from phantom_users.cloner import Clone
from counters import user_counter
from notifications import UserNotifier
from nicknames import get_nickname_for
from image_cache import ImageCache
from api.auth.xsrf import ensure_xsrf_cookie
import redirects
import robots
from gae_bingo.gae_bingo import bingo

class VideoDataTest(request_handler.RequestHandler):

    @user_util.developer_only
    def get(self):
        self.response.out.write('<html>')
        videos = Video.all()
        for video in videos:
            self.response.out.write('<P>Title: ' + video.title)


class DeleteVideoPlaylists(request_handler.RequestHandler):
# Deletes at most 200 Video-Playlist associations that are no longer live.  Should be run every-now-and-then to make sure the table doesn't get too big
    @user_util.developer_only
    def get(self):
        query = VideoPlaylist.all()
        all_video_playlists = query.fetch(200)
        video_playlists_to_delete = []
        for video_playlist in all_video_playlists:
            if video_playlist.live_association != True:
                video_playlists_to_delete.append(video_playlist)
        db.delete(video_playlists_to_delete)


class KillLiveAssociations(request_handler.RequestHandler):
    @user_util.developer_only
    def get(self):
        query = VideoPlaylist.all()
        all_video_playlists = query.fetch(100000)
        for video_playlist in all_video_playlists:
            video_playlist.live_association = False
        db.put(all_video_playlists)

def get_mangled_playlist_name(playlist_name):
    for char in " :()":
        playlist_name = playlist_name.replace(char, "")
    return playlist_name

class ViewVideo(request_handler.RequestHandler):

    @ensure_xsrf_cookie
    def get(self, readable_id=""):

        # This method displays a video in the context of a particular playlist.
        # To do that we first need to find the appropriate playlist.  If we aren't
        # given the playlist title in a query param, we need to find a playlist that
        # the video is a part of.  That requires finding the video, given it readable_id
        # or, to support old URLs, it's youtube_id.
        video = None
        playlist = None
        video_id = self.request.get('v')
        playlist_title = self.request_string('playlist', default="") or self.request_string('p', default="")

        readable_id = urllib.unquote(readable_id)
        readable_id = re.sub('-+$', '', readable_id)  # remove any trailing dashes (see issue 1140)

        # If either the readable_id or playlist title is missing,
        # redirect to the canonical URL that contains them
        redirect_to_canonical_url = False
        if video_id: # Support for old links
            query = Video.all()
            query.filter('youtube_id =', video_id)
            video = query.get()

            if not video:
                raise MissingVideoException("Missing video w/ youtube id '%s'" % video_id)

            readable_id = video.readable_id
            playlist = video.first_playlist()

            if not playlist:
                raise MissingVideoException("Missing video w/ youtube id '%s'" % video_id)

            redirect_to_canonical_url = True

        if playlist_title is not None and len(playlist_title) > 0:
            query = Playlist.all().filter('title =', playlist_title)
            key_id = 0
            for p in query:
                if p.key().id() > key_id and not p.youtube_id.endswith('_player'):
                    playlist = p
                    key_id = p.key().id()

        # If a playlist_title wasn't specified or the specified playlist wasn't found
        # use the first playlist for the requested video.
        if playlist is None:
            # Get video by readable_id just to get the first playlist for the video
            video = Video.get_for_readable_id(readable_id)
            if video is None:
                raise MissingVideoException("Missing video '%s'" % readable_id)

            playlist = video.first_playlist()
            if not playlist:
                raise MissingVideoException("Missing video '%s'" % readable_id)

            redirect_to_canonical_url = True

        exid = self.request_string('exid', default=None)

        if redirect_to_canonical_url:
            qs = {'playlist': playlist.title}
            if exid:
                qs['exid'] = exid

            urlpath = "/video/%s" % urllib.quote(readable_id)
            url = urlparse.urlunparse(('', '', urlpath, '', urllib.urlencode(qs), ''))
            self.redirect(url, True)
            return

        # If we got here, we have a readable_id and a playlist_title, so we can display
        # the playlist and the video in it that has the readable_id.  Note that we don't
        # query the Video entities for one with the requested readable_id because in some
        # cases there are multiple Video objects in the datastore with the same readable_id
        # (e.g. there are 2 "Order of Operations" videos).

        videos = VideoPlaylist.get_cached_videos_for_playlist(playlist)
        previous_video = None
        next_video = None
        for v in videos:
            if v.readable_id == readable_id:
                v.selected = 'selected'
                video = v
            elif video is None:
                previous_video = v
            elif next_video is None:
                next_video = v

        if video is None:
            raise MissingVideoException("Missing video '%s'" % readable_id)

        if App.offline_mode:
            video_path = "/videos/" + get_mangled_playlist_name(playlist_title) + "/" + video.readable_id + ".flv"
        else:
            video_path = video.download_video_url()

        if video.description == video.title:
            video.description = None

        related_exercises = video.related_exercises()
        button_top_exercise = None
        if related_exercises:
            def ex_to_dict(exercise):
                return {
                    'name': exercise.display_name,
                    'url': exercise.relative_url,
                }
            button_top_exercise = ex_to_dict(related_exercises[0])

        user_video = UserVideo.get_for_video_and_user_data(video, UserData.current(), insert_if_missing=True)

        awarded_points = 0
        if user_video:
            awarded_points = user_video.points

        template_values = {
                            'playlist': playlist,
                            'video': video,
                            'videos': videos,
                            'video_path': video_path,
                            'video_points_base': consts.VIDEO_POINTS_BASE,
                            'button_top_exercise': button_top_exercise,
                            'related_exercises': [], # disabled for now
                            'previous_video': previous_video,
                            'next_video': next_video,
                            'selected_nav_link': 'watch',
                            'awarded_points': awarded_points,
                            'issue_labels': ('Component-Videos,Video-%s' % readable_id),
                            'author_profile': 'https://plus.google.com/103970106103092409324'
                        }
        template_values = qa.add_template_values(template_values, self.request)

        bingo(['struggling_videos_landing',
               'homepage_restructure_videos_landing'])
        self.render_jinja2_template('viewvideo.html', template_values)

class ReportIssue(request_handler.RequestHandler):

    def get(self):
        issue_type = self.request.get('type')
        self.write_response(issue_type, {'issue_labels': self.request.get('issue_labels'),})

    def write_response(self, issue_type, extra_template_values):
        user_agent = self.request.headers.get('User-Agent')
        if user_agent is None:
            user_agent = ''
        user_agent = user_agent.replace(',',';') # Commas delimit labels, so we don't want them
        template_values = {
            'referer': self.request.headers.get('Referer'),
            'user_agent': user_agent,
            }
        template_values.update(extra_template_values)
        page = 'reportissue_template.html'
        if issue_type == 'Defect':
            page = 'reportproblem.html'
        elif issue_type == 'Enhancement':
            page = 'makesuggestion.html'
        elif issue_type == 'New-Video':
            page = 'requestvideo.html'
        elif issue_type == 'Comment':
            page = 'makecomment.html'
        elif issue_type == 'Question':
            page = 'askquestion.html'

        self.render_jinja2_template(page, template_values)

class Crash(request_handler.RequestHandler):
    def get(self):
        if self.request_bool("capability_disabled", default=False):
            raise CapabilityDisabledError("Simulate scheduled GAE downtime")
        else:
            # Even Watson isn't perfect
            raise Exception("What is Toronto?")

class ReadOnlyDowntime(request_handler.RequestHandler):
    def get(self):
        raise CapabilityDisabledError("App Engine maintenance period")

    def post(self):
        return self.get()

class SendToLog(request_handler.RequestHandler):
    def post(self):
        message = self.request_string("message", default="")
        if message:
            logging.critical("Manually sent to log: %s" % message)

class MobileFullSite(request_handler.RequestHandler):
    def get(self):
        self.set_mobile_full_site_cookie(True)
        self.redirect("/")

class MobileSite(request_handler.RequestHandler):
    def get(self):
        self.set_mobile_full_site_cookie(False)
        self.redirect("/")

class ViewFAQ(request_handler.RequestHandler):
    def get(self):
        self.redirect("/about/faq", True)
        return

class ViewGetInvolved(request_handler.RequestHandler):
    def get(self):
        self.redirect("/contribute", True)

class ViewContribute(request_handler.RequestHandler):
    def get(self):
        self.render_jinja2_template('contribute.html', {"selected_nav_link": "contribute"})

class ViewCredits(request_handler.RequestHandler):
    def get(self):
        self.render_jinja2_template('viewcredits.html', {"selected_nav_link": "contribute"})

class Donate(request_handler.RequestHandler):
    def get(self):
        self.redirect("/contribute", True)

class ViewTOS(request_handler.RequestHandler):
    def get(self):
        self.render_jinja2_template('tos.html', {"selected_nav_link": "tos"})

class ViewAPITOS(request_handler.RequestHandler):
    def get(self):
        self.render_jinja2_template('api-tos.html', {"selected_nav_link": "api-tos"})

class ViewPrivacyPolicy(request_handler.RequestHandler):
    def get(self):
        self.render_jinja2_template('privacy-policy.html', {"selected_nav_link": "privacy-policy"})

class ViewDMCA(request_handler.RequestHandler):
    def get(self):
        self.render_jinja2_template('dmca.html', {"selected_nav_link": "dmca"})

class ViewSAT(request_handler.RequestHandler):

    def get(self):
        playlist_title = "SAT Preparation"
        query = Playlist.all()
        query.filter('title =', playlist_title)
        playlist = query.get()
        query = VideoPlaylist.all()
        query.filter('playlist =', playlist)
        query.filter('live_association = ', True) #need to change this to true once I'm done with all of my hacks
        query.order('video_position')
        playlist_videos = query.fetch(500)

        template_values = {
                'videos': playlist_videos,
        }

        self.render_jinja2_template('sat.html', template_values)

class ViewGMAT(request_handler.RequestHandler):

    def get(self):
        problem_solving = VideoPlaylist.get_query_for_playlist_title("GMAT: Problem Solving")
        data_sufficiency = VideoPlaylist.get_query_for_playlist_title("GMAT Data Sufficiency")
        template_values = {
                            'data_sufficiency': data_sufficiency,
                            'problem_solving': problem_solving,
        }

        self.render_jinja2_template('gmat.html', template_values)


class RetargetFeedback(bulk_update.handler.UpdateKind):
    def get_keys_query(self, kind):
        """Returns a keys-only query to get the keys of the entities to update"""
        return db.GqlQuery('select __key__ from Feedback')

    def use_transaction(self):
        return False

    def update(self, feedback):
        orig_video = feedback.video()

        if orig_video == None or type(orig_video).__name__ != "Video":
            return False
        readable_id = orig_video.readable_id
        query = Video.all()
        query.filter('readable_id =', readable_id)
        # The database currently contains multiple Video objects for a particular
        # video.  Some are old.  Some are due to a YouTube sync where the youtube urls
        # changed and our code was producing youtube_ids that ended with '_player'.
        # This hack gets the most recent valid Video object.
        key_id = 0
        for v in query:
            if v.key().id() > key_id and not v.youtube_id.endswith('_player'):
                video = v
                key_id = v.key().id()
        # End of hack
        if video is not None and video.key() != orig_video.key():
            logging.info("Retargeting Feedback %s from Video %s to Video %s", feedback.key().id(), orig_video.key().id(), video.key().id())
            feedback.targets[0] = video.key()
            return True
        else:
            return False

class ChangeEmail(bulk_update.handler.UpdateKind):

    def get_email_params(self):
        old_email = self.request.get('old')
        new_email = self.request.get('new')
        prop = self.request.get('prop')
        if old_email is None or len(old_email) == 0:
            raise Exception("parameter 'old' is required")
        if new_email is None or len(new_email) == 0:
            new_email = old_email
        if prop is None or len(prop) == 0:
            prop = "user"
        return (old_email, new_email, prop)

    def get(self):
        (old_email, new_email, prop) = self.get_email_params()
        if new_email == old_email:
            return bulk_update.handler.UpdateKind.get(self)
        self.response.out.write("To prevent a CSRF attack from changing email addresses, you initiate an email address change from the browser. ")
        self.response.out.write("Instead, run the following from remote_api_shell.py.<pre>\n")
        self.response.out.write("import bulk_update.handler\n")
        self.response.out.write("bulk_update.handler.start_task('%s',{'kind':'%s', 'old':'%s', 'new':'%s'})\n"
                                % (self.request.path, self.request.get('kind'), old_email, new_email))
        self.response.out.write("</pre>and then check the logs in the admin console")


    def get_keys_query(self, kind):
        """Returns a keys-only query to get the keys of the entities to update"""

        (old_email, new_email, prop) = self.get_email_params()
        # When a user's personal Google account is replaced by their transitioned Google Apps account with the same email,
        # the Google user ID changes and the new User object's are not considered equal to the old User object's with the same
        # email, so querying the datastore for entities referring to users with the same email return nothing. However an inequality
        # query will return the relevant entities.
        gt_user = users.User(old_email[:-1] + chr(ord(old_email[-1])-1) + chr(127))
        lt_user = users.User(old_email + chr(0))
        return db.GqlQuery(('select __key__ from %s where %s > :1 and %s < :2' % (kind, prop, prop)), gt_user, lt_user)

    def use_transaction(self):
        return False

    def update(self, entity):
        (old_email, new_email, prop) = self.get_email_params()
        if getattr(entity, prop).email() != old_email:
            # This should never occur, but just in case, don't change or reput the entity.
            return False
        setattr(entity, prop, users.User(new_email))
        return True

class Login(request_handler.RequestHandler):
    def get(self):
        return self.post()

    def post(self):
        cont = self.request_string('continue', default = "/")
        direct = self.request_bool('direct', default = False)

        openid_identifier = self.request.get('openid_identifier')
        if openid_identifier is not None and len(openid_identifier) > 0:
            if App.accepts_openid:
                self.redirect(users.create_login_url(cont, federated_identity = openid_identifier))
                return
            self.redirect(users.create_login_url(cont))
            return

        if App.facebook_app_secret is None:
            self.redirect(users.create_login_url(cont))
            return
        template_values = {
                           'continue': cont,
                           'direct': direct
                           }
        self.render_jinja2_template('login.html', template_values)

class MobileOAuthLogin(request_handler.RequestHandler):
    def get(self):
        self.render_jinja2_template('login_mobile_oauth.html', {
            "oauth_map_id": self.request_string("oauth_map_id", default=""),
            "anointed": self.request_bool("an", default=False),
            "view": self.request_string("view", default="")
        })

class PostLogin(request_handler.RequestHandler):
    def get(self):
        cont = self.request_string('continue', default = "/")

        # Immediately after login we make sure this user has a UserData entity
        user_data = UserData.current()
        if user_data:

            # Update email address if it has changed
            current_google_user = users.get_current_user()
            if current_google_user and current_google_user.email() != user_data.email:
                user_data.user_email = current_google_user.email()
                user_data.put()

            # Update nickname if it has changed
            current_nickname = get_nickname_for(user_data)
            if user_data.user_nickname != current_nickname:
                user_data.user_nickname = current_nickname
                user_data.put()

            # Set developer and moderator to True if user is admin
            if (not user_data.developer or not user_data.moderator) and users.is_current_user_admin():
                user_data.developer = True
                user_data.moderator = True
                user_data.put()

            # If user is brand new and has 0 points, migrate data
            phantom_id = get_phantom_user_id_from_cookies()
            if phantom_id:
                phantom_data = UserData.get_from_db_key_email(phantom_id)

                # First make sure user has 0 points and phantom user has some activity
                if user_data.points == 0 and phantom_data and phantom_data.points > 0:

                    # Make sure user has no students
                    if not user_data.has_students():

                        # Clear all "login" notifications
                        UserNotifier.clear_all(phantom_data)

                        # Update phantom user_data to real user_data
                        phantom_data.user_id = user_data.user_id
                        phantom_data.current_user = user_data.current_user
                        phantom_data.user_email = user_data.user_email
                        phantom_data.user_nickname = user_data.user_nickname

                        if phantom_data.put():
                            # Phantom user was just transitioned to real user
                            user_counter.add(1)
                            user_data.delete()

                        cont = "/newaccount?continue=%s" % cont
        else:

            # If nobody is logged in, clear any expired Facebook cookie that may be hanging around.
            self.delete_cookie("fbsr_" + App.facebook_app_id)
            self.delete_cookie("fbs_" + App.facebook_app_id)

            logging.critical("Missing UserData during PostLogin, with id: %s, cookies: (%s), google user: %s" % (
                    util.get_current_user_id(), os.environ.get('HTTP_COOKIE', ''), users.get_current_user()
                )
            )

        # Always delete phantom user cookies on login
        self.delete_cookie('ureg_id')

        self.redirect(cont)

class Logout(request_handler.RequestHandler):
    def get(self):
        self.delete_cookie('ureg_id')
        self.redirect(users.create_logout_url(self.request_string("continue", default="/")))

class Search(request_handler.RequestHandler):

    def get(self):
        query = self.request.get('page_search_query')
        template_values = {'page_search_query': query}
        query = query.strip()
        if len(query) < search.SEARCH_PHRASE_MIN_LENGTH:
            if len(query) > 0:
                template_values.update({
                    'query_too_short': search.SEARCH_PHRASE_MIN_LENGTH
                })
            self.render_jinja2_template("searchresults.html", template_values)
            return
        searched_phrases = []

        # Do an async query for all ExerciseVideos, since this may be slow
        exvids_query = ExerciseVideo.all()
        exvids_future = util.async_queries([exvids_query])

        # One full (non-partial) search, then sort by kind
        all_text_keys = Playlist.full_text_search(
                query, limit=50, kind=None,
                stemming=Playlist.INDEX_STEMMING,
                multi_word_literal=Playlist.INDEX_MULTI_WORD,
                searched_phrases_out=searched_phrases)


        # Quick title-only partial search
        playlist_partial_results = filter(
                lambda playlist_dict: query in playlist_dict["title"].lower(),
                autocomplete.playlist_title_dicts())
        video_partial_results = filter(
                lambda video_dict: query in video_dict["title"].lower(),
                autocomplete.video_title_dicts())

        # Combine results & do one big get!
        all_key_list = [str(key_and_title[0]) for key_and_title in all_text_keys]
        #all_key_list.extend([result["key"] for result in playlist_partial_results])
        all_key_list.extend([result["key"] for result in video_partial_results])
        all_key_list = list(set(all_key_list))
        all_entities = db.get(all_key_list)

        # Filter results by type
        playlists = []
        videos = []
        for entity in all_entities:
            if isinstance(entity, Playlist):
                playlists.append(entity)
            elif isinstance(entity, Video):
                videos.append(entity)
            elif entity is not None:
                logging.error("Unhandled kind in search results: " +
                              str(type(entity)))

        playlist_count = len(playlists)

        # Get playlists for videos not in matching playlists
        filtered_videos = []
        filtered_videos_by_key = {}
        for video in videos:
            if [(playlist.title in video.playlists) for playlist in playlists].count(True) == 0:
                video_playlist = video.first_playlist()
                if video_playlist != None:
                    playlists.append(video_playlist)
                    filtered_videos.append(video)
                    filtered_videos_by_key[str(video.key())] = []
            else:
                filtered_videos.append(video)
                filtered_videos_by_key[str(video.key())] = []
        video_count = len(filtered_videos)

        # Get the related exercises
        all_exercise_videos = exvids_future[0].get_result()
        exercise_keys = []
        for exvid in all_exercise_videos:
            video_key = str(ExerciseVideo.video.get_value_for_datastore(exvid))
            if video_key in filtered_videos_by_key:
                exercise_key = ExerciseVideo.exercise.get_value_for_datastore(exvid)
                video_exercise_keys = filtered_videos_by_key[video_key]
                video_exercise_keys.append(exercise_key)
                exercise_keys.append(exercise_key)
        exercises = db.get(exercise_keys)

        # Sort exercises with videos
        video_exercises = {}
        for video_key, exercise_keys in filtered_videos_by_key.iteritems():
            video_exercises[video_key] = map(lambda exkey: [exercise for exercise in exercises if exercise.key() == exkey][0], exercise_keys)

        # Count number of videos in each playlist and sort descending
        for playlist in playlists:
            if len(filtered_videos) > 0:
                playlist.match_count = [(playlist.title in video.playlists) for video in filtered_videos].count(True)
            else:
                playlist.match_count = 0
        playlists = sorted(playlists, key=lambda playlist: -playlist.match_count)

        template_values.update({
                           'playlists': playlists,
                           'videos': filtered_videos,
                           'video_exercises': video_exercises,
                           'search_string': query,
                           'video_count': video_count,
                           'playlist_count': playlist_count,
                           })
        self.render_jinja2_template("searchresults.html", template_values)

class RedirectToJobvite(request_handler.RequestHandler):
    def get(self):
        self.redirect("http://hire.jobvite.com/CompanyJobs/Careers.aspx?k=JobListing&c=qd69Vfw7")

class RedirectToToolkit(request_handler.RequestHandler):
    def get(self):
        self.redirect("https://sites.google.com/a/khanacademy.org/schools/")

class PermanentRedirectToHome(request_handler.RequestHandler):
    def get(self):

        redirect_target = "/"
        relative_path = self.request.path.rpartition('/')[2].lower()

        # Permanently redirect old JSP version of the site to home
        # or, in the case of some special targets, to their appropriate new URL
        dict_redirects = {
            "sat.jsp": "/sat",
            "gmat.jsp": "/gmat",
        }

        if dict_redirects.has_key(relative_path):
            redirect_target = dict_redirects[relative_path]

        self.redirect(redirect_target, True)

class ServeUserVideoCss(request_handler.RequestHandler):
    def get(self):
        user_data = UserData.current()
        if user_data == None:
            return

        user_video_css = models.UserVideoCss.get_for_user_data(user_data)
        self.response.headers['Content-Type'] = 'text/css'

        if user_video_css.version == user_data.uservideocss_version:
            # Don't cache if there's a version mismatch and update isn't finished
            self.response.headers['Cache-Control'] = 'public,max-age=1000000'

        self.response.out.write(user_video_css.video_css)

class RealtimeEntityCount(request_handler.RequestHandler):
    def get(self):
        if not App.is_dev_server:
            raise Exception("Only works on dev servers.")
        default_kinds = 'Exercise'
        kinds = self.request_string("kinds", default_kinds).split(',')
        for kind in kinds:
            count = getattr(models, kind).all().count(10000)
            self.response.out.write("%s: %d<br>" % (kind, count))

applicationSmartHistory = webapp2.WSGIApplication([
    ('/.*', smarthistory.SmartHistoryProxy)
])

application = webapp2.WSGIApplication([
    ('/', homepage.ViewHomePage),
    ('/about', util_about.ViewAbout),
    ('/about/blog', blog.ViewBlog),
    ('/about/blog/.*', blog.ViewBlogPost),
    ('/about/the-team', util_about.ViewAboutTheTeam),
    ('/about/getting-started', util_about.ViewGettingStarted),
    ('/about/tos', ViewTOS ),
    ('/about/api-tos', ViewAPITOS),
    ('/about/privacy-policy', ViewPrivacyPolicy ),
    ('/about/dmca', ViewDMCA ),
    ('/contribute', ViewContribute ),
    ('/contribute/credits', ViewCredits ),
    ('/frequently-asked-questions', util_about.ViewFAQ),
    ('/about/faq', util_about.ViewFAQ),
    ('/downloads', util_about.ViewDownloads),
    ('/about/downloads', util_about.ViewDownloads),
    ('/getinvolved', ViewGetInvolved),
    ('/donate', Donate),
    ('/exercisedashboard', exercises.ViewAllExercises),

    # Issues a command to re-generate the library content.
    ('/library_content', library.GenerateLibraryContent),

    ('/exercise/(.+)', exercises.ViewExercise), # /exercises/addition_1
    ('/exercises', exercises.ViewExercise), # This old /exercises?exid=addition_1 URL pattern is deprecated
    ('/review', exercises.ViewExercise),

    ('/khan-exercises/exercises/.*', exercises.RawExercise),
    ('/viewexercisesonmap', exercises.ViewAllExercises),
    ('/editexercise', exercises.EditExercise),
    ('/updateexercise', exercises.UpdateExercise),
    ('/moveexercisemapnodes', exercises.MoveMapNodes),
    ('/admin94040', exercises.ExerciseAdmin),
    ('/video/(.*)', ViewVideo),
    ('/v/(.*)', ViewVideo),
    ('/video', ViewVideo), # Backwards URL compatibility
    ('/sat', ViewSAT),
    ('/gmat', ViewGMAT),
    ('/reportissue', ReportIssue),
    ('/search', Search),
    ('/savemapcoords', knowledgemap.SaveMapCoords),
    ('/saveexpandedallexercises', knowledgemap.SaveExpandedAllExercises),
    ('/crash', Crash),

    ('/image_cache/(.+)', ImageCache),

    ('/mobilefullsite', MobileFullSite),
    ('/mobilesite', MobileSite),

    ('/admin/reput', bulk_update.handler.UpdateKind),
    ('/admin/retargetfeedback', RetargetFeedback),
    ('/admin/startnewbadgemapreduce', util_badges.StartNewBadgeMapReduce),
    ('/admin/badgestatistics', util_badges.BadgeStatistics),
    ('/admin/startnewexercisestatisticsmapreduce', exercise_statistics.StartNewExerciseStatisticsMapReduce),
    ('/admin/startnewvotemapreduce', voting.StartNewVoteMapReduce),
    ('/admin/feedbackflagupdate', qa.StartNewFlagUpdateMapReduce),
    ('/admin/dailyactivitylog', activity_summary.StartNewDailyActivityLogMapReduce),
    ('/admin/youtubesync.*', youtube_sync.YouTubeSync),
    ('/admin/changeemail', ChangeEmail),
    ('/admin/realtimeentitycount', RealtimeEntityCount),

    ('/devadmin/emailchange', devpanel.Email),
    ('/devadmin/managedevs', devpanel.Manage),
    ('/devadmin/managecoworkers', devpanel.ManageCoworkers),
    ('/devadmin/commoncore', devpanel.CommonCore),

    ('/coaches', coaches.ViewCoaches),
    ('/students', coaches.ViewStudents),
    ('/registercoach', coaches.RegisterCoach),
    ('/unregistercoach', coaches.UnregisterCoach),
    ('/unregisterstudent', coaches.UnregisterStudent),
    ('/requeststudent', coaches.RequestStudent),
    ('/acceptcoach', coaches.AcceptCoach),

    ('/createstudentlist', coaches.CreateStudentList),
    ('/deletestudentlist', coaches.DeleteStudentList),
    ('/removestudentfromlist', coaches.RemoveStudentFromList),
    ('/addstudenttolist', coaches.AddStudentToList),

    ('/individualreport', coaches.ViewIndividualReport),
    ('/progresschart', coaches.ViewProgressChart),
    ('/sharedpoints', coaches.ViewSharedPoints),
    ('/classreport', coaches.ViewClassReport),
    ('/classtime', coaches.ViewClassTime),
    ('/charts', coaches.ViewCharts),

    ('/mailing-lists/subscribe', util_mailing_lists.Subscribe),

    ('/profile/graph/activity', util_profile.ActivityGraph),
    ('/profile/graph/focus', util_profile.FocusGraph),
    ('/profile/graph/exercisesovertime', util_profile.ExercisesOverTimeGraph),
    ('/profile/graph/exerciseproblems', util_profile.ExerciseProblemsGraph),
    ('/profile/graph/exerciseprogress', util_profile.ExerciseProgressGraph),
    ('/profile', util_profile.ViewProfile),

    ('/profile/graph/classexercisesovertime', util_profile.ClassExercisesOverTimeGraph),
    ('/profile/graph/classenergypointsperminute', util_profile.ClassEnergyPointsPerMinuteGraph),
    ('/profile/graph/classtime', util_profile.ClassTimeGraph),
    ('/class_profile', util_profile.ViewClassProfile),

    ('/login', Login),
    ('/login/mobileoauth', MobileOAuthLogin),
    ('/postlogin', PostLogin),
    ('/logout', Logout),

    ('/api-apps/register', oauth_apps.Register),

    # These are dangerous, should be able to clean things manually from the remote python shell

    ('/deletevideoplaylists', DeleteVideoPlaylists),
    ('/killliveassociations', KillLiveAssociations),

    # Below are all discussion related pages
    ('/discussion/addcomment', comments.AddComment),
    ('/discussion/pagecomments', comments.PageComments),

    ('/discussion/addquestion', qa.AddQuestion),
    ('/discussion/expandquestion', qa.ExpandQuestion),
    ('/discussion/addanswer', qa.AddAnswer),
    ('/discussion/editentity', qa.EditEntity),
    ('/discussion/answers', qa.Answers),
    ('/discussion/pagequestions', qa.PageQuestions),
    ('/discussion/clearflags', qa.ClearFlags),
    ('/discussion/flagentity', qa.FlagEntity),
    ('/discussion/voteentity', voting.VoteEntity),
    ('/discussion/updateqasort', voting.UpdateQASort),
    ('/admin/discussion/finishvoteentity', voting.FinishVoteEntity),
    ('/discussion/deleteentity', qa.DeleteEntity),
    ('/discussion/changeentitytype', qa.ChangeEntityType),
    ('/discussion/videofeedbacknotificationlist', notification.VideoFeedbackNotificationList),
    ('/discussion/videofeedbacknotificationfeed', notification.VideoFeedbackNotificationFeed),
    ('/discussion/moderatorlist', qa.ModeratorList),
    ('/discussion/flaggedfeedback', qa.FlaggedFeedback),

    ('/githubpost', github.NewPost),
    ('/githubcomment', github.NewComment),

    ('/toolkit', RedirectToToolkit),

    ('/paypal/ipn', paypal.IPN),

    ('/badges/view', util_badges.ViewBadges),
    ('/badges/custom/create', custom_badges.CreateCustomBadge),
    ('/badges/custom/award', custom_badges.AwardCustomBadge),

    ('/notifierclose', util_notify.ToggleNotify),
    ('/newaccount', Clone),

    ('/jobs', RedirectToJobvite),
    ('/jobs/.*', RedirectToJobvite),

    ('/dashboard', dashboard.Dashboard),
    ('/contentdash', dashboard.ContentDashboard),
    ('/admin/dashboard/record_statistics', dashboard.RecordStatistics),
    ('/admin/entitycounts', dashboard.EntityCounts),

    ('/sendtolog', SendToLog),

    ('/user_video_css', ServeUserVideoCss),

    ('/admin/exercisestats/collectfancyexercisestatistics', exercisestats.CollectFancyExerciseStatistics),
    ('/exercisestats/report', exercisestats.report.Test),
    ('/exercisestats/exerciseovertime', exercisestats.report_json.ExerciseOverTimeGraph),
    ('/exercisestats/geckoboardexerciseredirect', exercisestats.report_json.GeckoboardExerciseRedirect),
    ('/exercisestats/exercisestatsmap', exercisestats.report_json.ExerciseStatsMapGraph),
    ('/exercisestats/exerciseslastauthorcounter', exercisestats.report_json.ExercisesLastAuthorCounter),
    ('/exercisestats/exercisenumbertrivia', exercisestats.report_json.ExerciseNumberTrivia),
    ('/exercisestats/userlocationsmap', exercisestats.report_json.UserLocationsMap),
    ('/exercisestats/exercisescreatedhistogram', exercisestats.report_json.ExercisesCreatedHistogram),

    ('/goals/new', goals.handlers.CreateNewGoal),
    ('/goals/admincreaterandom', goals.handlers.CreateRandomGoalData),

    ('/robots.txt', robots.RobotsTxt),

    ('/r/.*', redirects.Redirect),
    ('/redirects', redirects.List),
    ('/redirects/add', redirects.Add),
    ('/redirects/remove', redirects.Remove),

    # Redirect any links to old JSP version
    ('/.*\.jsp', PermanentRedirectToHome),
    ('/index\contribute', PermanentRedirectToHome),

    ('/_ah/warmup.*', warmup.Warmup),

    # -- KHAN-NL -----------------------------------
    ('/nl-content/.*', nl.Content),
    ('/nl_report', nl_report.BugReporter),
	('/helpmee', nl.LinkerHelpmee),

    ], debug=True)

application = profiler.ProfilerWSGIMiddleware(application)
application = GAEBingoWSGIMiddleware(application)
application = request_cache.RequestCacheMiddleware(application)

def main():
    if os.environ["SERVER_NAME"] == "smarthistory.khanacademy.org":
        run_wsgi_app(applicationSmartHistory)
    else:
        run_wsgi_app(application)

if __name__ == '__main__':
    main()
