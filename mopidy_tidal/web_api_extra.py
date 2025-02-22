import logging
import tornado.web

logger = logging.getLogger(__name__)

class TidalRequestHandler(tornado.web.RequestHandler):

    def set_default_headers(self):
        # TODO: only allow localhost
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    def initialize(self, config, core):
        from .backend import TidalBackend
        self.config = config
        self.core = core
        self.backend = TidalBackend(config, None)
        self.backend.on_start()

class AddToPlaylistRequestHandler(TidalRequestHandler):

    def get(self):
        playlist_uri = self.get_arguments("playlist_uri")
        track_uri = self.get_arguments("track_uri")
        if len(playlist_uri) == 0 or len(track_uri) == 0:
            self.set_status(400)
            self.finish("Error: needs playlist_uri and track_uri parameters")

        playlist_id = playlist_uri[0].split(":")[-1]
        track_ids = [uri.split(":")[-1] for uri in  track_uri]

        upstream_playlist = self.backend.session.playlist(playlist_id)
        res = upstream_playlist.add(track_ids)
        logger.info(self.backend.playlists._current_tidal_playlists)
        self.backend.playlists.refresh(playlist_uri)
        self.finish(
            f'Added {res} to playlist {playlist_id}'
        )


def api_extra_factory(config, core):
    return [
        ('/add_to_playlist', AddToPlaylistRequestHandler, {'config': config, 'core': core})
    ]
