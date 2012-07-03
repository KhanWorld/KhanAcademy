#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Created on Oct 13, 2010

@author: brettle

New BSD License:

Copyright (c) 2010, Dean Brettle (dean@brettle.com)
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    Redistributions of source code must retain the above copyright notice, 
    this list of conditions and the following disclaimer.
    Redistributions in binary form must reproduce the above copyright 
    notice, this list of conditions and the following disclaimer in the 
    documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
'''

import gdata.youtube
import gdata.youtube.data
import gdata.youtube.service
import gdata.youtube.client
import time
import cgi
import os
from getpass import getpass

def main():
    yt_service = gdata.youtube.service.YouTubeService()
    yt_service.email = 'khanacademy'
    yt_service.password = getpass('Enter the password for the khanacademy account YouTube account: ')
    yt_service.source = 'upload_captions.py'
    yt_service.additional_headers = { 'GData-Version': 2 }
    yt_service.ProgrammaticLogin()
    yt_service.developer_key = getpass('Enter your YouTube developer key: ')
    delay = 3
    for root, dirs, files in os.walk('.'):
        for f in files:
            file = os.path.join(root, f)
            (id, ext) = os.path.splitext(f)
            id = id[0:11]
            if ext.lower() != '.srt':
                continue
            caption_file = open(file, 'r')
            caption_text = caption_file.read()
            caption_file.close()
            while True:
                result = None
                try:
                    caption_post_url = gdata.youtube.client.YOUTUBE_CAPTION_FEED_URI % id
                    print caption_post_url
                    result = yt_service.Post(caption_text, caption_post_url, 
                                             extra_headers={'Content-Type': 'application/vnd.youtube.timedtext; charset=UTF-8',
                                                            'Content-Language': 'en'})
                    print result
                    os.remove(file)
                    time.sleep(delay)
                    break
                except gdata.service.RequestError, err:
                    print "Trying again in 10 minutes due to error: %s" % err
                    delay = min(delay + 1, 10)
                    print "New inter-request delay = %s seconds" % delay
                    time.sleep(600)

if __name__ == '__main__':
    main()