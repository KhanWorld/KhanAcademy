#!/usr/bin/python
# -*- coding: utf-8 -*-
import simplejson as json
import user_util

import request_handler

from google.appengine.ext import db

class BugReport(db.Model):

    page = db.StringProperty()
    uagent = db.StringProperty()
    ureport = db.StringProperty()
    ucontact = db.StringProperty()
    utype = db.StringProperty()
    udate = db.StringProperty()
    ustamp = db.StringProperty()

    def delete(self, *args, **kwargs):
        db.Model.delete(self, *args, **kwargs)

    @staticmethod
    def get_for_page(key):
        query = BugReport.all()
        #query.filter("page = ", key)
        return query

class BugReporter(request_handler.RequestHandler):

    @user_util.admin_only
    def get(self):

        self.render_jinja2_template("nl_report.html", {
            "reports" : BugReport.get_for_page(self.request.get("page"))
        })

    def post(self):
        e = BugReport()
        e.page = self.request.get("page")
        e.uagent = self.request.user_agent
        e.ucontact = self.request.get("ucontact")
        e.ureport = self.request.get("ureport")
        e.utype = self.request.get("utype")
        e.udate = self.request.get("udate")
        e.ustamp = self.request.get("ustamp")

        db.put(e)