import datetime
import logging
import copy

from google.appengine.api import users
from google.appengine.ext import deferred

from asynctools import AsyncMultiTask, QueryTask

import util
from models import UserExercise, Exercise, UserData, ProblemLog, VideoLog, LogSummary, LogSummaryTypes
import activity_summary

def dt_to_utc(dt, timezone_adjustment):
    return dt - timezone_adjustment

def dt_to_ctz(dt, timezone_adjustment):
    return dt + timezone_adjustment

# bulk loads the entire class data for the day
def reload_class(user_data_coach, dt_start_utc):
    students_data = user_data_coach.get_students_data()
    dt_start_utc1 = datetime.datetime(dt_start_utc.year, dt_start_utc.month, dt_start_utc.day)

    for student_data in students_data:
        deferred.defer(fill_class_summaries_from_logs, user_data_coach, [student_data], dt_start_utc1)

    if dt_start_utc1 != dt_start_utc:
        dt_start_utc2 =  dt_start_utc1 + datetime.timedelta(days = 1)
        for student_data in students_data:
            deferred.defer(fill_class_summaries_from_logs, user_data_coach, [student_data], dt_start_utc2)

#bulk loader of student data into the LogSummaries where there is one LogSummary per day per coach
#can get in memory trouble if handling a large class - so break it up and send only one student at a time
def fill_class_summaries_from_logs(user_data_coach, students_data, dt_start_utc):
    dt_end_utc = dt_start_utc + datetime.timedelta(days = 1)    

   # Asynchronously grab all student data at once
    async_queries = []
    for user_data_student in students_data:
        query_problem_logs = ProblemLog.get_for_user_data_between_dts(user_data_student, dt_start_utc, dt_end_utc)
        query_video_logs = VideoLog.get_for_user_data_between_dts(user_data_student, dt_start_utc, dt_end_utc)

        async_queries.append(query_problem_logs)
        async_queries.append(query_video_logs)

    # Wait for all queries to finish
    results = util.async_queries(async_queries, limit=10000)

    for i, user_data_student in enumerate(students_data):
        logging.info("working on student "+str(user_data_student.user))
        problem_and_video_logs = []

        problem_logs = results[i * 2].get_result()
        video_logs = results[i * 2 + 1].get_result()
        
        for problem_log in problem_logs:
            problem_and_video_logs.append(problem_log)
        for video_log in video_logs:
            problem_and_video_logs.append(video_log)

        problem_and_video_logs = sorted(problem_and_video_logs, key=lambda log: log.time_started())

        if problem_and_video_logs:       
            LogSummary.add_or_update_entry(user_data_coach, problem_and_video_logs, ClassDailyActivitySummary, LogSummaryTypes.CLASS_DAILY_ACTIVITY, 1440)
    
