#!/usr/bin/env python
# Copyright (c) 2010, Dean Brettle (dean@brettle.com)
# All rights reserved.
# Licensed under the New BSD License: http://www.opensource.org/licenses/bsd-license.php
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#    * Neither the name of Dean Brettle nor the names of its contributors may be
#      used to endorse or promote products derived from this software without
#      specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

""" Wrapper for uploading/downloading all the system-wide data """

import os, platform, sys
import subprocess
from optparse import OptionParser


def main():
    kinds = ('Exercise',
             'Video',
             'Playlist',
             'ExerciseVideo',
             'ExercisePlaylist',
             'VideoPlaylist',
             'StemmedIndex',
             'LiteralIndex',
             'ExerciseStatistic'
             )
    parser = OptionParser(usage="%prog [options] upload|download",
                          description="Uploads the sample data to a server or downloads it from the server.")
    parser.add_option("-U", "--url", default="http://localhost:8080/remote_api",
                      help="The location of the remote_api endpoint.")
    parser.add_option("-e", "--email", default="test@example.com",
                      help="The username to use.")
    parser.add_option("-k", "--kinds", default=','.join(kinds),
                      help="The comma separated list of kinds.")

    parser.add_option("-p", "--python", default=(sys.executable if platform.system() == "Windows" else None), help="Path of python executable.")
    parser.add_option("-a", "--appcfg", default='appcfg.py', help="Path of appcfg.py (Google App Engine).")
    parser.add_option("-A", "--application", default='dev~khan-academy', help="GAE application name")

    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.print_help()
        return
    for kind in options.kinds.split(','):
        filename='%s.data' % kind
        call_args = [options.appcfg,
                     '--url=%s' % options.url,
                     '--email=%s' % options.email,
                     '--kind=%s' % kind,
                     '--filename=%s' % filename]
        if options.application is not None:
            call_args.append('--application=%s' % options.application)

        if options.email == parser.get_option('--email').default:
            call_args.append('--passin')

        if options.python is not None:
            call_args.insert(0, options.python)

        call_args.append('--num_threads=1')

        if args[0] == 'upload':
            call_args.append('upload_data')
        elif args[0] == 'download':
            if os.path.exists(filename):
                os.remove(filename)
            call_args.append('download_data')
        else:
            parser.print_help()
            return
        print ' '.join(call_args)

        if options.email == parser.get_option('--email').default:
            process = subprocess.Popen(call_args, stdin=subprocess.PIPE)
            # Send a newline for the password prompt
            process.communicate("\n")
        else:
            process = subprocess.Popen(call_args)
        process.wait()

if __name__ == '__main__':
    main()
