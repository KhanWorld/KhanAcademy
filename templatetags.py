import math

from jinja2.utils import escape

from templatefilters import slugify
import topics_list
import models
import shared_jinja

def user_info(username, user_data):
    context = {"username": username, "user_data": user_data}
    return shared_jinja.get().render_template("user_info_only.html", **context)

def column_major_sorted_videos(videos, num_cols=3, column_width=300, gutter=20, font_size=12):
    items_in_column = len(videos) / num_cols
    remainder = len(videos) % num_cols
    link_height = font_size * 1.5
    # Calculate the column indexes (tops of columns). Since video lists won't divide evenly, distribute
    # the remainder to the left-most columns first, and correctly increment the indices for remaining columns
    column_indices = [(items_in_column * multiplier + (multiplier if multiplier <= remainder else remainder)) for multiplier in range(1, num_cols + 1)]

    template_values = {
        "videos": videos,
        "column_width": column_width,
        "column_indices": column_indices,
        "link_height": link_height,
        "list_height": column_indices[0] * link_height,
    }

    return shared_jinja.get().render_template("column_major_order_videos.html", **template_values)

def exercise_message(exercise, user_exercise_graph, sees_graph=False,
        review_mode=False):
    """Render UserExercise html for APIActionResults["exercise_message_html"] listener in khan-exercise.js.

    This is called **each time** a problem is either attempted or a hint is called (via /api/v1.py)
    returns nothing unless a user is struggling, proficient, etc. then it returns the appropriat template

    See Also: APIActionResults

    sees_graph is part of an ab_test to see if a small graph will help
    """

    # TODO(david): Should we show a message if the user gets a problem wrong
    #     after proficiency, to explain that this exercise needs to be reviewed?

    exercise_states = user_exercise_graph.states(exercise.name)

    if review_mode and user_exercise_graph.has_completed_review():
        filename = 'exercise_message_review_finished.html'

    elif (exercise_states['proficient'] and not exercise_states['reviewing'] and
            not review_mode):
        if sees_graph:
            filename = 'exercise_message_proficient_withgraph.html'
        else:
            filename = 'exercise_message_proficient.html'

    elif exercise_states['struggling']:
        filename = 'exercise_message_struggling.html'
        exercise_states['exercise_videos'] = exercise.related_videos_fetch()

    else:
        return None

    return shared_jinja.get().render_template(filename, **exercise_states)

def user_points(user_data):
    if user_data:
        points = user_data.points
    else:
        points = 0

    return {"points": points}

def streak_bar(user_exercise_dict):
    progress = user_exercise_dict["progress"]

    bar_max_width = 228
    bar_width = min(1.0, progress) * bar_max_width

    levels = []
    if user_exercise_dict["summative"]:
        c_levels = user_exercise_dict["num_milestones"]
        level_offset = bar_max_width / float(c_levels)
        for ix in range(c_levels - 1):
            levels.append(math.ceil((ix + 1) * level_offset) + 1)

    template_values = {
        "is_suggested": user_exercise_dict["suggested"],
        "is_proficient": user_exercise_dict["proficient"],
        "float_progress": progress,
        "progress": models.UserExercise.to_progress_display(progress),
        "bar_width": bar_width,
        "bar_max_width": bar_max_width,
        "levels": levels
    }

    return shared_jinja.get().render_template("streak_bar.html", **template_values)

def playlist_browser(browser_id):
    template_values = {
        'browser_id': browser_id, 'playlist_structure': topics_list.PLAYLIST_STRUCTURE
    }

    return shared_jinja.get().render_template("playlist_browser.html", **template_values)

def playlist_browser_structure(structure, class_name="", level=0):
    if type(structure) == list:

        s = ""
        class_next = "topline"
        for sub_structure in structure:
            s += playlist_browser_structure(sub_structure, class_name=class_next, level=level)
            class_next = ""
        return s

    else:

        s = ""
        name = structure["name"]

        if structure.has_key("playlist"):

            playlist_title = structure["playlist"]
            href = "#%s" % escape(slugify(playlist_title))

            # We have two special case playlist URLs to worry about for now. Should remove later.
            if playlist_title.startswith("SAT"):
                href = "/sat"

            if level == 0:
                s += "<li class='solo'><a href='%s' class='menulink'>%s</a></li>" % (href, escape(name))
            else:
                s += "<li class='%s'><a href='%s'>%s</a></li>" % (class_name, href, escape(name))

            if playlist_title=="History":
                s += "<li class=''><a href='#smarthistory'>Art History</a></li>"

        else:
            items = structure["items"]

            if level > 0:
                class_name += " sub"

            s += "<li class='%s'>%s <ul>%s</ul></li>" % (class_name, escape(name), playlist_browser_structure(items, level=level + 1))

        return s

def video_name_and_progress(video):
    return "<span class='vid-progress v%d'>%s</span>" % (video.key().id(), escape(video.title.encode('utf-8', 'ignore')))