class ClassTimeAnalyzer:

    def __init__(self, timezone_offset = 0, downtime_minutes = 30):
        self.tried_logs = False
        
        self.timezone_offset = timezone_offset
        self.timezone_adjustment = datetime.timedelta(minutes = self.timezone_offset)

        # Number of downtime minutes considered to indicate a new 'chunk' of work
        self.chunk_delta = datetime.timedelta(minutes = downtime_minutes)

    def dt_to_utc(self, dt):
        return dt - self.timezone_adjustment

    def dt_to_ctz(self, dt):
        return dt + self.timezone_adjustment

    # gets the classtime table by looking in the log summary for ClassDailyActivity summaries 
    def get_classtime_table_by_coach(self, user_data_coach, students_data, dt_start_utc):
        logging.info("getting classtime table for "+str(dt_start_utc))
        
        #ctz will be from midnight to midnight on the day they are looking at
        dt_start_ctz = self.dt_to_ctz(dt_start_utc)
        dt_end_ctz = dt_start_ctz + datetime.timedelta(days = 1)
        
        classtime_table = ClassTimeTable(dt_start_ctz, dt_end_ctz)   

        # midnight at PST is 7AM UTC and hence the coach's day in UTC goes from 7AM to 7AM the next day, spanning two different UTC days 
        dt_end_utc = dt_start_utc + datetime.timedelta(days = 1)

        # find the first utc days that spans the teacher's day
        dt_start_utc1 = datetime.datetime(dt_start_utc.year, dt_start_utc.month, dt_start_utc.day)
        dt_end_utc1 = dt_start_utc1 + datetime.timedelta(days = 1)

        # get the query to get the summary shards from the first day
        log_summary_query_1 = LogSummary.get_by_name(LogSummary.get_name_by_dates(user_data_coach, LogSummaryTypes.CLASS_DAILY_ACTIVITY, dt_start_utc1, dt_end_utc1))
        

        # find the second utc day that spans the teacher's day
        dt_start_utc2 = dt_end_utc1
        dt_end_utc2 = dt_start_utc2 + datetime.timedelta(days = 1)

        log_summary_query_2 = LogSummary.get_by_name(LogSummary.get_name_by_dates(user_data_coach, LogSummaryTypes.CLASS_DAILY_ACTIVITY, dt_start_utc2, dt_end_utc2))

        results = util.async_queries([log_summary_query_1, log_summary_query_2], limit = 10000)

        class_summary_shards = results[0].get_result()
        class_summary = None
        if class_summary_shards: 
            class_summary = reduce(lambda x, y: x.merge_shard(y), map(lambda x: x.summary, class_summary_shards)) 

        class_summary_day2_shards = results[1].get_result()
        class_summary_day2 = None
        if class_summary_day2_shards:
            class_summary_day2 = reduce(lambda x, y: x.merge_shard(y), map(lambda x: x.summary, class_summary_day2_shards))

        if class_summary_day2 is not None:
            if class_summary is not None :        
                class_summary.merge_day(class_summary_day2)
            else:
                class_summary = class_summary_day2
        
        if not class_summary:
            return classtime_table

        rows = 0
        # only consider sudents that are in the coach's currently looked at list (some students might have stopped having their current coach, or we might only be interested in a coach's student_list
        for i, user_data_student in enumerate(students_data):

            # check to see if the current student has had any activity 
            if class_summary.student_dict.has_key(user_data_student.user):
                    
                # loop over all chunks of that day
                for adjacent_activity_summary in class_summary.student_dict[user_data_student.user]:

                    # make sure the chunk falls within the day specified by the coach's timezone
                    if adjacent_activity_summary.start > dt_start_utc and adjacent_activity_summary.start < dt_end_utc:
                    
                        rows += 1
                        adjacent_activity_summary.setTimezoneOffset(self.timezone_offset)

                        classtime_table.drop_into_column(adjacent_activity_summary, i)      
        
        logging.info("summary by coach rows="+str(rows))

        return classtime_table 

    def get_classtime_table_old(self, students_data, dt_start_utc):

        dt_start_ctz = self.dt_to_ctz(dt_start_utc)
        dt_end_ctz = dt_start_ctz + datetime.timedelta(days = 1)

        column = 0

        classtime_table = ClassTimeTable(dt_start_ctz, dt_end_ctz)

        # Asynchronously grab all student data at once
        async_queries = []
        for user_data_student in students_data:

            query_problem_logs = ProblemLog.get_for_user_data_between_dts(user_data_student, self.dt_to_utc(dt_start_ctz), self.dt_to_utc(dt_end_ctz))
            query_video_logs = VideoLog.get_for_user_data_between_dts(user_data_student, self.dt_to_utc(dt_start_ctz), self.dt_to_utc(dt_end_ctz))

            async_queries.append(query_problem_logs)
            async_queries.append(query_video_logs)

        # Wait for all queries to finish
        results = util.async_queries(async_queries, limit=10000)

        rows = 0
        chunks = 0
        for i, user_data_student in enumerate(students_data):

            problem_logs = results[i * 2].get_result()
            video_logs = results[i * 2 + 1].get_result()

            problem_and_video_logs = []

            for problem_log in problem_logs:
                problem_and_video_logs.append(problem_log)
            for video_log in video_logs:
                problem_and_video_logs.append(video_log)

            problem_and_video_logs = sorted(problem_and_video_logs, key=lambda log: log.time_started())
            rows += len(problem_and_video_logs)
            
            chunk_current = None

            for activity in problem_and_video_logs:   

                if chunk_current is not None and self.dt_to_ctz(activity.time_started()) > (chunk_current.end + self.chunk_delta):
                    chunks += 1

                    classtime_table.drop_into_column_old(chunk_current, column)
                    chunk_current.description()
                    chunk_current = None

                if chunk_current is None:
                    chunk_current = ClassTimeChunk()
                    chunk_current.user_data_student = user_data_student
                    chunk_current.start = self.dt_to_ctz(activity.time_started())
                    chunk_current.end = self.dt_to_ctz(activity.time_ended())

                chunk_current.activities.append(activity)
                chunk_current.end = min(self.dt_to_ctz(activity.time_ended()), dt_end_ctz)

            if chunk_current is not None:
                chunks += 1

                classtime_table.drop_into_column_old(chunk_current, column)
                chunk_current.description()

            column += 1

        logging.info("old rows="+str(rows)+", old chunks="+str(chunks))
        classtime_table.balance()
        return classtime_table
  

