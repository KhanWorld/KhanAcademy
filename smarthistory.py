#for blobstore of images
from __future__ import with_statement
from google.appengine.api import files, urlfetch
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.blobstore import BlobInfo

import logging
import layer_cache
import urllib
import urllib2

from models import Setting

from request_handler import RequestHandler

from custom_exceptions import SmartHistoryLoadException 

from datetime import datetime


SMARTHISTORY_CACHE_EXPIRATION_TIME=86400
SMARTHISTORY_IMAGE_CACHE_EXPIRATION=2419200 #28 days
SMARTHISTORY_URL = "http://khan.smarthistory.org"

def deleteOldBlobs():
    blobs=BlobInfo.all().fetch(500)
    for blob in blobs:
        if blob.filename.find(SMARTHISTORY_URL) != -1:
            age = datetime.now() - blob.creation
            if age.days * 86400 + age.seconds >= SMARTHISTORY_IMAGE_CACHE_EXPIRATION:
                blob.delete()

class SmartHistoryProxy(RequestHandler, blobstore_handlers.BlobstoreDownloadHandler):
    def __init__(self):
        self.attempt_counter = 0	
	
    def get(self):

        if self.request.params.has_key("clearcache"):
            self.clearCache()
       
        if self.request.path == "/robots.txt":
            self.response.headers["Content-Type"]="text/plain"
            self.response.out.write("User-agent: *\r\nDisallow:")
            return

        #redirect file back to smarthistory.org if the file is an audio/video and hence might be too big to store in blobstore
        extension = self.request.path[self.request.path.rfind(".") + 1:]
        if extension.lower() in ("mp3", "m4a", "flv", "mp4", "mov", "avi", "m4v", "swf"):
            logging.info("multimedia: sending redirect request back to Smarthistory for %s" % self.request.path)
            self.redirect( SMARTHISTORY_URL + str(self.request.path), True )
            return                  
 
        data, response_headers, blob_key=self.load_resource()

        if response_headers.has_key("Location"):
            logging.info("sending redirect request back to Smarthistory for %s" % self.request.path)
            self.redirect( response_headers["Location"], True )
            return
        
        #might need to convert all dictionary keys to lower case
        #check to see if we need to return 304 - might need to add handling of If-Modified-Since, in case If-None-Match is not sent 
        if self.request.headers.has_key("If-None-Match") and response_headers.has_key("etag") and self.request.headers["If-None-Match"] == response_headers["etag"]:
            logging.info("sending 304 from within the application");
            
            content_type = response_headers.get("content-type")[:response_headers.get("content-type").find("/")]
            
            if content_type in ("image", "audio", "video"):
                self.response.headers["Cache-Control"] = "public, max-age=" + str(SMARTHISTORY_IMAGE_CACHE_EXPIRATION) + ";"
            else:
                self.response.headers["Cache-Control"] = "public, max-age=" + str(SMARTHISTORY_CACHE_EXPIRATION_TIME) + ";"
            
            self.response.set_status(304)
            return

        for h in response_headers:
            self.response.headers[h] = response_headers[h]

        if blob_key:
            logging.info("resending blob with key=" + str(blob_key))
            self.send_blob(blob_key)
            return
 
        self.response.out.write(data)
        return 
  		
    def post(self):
        arguments = self.request.arguments()
        
        post_data = dict( (a, self.request.get(a)) for a in arguments )

        try:
            response = urlfetch.fetch(url = SMARTHISTORY_URL + self.request.path, payload = urllib.urlencode(post_data) , method="POST", headers = self.request.headers, deadline=25)
            if response.status_code == 200:
                data=response.content
            else:
                raise SmartHistoryLoadException(response.status_code)     
        except Exception, e:
            raise SmartHistoryLoadException("Post attempt failed to SmartHsitory with :"+str(e))  
            return      

        self.response.out.write(data)   

    @staticmethod
    def clearCache():
        Setting.smarthistory_version(int(Setting.smarthistory_version()) + 1)  

    #load the resource from smart history's server and then cache it in the data store
    #if it is an image then cache it in the blob store and store the blobkey in the data store 
    @layer_cache.cache_with_key_fxn(
        lambda self: "smart_history_v%s_%s" % (Setting.smarthistory_version(), self.request.path_qs), 
        layer = layer_cache.Layers.Datastore, 
        expiration = SMARTHISTORY_CACHE_EXPIRATION_TIME, 
        persist_across_app_versions = True, 
        permanent_key_fxn = lambda self: "smart_history_permanent_%s" % (self.request.path_qs))
    def load_resource(self):
        path = self.request.path

        #img is in users browser cache - we don't want to cache a Not-Modified response otherwise people who don't have image in browser cache won't get it
        headers = dict((k, v) for (k, v) in self.request.headers.iteritems() if k not in ["If-Modified-Since", "If-None-Match", "Content-Length","Host"])

        logging.info("getting resource " + str(path) + " from "+SMARTHISTORY_URL);       
        try:
            response = urlfetch.fetch(url = SMARTHISTORY_URL + path, headers = headers, deadline=25)
        except urlfetch.ResponseTooLargeError, e:
            logging.info("got too large a file back, sending redirect headers")
            response_headers = {"Location": SMARTHISTORY_URL + str(self.request.path)}
            return ["", response_headers, None]    
        except Exception, e:
            raise SmartHistoryLoadException("Failed loading %s from SmartHistory with Exception: %s" % (path, e))


        if response.status_code != 200:
            self.attempt_counter += 1

            if response.status_code == 404:
                 raise SmartHistoryLoadException("After attempt #%i Failed loading %s from SmartHistory with response code:%i " % (self.attempt_counter, path, response.status_code))  
            elif self.attempt_counter < 3:
                 logging.info("After attempt #%i Failed loading %s from SmartHistory with response code:%i " % (self.attempt_counter, path, response.status_code))
                 return self.load_resource()
            else:
                raise SmartHistoryLoadException("After attempt #%i Failed loading %s from SmartHistory with response code:%i " % (self.attempt_counter, path, response.status_code))

        data = response.content

        #load the response headers into a dictionary as layer_cache was throwing an error caching an object of class mimetools.Message   
        response_headers = dict( (h, response.headers[h]) for h in response.headers if h not in ["Content-Length", "Host"]) 

        content_type = response.headers.get("content-type")[:response.headers.get("content-type").find("/")]

        #check to see if it is an image, audio, or video, if so store it in blobstore, set the appropriate headers and remove data from the output
        if content_type in ("image", "audio", "video"):

            # Create the file
            file_name = files.blobstore.create(mime_type=response.headers.get("content-type"),_blobinfo_uploaded_filename = SMARTHISTORY_URL+path)
  
            # Writing too large a chunk to the blobstore at a single time throws an error, so it should be done in pieces 
            pos = 0
            chunkSize = 65536
            with files.open(file_name, 'a') as f:
                while pos < len(data):
                    chunk = data[pos:pos+chunkSize]
                    pos += chunkSize
                    f.write(chunk)
    
            # Finalize the file. Do this before attempting to read it.
            files.finalize(file_name)
    
            # Get the file's blob key
            blob_key = files.blobstore.get_blob_key(file_name)
            
            response_headers["Cache-Control"]="public, max-age="+str(SMARTHISTORY_IMAGE_CACHE_EXPIRATION)+";"
            return ["", response_headers, blob_key]
            
        return [data, response_headers, None]
   
   
