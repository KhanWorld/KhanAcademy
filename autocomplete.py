import layer_cache
from models import Video, Playlist
from templatefilters import slugify

CACHE_EXPIRATION_SECONDS = 60 * 60 * 24 * 3 # Expires after three days

@layer_cache.cache(expiration=CACHE_EXPIRATION_SECONDS)
def video_title_dicts():
    return map(lambda video: {
        "title": video.title,
        "key": str(video.key()),
        "ka_url": video.relative_url, # remove once js clients update
        "url": video.relative_url
    }, [v for v in Video.get_all_live() if v is not None])

@layer_cache.cache(expiration=CACHE_EXPIRATION_SECONDS)
def playlist_title_dicts():
    return map(lambda playlist: {
        "title": playlist.title,
        "key": str(playlist.key()),
        "ka_url": playlist.relative_url, # remove once js clients update
        "url": playlist.relative_url
    }, Playlist.all())
