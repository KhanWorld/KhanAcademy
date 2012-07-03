import datetime

from google.appengine.api import users

from app import App
import request_handler
import user_util
from dashboard.models import DailyStatistic, EntityStatistic
from google.appengine.ext.db import stats
from itertools import groupby

class Dashboard(request_handler.RequestHandler):
    """
    Handles request to show the main internal dashboard.
    
    Shows graphs for particular entity counts which may be specified as
    a comma separated URL parameter called "kinds".
    
    """

    DEFAULT_KINDS = ','.join([
            'RegisteredUser',
            'ProblemLog',
    ])

    def get(self):
        if not user_util.is_current_user_developer():
            if App.dashboard_secret and self.request_string("x", default=None) != App.dashboard_secret:
                self.redirect(users.create_login_url(self.request.uri))
                return

        kinds = self.request_string("kinds", Dashboard.DEFAULT_KINDS).split(',')

        graphs = []
        for kind in kinds:
            d = daily_graph_context(EntityStatistic(kind), "data")
            d['kind_name'] = kind
            d['title'] = "%s created per day" % kind
            graphs.append(d)

        self.render_jinja2_template("dashboard/dashboard.html", {'graphs': graphs})

def daily_graph_context(cls, key):
    # Grab last ~4 months
    counts = cls.all().order("-dt").fetch(31 * 4)

    # Flip 'em around
    counts.reverse()

    # Grab deltas
    count_last = None
    for count in counts:
        if count_last:
            count.delta = count.val - count_last.val

        # Better to show date previous to date stat recorded.
        count.dt_display = count.dt - datetime.timedelta(days=1)
        count.js_month = count.dt_display.month - 1
        count_last = count

    return { key: filter(lambda count: hasattr(count, "delta"), counts) }

class RecordStatistics(request_handler.RequestHandler):
    def get(self):
        return self.post()

    def post(self):
        DailyStatistic.record_all()
        self.response.out.write("Dashboard statistics recorded.")

class EntityCounts(request_handler.RequestHandler):
    @user_util.developer_only
    def get(self):
        kind_stats = [s for s in stats.KindStat.all().fetch(1000)]

        counts = []
        kind_stats.sort(key=lambda s: s.kind_name)
        for key,group in groupby(kind_stats, lambda s: s.kind_name):
            grouped = sorted(group, key=lambda s: s.timestamp, reverse=True)
            counts.append(dict(kind=key, count=grouped[0].count, timestamp=grouped[0].timestamp))

        self.render_jinja2_template("dashboard/entitycounts.html", {'counts':counts})
        

class ContentDashboard(request_handler.RequestHandler):
    """
    Handles request to show an internal dashboard that shows problematic
    issues in our content.
    
    An example of data that would go in this dashboard are statistics
    related to searches users make where they cannot find content for.
    
    """

    def get(self):
        # Right now there is no dynamic data from the db necessary.
        # the template does, however, query Google Analytics
        self.render_jinja2_template("dashboard/contentdash.html", {})