class ClassTimeTable:
    def __init__(self, dt_start_ctz, dt_end_ctz):
        self.rows = []
        self.height = 0
        self.student_totals = {}
        self.dt_start_ctz = dt_start_ctz
        self.dt_end_ctz = dt_end_ctz

    def update_student_total(self, chunk):
        email = chunk.user_data_student.email() if callable(getattr(chunk.user_data_student, "email")) else chunk.user_data_student.email
        if not self.student_totals.has_key(email):
            self.student_totals[email] = 0
        self.student_totals[email] += chunk.minutes_spent()

    def get_student_total(self, student_email):
        if self.student_totals.has_key(student_email):
            return self.student_totals[student_email]
        return 0

    def dt_start_ctz_formatted(self):
        return self.dt_start_ctz.strftime("%m/%d/%Y")

    def schoolday_start(self):
        return datetime.datetime(
                year = self.start.year, 
                month = self.start.month, 
                day = self.start.day, 
                hour = ClassTimeChunk.SCHOOLDAY_START_HOURS)

    def schoolday_end(self):
        return datetime.datetime(
                year = self.start.year, 
                month = self.start.month, 
                day = self.start.day, 
                hour = ClassTimeChunk.SCHOOLDAY_END_HOURS)

    def during_schoolday(self):
        return self.start >= self.schoolday_start() and self.end <= self.schoolday_end()

    def drop_into_column(self, chunk, column):
        #not splitting up summary like old drop_into_column as it does not contain the individual logs
        
        ix = 0
        height = len(self.rows)
        while ix < height:
            if column >= len(self.rows[ix].chunks) or self.rows[ix].chunks[column] is None:
                break
            ix += 1

        if ix >= height:
            self.rows.append(ClassTimeRow())

        while len(self.rows[ix].chunks) <= column:
            self.rows[ix].chunks.append(None)

        self.rows[ix].chunks[column] = chunk

        self.update_student_total(chunk)

    def drop_into_column_old(self, chunk, column):

        chunks_split = chunk.split_schoolday()
        if chunks_split is not None:
            for chunk_after_split in chunks_split:
                if chunk_after_split is not None:
                    self.drop_into_column_old(chunk_after_split, column)
            return

        ix = 0
        height = len(self.rows)
        while ix < height:
            if column >= len(self.rows[ix].chunks) or self.rows[ix].chunks[column] is None:
                break
            ix += 1

        if ix >= height:
            self.rows.append(ClassTimeRow())

        while len(self.rows[ix].chunks) <= column:
            self.rows[ix].chunks.append(None)

        self.rows[ix].chunks[column] = chunk

        self.update_student_total(chunk)

    def balance(self):
        width = 0
        height = len(self.rows)
        for ix in range(0, height):
            if len(self.rows[ix].chunks) > width:
                width = len(self.rows[ix].chunks)

        for ix in range(0, height):
            while len(self.rows[ix].chunks) < width:
                self.rows[ix].chunks.append(None)

class ClassTimeRow:
    def __init__(self):
        self.chunks = []

