from google.appengine.ext import db
from google.appengine.tools import bulkloader


class Playlist(db.Model):
	youtube_id = db.StringProperty()
	url = db.StringProperty()
	title = db.StringProperty()
	description = db.TextProperty()
	
class PlaylistExporter(bulkloader.Exporter):
    def __init__(self):
        bulkloader.Exporter.__init__(self, 'Playlist',
                                     [('youtube_id', str, None),
                                      ('url', str, None),
                                      ('title', str, None),
                                      ('description', str, None)
                                     ])

exporters = [PlaylistExporter]
