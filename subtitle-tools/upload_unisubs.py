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
import urllib
import urllib2
import httplib
import time
import cgi
import os
import json
from getpass import getpass

# These are the UniSub video IDs of videos where Jeffrey Faus (jeffrey@treesforlife.org)
# has already edited the English subtitles. 
videos_to_avoid = [
                   'rJgSaCBtUcS6',
                   'KewEIJf378xx',
                   'NNXgRj1OhJMv',
                   'SWPJGCVAIjiR',
                   'CcxW75CLF10D',
                   '3H9Uv4LwGnAd',
                   'v9TyVzSc6jE9',
                   'plrQokmupooh',
                   '0cvHoFWiJxVO',
                   'vyHkXQ0rftrs',
                   '8QWKmWCfbSEg',
                   '0r92KW5CaufL',
                   '0ZbIvSy8uGqi',
                   'o3E8fSCZpn47',
                   'GrysaLOpk6a8',
                   'W4bfbRwzT1Uj',
                   'N2eAUJ867i8w',
                   '1CfzViBsqI5Y',
                   'R0M63JmwxIBG',
                   'pvUF46jMbkGd',
                   'nzy9kM1xduJe',
                   'LbI1xrmTN9vN',
                   'EfrRsthcBv9n',
                   'XBA19hqiNg4q',
                   'jBW5oMBej2PB',
                   'AJmS0x8f4fz2',
                   '0Q3fwpNahN56',
                   'o7thaVZ3wj3k',
                   'h12NVgUMWe8q',
                   'khm6vRLb094F',
                   'ryhbquxX3BFG',
                   'FKBvza7PrBi8',
                   'DQmOWFnPps72',
                   'XPmtAX5ocr0S',
                   '7jjJ7z7dr9Fh',
                   'gLUWCAT67fnP',
                   '3sLUVP8OHp8t',
                   'r9ToTcB2feW4',
                   'ZRePOd5k2c66',
                   'sSMHIBfZGNpH',
                   'XnVkldlwjGrW',
                   '7AEG5htSqEXH',
                   'qKd5tmY43hJR',
                   's8qcxlP5m6oo',
                   'ca6dxJrkkyXk',
                   '67nJ44safolt',
                   'nS8y56SERu9r',
                   ]

def main():
    username = getpass('Enter the username for the Universal Subtitles account: ')
    password = getpass('Enter the password for the Universal Subtitles account: ')
    delay = 1
#    hostname = "mirosubs.example.com:8001"
    hostname = "www.universalsubtitles.org"
    apiurl = "http://%s/api/1.0" % hostname
    
    def make_api_call(endpoint, params, form_fields):
        all_params = {
                        "username": username, 
                        "password": password 
                      }
        all_params.update(params)
        qs = urllib.urlencode(all_params)
        post_data = None
        if form_fields is not None:
            post_data = urllib.urlencode(form_fields)
        url = "%s/%s/?%s" % (apiurl, endpoint, qs)
        handle = urllib2.urlopen(url, post_data)
        info = handle.info()
        result = handle.read()
        handle.close()
        return result
    
    def upload_subtitles(unisubs_id, lang_code, caption_text):
        status = make_api_call("subtitles", {}, { "video": unisubs_id,
                                                 "video_language": "en",
                                                 "language": lang_code,
                                                 "format": "srt",
                                                 "subtitles": caption_text
                                                 })
        if status != "OK":
            raise Exception("Unexpected status for language %s: %s" % (lang_code, status))

    def update_subtitles(id, caption_text):
        connection = httplib.HTTPConnection(hostname)
        body = urllib.urlencode({ "language_id": id, "format": "srt", "subtitles": caption_text })
        path_and_query =  "/api/1.0/subtitles/languages/update/?%s"  % urllib.urlencode({
                                                                                         "username": username, 
                                                                                         "password": password
                                                                                         })
        connection.request('PUT', path_and_query, body)
        result = connection.getresponse()
        if result.status != 201 and result.status != 200:
            raise Exception("Unexpected status for language id %s: %s %s" % (id, result.status, result.reason))
        
    completed_youtube_ids_file = open("completed_youtube_ids.txt", 'a')
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
            subtitle_text = None
            while True:
                try:
# curl "http://127.0.0.1:8000/api/1.0/video/?username=admin&password=admin" -d 'video_url=http://www.youtube.com/watch?v=oOOve811tMY' -G
                    print "%s in progress" % id
                    video_info = json.loads(make_api_call("video", { "video_url": "http://www.youtube.com/watch?v=%s" % id }, None))
                    unisubs_id = video_info["video_id"]
                    if unisubs_id in videos_to_avoid:
                        print "Skipping video because %s is in videos_to_avoid" % unisubs_id
                        break
                    languages = json.loads(make_api_call("subtitles/languages", { "video_id": unisubs_id }, None))
                    other_languages = []
                    lang_to_replace = None
                    for lang in languages:
                        if lang["is_original"] and lang["code"] == "en":
                            lang_to_replace = lang
                            break
                                            
                    while True:
                        try:
                            if lang_to_replace is None:
                                print "Uploading en subtitles"
                                upload_subtitles(unisubs_id, "en", caption_text)
                            else:
                                print "Updating subtitles %s" % lang_to_replace["id"]
                                update_subtitles(lang_to_replace["id"], caption_text)
                            break
                        except Exception, err:
                            print "Trying to upload again in 1 minutes due to error: %s" % err
                            time.sleep(60)

                    completed_youtube_ids_file.write("%s\n" % id)
                    completed_youtube_ids_file.flush()
                    print "%s completed (UniSub URL = http://%s/en/videos/%s/)" % (id, hostname, unisubs_id)
                    os.remove(file)
                    print "Resting.  Interrupt during next %d seconds if necessary" % delay
                    time.sleep(delay)
                    break
                except Exception, err:
                    print "Trying again in 1 minutes due to error: %s" % err
                    time.sleep(60)
    completed_youtube_ids_file.close()
if __name__ == '__main__':
    main()