class ClassTimeChunk:

    SCHOOLDAY_START_HOURS = 8 # 8am
    SCHOOLDAY_END_HOURS = 15 # 3pm

    def __init__(self):
        self.user_data_student = None
        self.start = None
        self.end = None
        self.activities = []
        self.cached_activity_class = None

    def minutes_spent(self):
        return util.minutes_between(self.start, self.end)

    def activity_class(self):

        if self.cached_activity_class is not None:
            return self.cached_activity_class

        has_exercise = False
        has_video = False

        for activity in self.activities:
            has_exercise = has_exercise or type(activity) == ProblemLog
            has_video = has_video or type(activity) == VideoLog

        if has_exercise and has_video:
            self.cached_activity_class = "exercise_video"
        elif has_exercise:
            self.cached_activity_class = "exercise"
        elif has_video:
            self.cached_activity_class = "video"

        return self.cached_activity_class

    def schoolday_start(self):
        return datetime.datetime(
                year = self.start.year, 
                month = self.start.month, 
                day=self.start.day, 
                hour=ClassTimeChunk.SCHOOLDAY_START_HOURS)

    def schoolday_end(self):
        return datetime.datetime(
                year = self.start.year, 
                month = self.start.month, 
                day=self.start.day, 
                hour=ClassTimeChunk.SCHOOLDAY_END_HOURS)

    def during_schoolday(self):
        return self.start >= self.schoolday_start() and self.end <= self.schoolday_end()

    def split_schoolday(self):

        school_start = self.schoolday_start()
        school_end = self.schoolday_end()

        pre_schoolday = None
        schoolday = None
        post_schoolday = None

        if self.start < school_start and self.end > school_start:
            pre_schoolday = copy.copy(self)
            pre_schoolday.end = school_start

            schoolday = copy.copy(self)
            schoolday.start = school_start

        if self.start < school_end and self.end > school_end:
            post_schoolday = copy.copy(self)
            post_schoolday.start = school_end

            if schoolday is None:
                schoolday = copy.copy(self)
                schoolday.start = self.start

            schoolday.end = school_end

        if pre_schoolday is not None or schoolday is not None or post_schoolday is not None:
            return [pre_schoolday, schoolday, post_schoolday]

        return None

    def description(self):
        dict_videos = {}
        dict_exercises = {}

        for activity in self.activities:

            dict_target = None
            name_activity = None

            if type(activity) == ProblemLog:
                name_activity = activity.exercise
                dict_target = dict_exercises
            elif type(activity) == VideoLog:
                name_activity = activity.video_title
                dict_target = dict_videos

            if dict_target is not None:

                # For older data that doesn't have video titles recorded
                if name_activity is None:
                    name_activity = "Unknown"

                if not dict_target.has_key(name_activity):
                    dict_target[name_activity] = True

        desc_videos = ""
        for key in dict_videos:
            if len(desc_videos) > 0:
                desc_videos += "<br/>"
            desc_videos += " - <em>%s</em>" % key
        if len(desc_videos) > 0:
            desc_videos = "<br/><b>Videos:</b><br/>" + desc_videos

        desc_exercises = ""
        for key in dict_exercises:
            if len(desc_exercises) > 0:
                desc_exercises += "<br/>"
            desc_exercises += " - <em>%s</em>" % Exercise.to_display_name(key)
        if len(desc_exercises) > 0:
            desc_exercises = "<br/><b>Exercises:</b><br/>" + desc_exercises

        desc = ("<b>%s</b> - <b>%s</b><br/>(<em>~%.0f min.</em>)" % (self.start.strftime("%I:%M%p"), self.end.strftime("%I:%M%p"), self.minutes_spent())) + "<br/>" + desc_videos + desc_exercises

        return desc

