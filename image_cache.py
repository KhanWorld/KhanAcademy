from __future__ import with_statement
from google.appengine.api import files, urlfetch
from google.appengine.ext.webapp import blobstore_handlers
import urllib
import logging

import webapp2

import layer_cache

CACHE_EXPIRATION = 60 * 60 * 24 * 60 # Cache for two months

class ImageCache(webapp2.RequestHandler, blobstore_handlers.BlobstoreDownloadHandler):
    """ ImageCache is a little utility used to cache images at other URLs
    in our blobstore with our own aggressive caching headers for client-side perf.

    Example: youtube_url = ImageCache.url_for("http://youtube.com/some/thumbnail")
    """

    @staticmethod
    def url_for(source_url, fallback_url = None):
        if fallback_url:
            return "/image_cache/%s?fallback=%s" % (urllib.quote(source_url), urllib.quote(fallback_url))
        else:
            return "/image_cache/%s" % urllib.quote(source_url)

    def get(self, source_url):

        blob_key = self.image_cache_blob_key(source_url)

        fallback_url = self.request.get("fallback")
        if fallback_url and not blob_key:
            blob_key = self.image_cache_blob_key(fallback_url)

        if not blob_key:
            # If we failed to grab something outta the blob store, just try a redirect.
            # ...but log the error, cuz we don't like this.
            logging.error("Failed to load image cache for source url, redirecting: %s" % source_url)
            self.redirect(source_url)
            return

        self.response.cache_control.max_age = CACHE_EXPIRATION
        self.response.cache_control.no_cache = None
        self.response.cache_control.public = True

        self.send_blob(blob_key)

    @layer_cache.cache_with_key_fxn(
            lambda self, source_url: "image_cache:%s" % source_url, 
            layer=layer_cache.Layers.Datastore,
            persist_across_app_versions=True)
    def image_cache_blob_key(self, source_url):

        tries = 0
        max_tries = 3

        while tries < max_tries:

            response = None

            try:
                response = urlfetch.fetch(url = source_url, headers = self.request.headers, deadline=10)
            except Exception, e:
                logging.info("Failed to load image cache source url %s due to %s" % (source_url, e))

            if response and response.status_code == 200:
                return blob_key_for_data(response.headers.get("Content-Type"), response.content)
            else:
                tries += 1

        return layer_cache.UncachedResult(None)

def blob_key_for_data(content_type, data):

    if "image" not in content_type:
        raise Exception("Image cache is currently only used for image content types.")

    # Create the file
    file_name = files.blobstore.create(mime_type = content_type)

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

    return files.blobstore.get_blob_key(file_name)
