#!/usr/bin/env python

""" Wrapper for uploading/downloading all the system-wide data """

import os, platform, sys
import subprocess
from optparse import OptionParser

def main():

    # TODO : query the App Engine metadata to determine all kinds
    kinds = ('Comment', 
             'DailyActivityLog', 
             'DiscussAnswer', 
             'DiscussQuestion', 
             'ExercisePlaylist', 
             'ExerciseVideo',
             'Exercise',
             'FeedbackNotification',
             'Feedback',
             'HourlyActivityLog',
             'Playlist',
             'ProblemLog',
             'Question',
             'Setting',
             'StemmedIndex',
             'UserBadge',
             'UserData',
             'UserExercise',
             'UserPlaylist',
             'UserVideo',
             'VideoLog',
             'VideoPlaylist',
             'Video',
             'YouTubeSyncStepLog'
            )
             
    parser = OptionParser(usage="%prog [options]", 
                          description="Downloads a data and progress file for each entity kind in SQLite3 format.")
    parser.add_option("-U", "--url", default="http://localhost:8080/remote_api",
                      help="The location of the remote_api endpoint.")
    parser.add_option("-e", "--email", default="test@example.com",
                      help="The username to use.")
    parser.add_option("-k", "--kinds", default=','.join(kinds),
                      help="The comma separated list of kinds.")
    parser.add_option("-p", "--python", default=(sys.executable if platform.system() == "Windows" else None), help="Path of python executable.")
    parser.add_option("-a", "--appcfg", default='appcfg.py', help="Path of appcfg.py (Google App Engine).")
    parser.add_option("-A", "--application", default='khanexercises', help="GAE application name")
    # Performance options
    parser.add_option("-n", "--num_threads", default='55', help="num_threads, passed to bulkloader")
    parser.add_option("-s", "--batch_size", default='500', help="batch_size, passed to bulkloader")
    parser.add_option("-b", "--bandwidth_limit", default='10000000', help="bandwidth_limit, passed to bulkloader")
    parser.add_option("-r", "--rps_limit", default='15000', help="rps_limit of threads, passed to bulkloader")
    parser.add_option("-c", "--http_limit", default='40', help="http_limit, passed to bulkloader")
    parser.add_option("-x", "--passin", default='', help="Path to file containing Google App Engine password")
 
    (options, args) = parser.parse_args()

    files = []
    for kind in options.kinds.split(','):

        filename='bulkloader-results.%s.data' % kind
        db_filename='bulkloader-progress.%s.data' % kind
        files.append(filename)
        files.append(db_filename)
        
        if os.path.exists(filename):
            os.remove(filename)
        if os.path.exists(db_filename):
            os.remove(db_filename)
        
        call_args = [options.appcfg,
                     '--url=%s' % options.url,
                     '--email=%s' % options.email,
                     '--kind=%s' % kind,
                     '--db_filename=%s' % db_filename,
                     '--filename=%s' % filename,
                     '--num_threads=%s' % options.num_threads,
                     '--batch_size=%s' % options.batch_size,
                     '--bandwidth_limit=%s' % options.bandwidth_limit,
                     '--rps_limit=%s' % options.rps_limit,
                     '--http_limit=%s' % options.http_limit
                    ]
        if options.application is not None:
            call_args.append('--application=%s' % options.application)
        if options.email == parser.get_option('--email').default or options.passin:
            call_args.append('--passin')
        if options.python is not None:
            call_args.insert(0, options.python)
        call_args.append('download_data')

        print ' '.join(call_args)

        if options.email == parser.get_option('--email').default:

            process = subprocess.Popen(call_args, stdin=subprocess.PIPE)
            # Send a newline for the password prompt
            process.communicate("\n")

        elif options.passin:

            f = open(options.passin, "r")
            password = f.read()
            f.close()

            # Send contents of password file for the password prompt
            process = subprocess.Popen(call_args, stdin=subprocess.PIPE)
            process.communicate(password)

        else:

            process = subprocess.Popen(call_args)
        process.wait()

    # zip up all created progress and results files
    os.system("zip bulkloader.zip bulkloader-*.data")
    os.system("rm bulkloader-*")  # warning: this will blow away the logs and extra results db's, too!


if __name__ == '__main__':
    main()