# stores the adjacent activities for all students of a particular coach
class ClassDailyActivitySummary:
    def __init__(self):
        self.student_dict = {} # a mapping between the user_data_student and a list of their adjacent activity summaries for the current time period
        self.user_data_coach = None

    def add(self, user, activity):
        if self.user_data_coach is None:
            self.user_data_coach = user
        elif self.user_data_coach.user_id != user.user_id:
            raise Exception("Trying to add a activity belonging to the coach %s to the ClassDailyActivitySummary of %s" % (user.user, self.user_data_coach.user))

        user_data_student = activity.user
        if self.student_dict.has_key(activity.user):
            # cycle through the students adjacent activity summaries to see if the current activity is close enough to and should be added to them
            for adjacent_summary in self.student_dict[activity.user]:
                if adjacent_summary.should_include(activity):
                    adjacent_summary.add(activity.user, activity)
                    return
        
        # no summary close to the current activity was found so making a new one    
        new_summary = UserAdjacentActivitySummary()
        new_summary.add(activity.user, activity)
        if self.student_dict.has_key(activity.user):
            self.student_dict[activity.user].append(new_summary)
        else:
            self.student_dict[activity.user] = [new_summary]      

    # cycles through all students and adds the second days data (assumed to be the next day) to the first, in the case that an activity chunk was started near midnight UTC between the two days it will merge those two AdjacentActivitySummaries together
    def merge_day(self, second_summary):
        
        for student, second_summary_list in second_summary.student_dict.iteritems():
            if self.student_dict.has_key(student):
                first_summary_list = self.student_dict[student]

                #check to see if the last summary of the first day is close enough to the first summary of the next day to merge the two, if so then merge them
                if first_summary_list[-1].should_merge(second_summary_list[0]):
                    first_summary_list[-1].merge(second_summary_list[0])
                    first_summary_list.extend(second_summary_list[1:])
                else:
                    first_summary_list.extend(second_summary_list)
            else:
                self.student_dict[student] = second_summary_list             


    # cycles through all students and adds the second summary data to the first, it will merge any two AdjacentActivitySummaries together if they are close enough to be merged
    def merge_shard(self, second_summary):

        for student, second_summary_list in second_summary.student_dict.iteritems():
            if self.student_dict.has_key(student):
                first_summary_list = self.student_dict[student]
                self.student_dict[student] = self._merge_lists(first_summary_list, second_summary_list)
            else:
                self.student_dict[student] = second_summary_list       
        
        return self


    # merges two lists of adjacent activity summaries
    @staticmethod
    def _merge_lists(listA, listB):
        merged_list = []
        key1 = 0
        key2 = 0
        key3 = -1 # holds always the index of the last item in the merged_list
        lenA = len(listA)
        lenB = len(listB)
        
        while key1 < lenA or key2 < lenB:
            # there is some item in one of the lists left to merge
        
            if key1 < lenA and (key2 >= lenB or listA[key1].start < listB[key2].start):
                # the next earliest item is in listA

                if key3 >= 0 and merged_list[key3].should_merge(listA[key1]):
                    # merged_list is not empty and its last item should be merged with the current item in listA
                    merged_list[key3].merge(listA[key1])

                else:
                    # the next earliest item in listA is not close enough to the last item in the merged list to merge with it, so just adding it to the end of the merged_list as a new item
                    key3 += 1
                    merged_list.append(listA[key1])

                # for the current item in listA we've either added to the end or merged with the last item in the merged list, so now lets look at next item in listA
                key1 += 1

            else:
                #the next earliest item is in listB

                if key3 >= 0 and merged_list[key3].should_merge(listB[key2]):
                    # merged_list is not empty and its last item should be merged with the current item in listB
                    merged_list[key3].merge(listB[key2])

                else:
                    # the next earliest item in listB is not close enough to the last item in the merged list to merge with it, so just adding it to the end of the merged_list as a new item
                    key3 += 1
                    merged_list.append(listB[key2])

                # for the current item in listB we've either added to the end or merged with the last item in the merged list, so now lets look at next item in listB 
                key2 += 1

        return merged_list

