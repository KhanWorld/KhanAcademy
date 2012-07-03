#
# The list of static JS and CSS files served and the packages they belong to.
# This file is munged and auto-regenerated at deploy time!
# See deploy/compress.py to ensure that changes made here are not incompatible
# with that deploy process.
#

transformations = {}
def register_conditional_file(debug_name, prod_name):
    """ Registers a file that has two versions: one for debug and one for
    production.

    This will return the name of the debug file, and include the transformation
    necessary for production in a global "transformations" map.
    """
    transformations[debug_name] = prod_name
    return debug_name

javascript = {
    "shared": {
        "files": [
            # general purpose libs
            "jquery.js",
            "jquery-ui-1.8.16.custom.js",
            "jquery.ui.menu.js",
            "jquery.placeholder.js",
            "jquery.hoverflow.js",
            "../../khan-exercises/utils/underscore.js",
            "backbone.js",
            register_conditional_file("handlebars.js", "handlebars.vm.js"),
            "templates.js",
            "bootstrap-modal.js",
            "../../gae_bingo/static/js/gae_bingo.js",

            # application code & templates:
            "handlebars-extras.js",
            "pageutil.js",
            "api.js",
            "social.js",
            "youtube-player.handlebars",
            "api-version-mismatch.handlebars",
            "streak-bar.handlebars",
            "knowledgemap-exercise.handlebars",
            "knowledgemap-admin-exercise.handlebars",
            "goal-summary-area.handlebars",
            "goalbook-row.handlebars",
            "goalbook.handlebars",
            "goal-objectives.handlebars",
            "goal-new.handlebars",
            "goal-new-dialog.handlebars",
            "goal-new-custom-dialog.handlebars",
            "goal-create.handlebars",
            "goals.js",
        ]
    },
    "video": {
        "files": [
            "jquery.qtip.js",
            "video.js",
            "discussion.js",
            "thumbnail.handlebars",
            "related-video-link.handlebars",
            "modal-video.handlebars",
            "modalvideo.js",
        ]
    },
    "homepage": {
        "files": [
            "jquery.easing.1.3.js",
            "jquery.cycle.all.min.js",
            "waypoints.min.js",
            "videolist.handlebars",
            "homepage.js",
            "ga_social_tracking.js",
        ]
    },
    "exercisestats": {
        "files": [
            "highcharts.js",
        ]
    },
    "profile": {
        "files": [
            "jquery.address-1.4.min.js",
            "highcharts.js",
            "profile-goals.handlebars",
            "profile-class-goals.handlebars",
            "profile-class-progress-report.handlebars",
            "class-progress-column.handlebars",
            "class-progress-summary.handlebars",
            "exercise_progress.handlebars",
            "profile.js",
        ]
    },
    "maps": {
        "files": [
            "fastmarkeroverlay.js",
            "knowledgemap.js",
        ]
    },
    "mobile": {
        "files": [
            "jquery.js",
            "jquery.mobile-1.0a4.1.js",
            "iscroll-lite.min.js",
            "mobile.js",
        ]
    },
    "studentlists": {
        "files": [
            "studentlists.js",
            "classprofile.js",
        ]
    },
    "exercises": {
        "base_path": "../khan-exercises",
        "base_url": "/khan-exercises",
        "files": [
            "khan-exercise.js",
            "utils/angles.js",
            "utils/answer-types.js",
            "utils/calculus.js",
            "utils/congruence.js",
            "utils/convert-values.js",
            "utils/d3.js",
            "utils/derivative-intuition.js",
            "utils/exponents.js",
            "utils/expressions.js",
            "utils/functional.js",
            "utils/graphie-geometry.js",
            "utils/graphie-helpers-arithmetic.js",
            "utils/graphie-helpers.js",
            "utils/graphie-polygon.js",
            "utils/graphie.js",
            "utils/interactive.js",
            "utils/jquery.mobile.vmouse.js",
            "utils/math-format.js",
            "utils/math.js",
            "utils/mean-and-median.js",
            "utils/NL.js",
            "utils/parabola-intuition.js",
            "utils/polynomials.js",
            "utils/probability.js",
            "utils/raphael.js",
            "utils/scratchpad.js",
            "utils/slice-clone.js",
            "utils/stat.js",
            "utils/tmpl.js",
            "utils/word-problems.js",
            "utils/spin.js",
            "utils/unit-circle.js",
        ]
    },
}

stylesheets = {
    "shared": {
        "files": [
            "default.css",
            "rating.css",
            "stylesheet.css",
            "menu.css",
            "profile.css",
            "museo-sans.css",
            "jquery-ui-1.8.16.custom.css",
            "bootstrap-modal.css",
            "goals.css",
        ]
    },
    "mobile": {
        "files": [
            "jquery.mobile-1.0a4.1.css",
            "mobile.css",
        ]
    },
    "video": {
        "files": [
            "jquery.qtip.css",
            "video.css",
            "discussion.css",
            "modalvideo.css",
        ]
    },
    "studentlists": {
        "files": [
            "viewstudentlists.css",
            "viewclassprofile.css",
        ]
    },
    "exercises": {
        "base_path": "../khan-exercises/css",
        "base_url": "/khan-exercises/css",
        "files": [
            "khan-exercise.css",
        ]
    },
}
