import logging
import tornado.web

logger = logging.getLogger(__name__)


class AddToPlaylistRequestHandler(tornado.web.RequestHandler):

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

    def get(self):
        playlist_uri = self.get_arguments("playlist_uri")
        track_uri = self.get_arguments("track_uri")
        logger.info(f"PL {playlist_uri}")
        logger.info(f"TR {track_uri}")
        playlist_id = playlist_uri[0].split(":")[-1]
        track_ids = [uri.split(":")[-1] for uri in  track_uri]

        upstream_playlist = self.backend.session.playlist(playlist_id)
        res = upstream_playlist.add(track_ids)
        self.backend.playlists.refresh(playlist_uri)
        self.write(
            f'Added {res}'
        )


def api_extra_factory(config, core):
    return [
        ('/add_to_playlist', AddToPlaylistRequestHandler, {'config': config, 'core': core})
    ]