#similar to the ClassTimeChunk but does not record the individual logs
class UserAdjacentActivitySummary:
    SCHOOLDAY_START_HOURS = 8 # 8am
    SCHOOLDAY_END_HOURS = 15 # 3pm
    DELTA = 30 #minutes

    def __init__(self):
        self.user_data_student = None
        self.start = None
        self.end = None
        self.dict_videos = {}
        self.dict_exercises = {}
        self.activity_class = None

    def setTimezoneOffset(self, offset):
        adjustment = datetime.timedelta(minutes = offset)
        self.start = self.start + adjustment
        self.end = self.end + adjustment

    def minutes_spent(self):
        return util.minutes_between(self.start, self.end)

    def activity_class(self):
        return self.activity_class

    def should_include(self, activity):
        return activity.time_ended()+datetime.timedelta(minutes=self.DELTA) > self.start and activity.time_started()-datetime.timedelta(minutes=self.DELTA) < self.end

    def should_merge(self, second_summary):
        return self.start - datetime.timedelta(minutes=self.DELTA) < second_summary.start < self.end+datetime.timedelta(minutes=self.DELTA) or \
            self.start - datetime.timedelta(minutes=self.DELTA) < second_summary.end < self.end+datetime.timedelta(minutes=self.DELTA) 
        
    def update_activity_class(self):
        if len(self.dict_exercises) and len(self.dict_videos):
            self.activity_class = "exercise_video"
        
        elif len(self.dict_exercises): 
            self.activity_class = "exercise"
        
        elif len(self.dict_videos):
            self.activity_class = "videos"

        else:
            self.activity_class = None
   
    def merge(self, second_summary):
        self.start = min(self.start, second_summary.start)
        self.end = max(self.end, second_summary.end)
        self.dict_videos.update(second_summary.dict_videos)
        self.dict_exercises.update(second_summary.dict_exercises)
        

    #updates the activity class based upon the new activity
    def update_activity_class(self, activity):
        if self.activity_class is None:
            if type(activity) == ProblemLog:
                self.activity_class = "exercise"
            elif type(activity) == VideoLog:
                self.activity_class = "video"
            elif (self.activity_class == "exercise" and type(activity) == VideoLog) or (self.activity_class == "video" and type(activity) == ProblemLog): 
                self.activity_class = "exercise_video"
        return self.activity_class

    def schoolday_start(self):
        return datetime.datetime(
                year = self.start.year, 
                month = self.start.month, 
                day=self.start.day, 
                hour=ClassTimeChunk.SCHOOLDAY_START_HOURS)

    def schoolday_end(self):
        return datetime.datetime(
                year = self.start.year, 
                month = self.start.month, 
                day=self.start.day, 
                hour=ClassTimeChunk.SCHOOLDAY_END_HOURS)

    #redefining chunk as being within a schoolday if any part of it is within the school day
    def during_schoolday(self):
        return (self.start >= self.schoolday_start() and self.start <= self.schoolday_end()) or (self.end >= self.schoolday_start() and self.end <= self.schoolday_end())  

    def add(self, user, activity):
        self.user_data_student = activity.user
        self.start = min(self.start, activity.time_started()) if self.start is not None else activity.time_started()
        self.end   = max(self.end, activity.time_ended()) if self.end is not None else activity.time_ended()

        dict_target = None
        name_activity = None

        if type(activity) == ProblemLog:
            name_activity = activity.exercise
            dict_target = self.dict_exercises
        elif type(activity) == VideoLog:
            name_activity = activity.video_title
            dict_target = self.dict_videos

        if dict_target is not None:
            # For older data that doesn't have video titles recorded
            if name_activity is None:
                name_activity = "Unknown"

            if not dict_target.has_key(name_activity):
                dict_target[name_activity] = True

        self.update_activity_class(activity)

    def description(self):
        desc_videos = ""
        for key in self.dict_videos:
            if len(desc_videos) > 0:
                desc_videos += "<br/>"
            desc_videos += " - <em>%s</em>" % key
        if len(desc_videos) > 0:
            desc_videos = "<br/><b>Videos:</b><br/>" + desc_videos

        desc_exercises = ""
        for key in self.dict_exercises:
            if len(desc_exercises) > 0:
                desc_exercises += "<br/>"
            desc_exercises += " - <em>%s</em>" % Exercise.to_display_name(key)
        if len(desc_exercises) > 0:
            desc_exercises = "<br/><b>Exercises:</b><br/>" + desc_exercises
 
        desc = ("<b>%s</b> - <b>%s</b><br/>(<em>~%.0f min.</em>)" % (self.start.strftime("%I:%M%p"), self.end.strftime("%I:%M%p"), self.minutes_spent())) + "<br/>" + desc_videos + desc_exercises

        return desc


