from __future__ import unicode_literals

import datetime
import logging
import operator
from typing import Union

from tidalapi.models import Playlist as TidalPlaylist

from mopidy import backend
from mopidy.models import Playlist as MopidyPlaylist, Ref

from mopidy_tidal import full_models_mappers
from mopidy_tidal.lru_cache import LruCache


logger = logging.getLogger(__name__)


def _to_timestamp(dt):
    if not dt:
        return 0
    if isinstance(dt, str):
        dt = datetime.datetime.fromisoformat(dt)
    if isinstance(dt, datetime.datetime):
        dt = dt.timestamp()
    return int(dt)


class PlaylistCache(LruCache):
    def __getitem__(
            self, key: Union[str, TidalPlaylist], *args, **kwargs
    ) -> MopidyPlaylist:
        uri = key.id if isinstance(key, TidalPlaylist) else key
        uri = (
            f'tidal:playlist:{uri}'
            if not uri.startswith('tidal:playlist:')
            else uri
        )

        playlist = super().__getitem__(uri, *args, **kwargs)
        if (
            playlist and isinstance(key, TidalPlaylist) and
            _to_timestamp(key.last_updated) >
            _to_timestamp(playlist.last_modified)
        ):
            # The playlist has been updated since last time:
            # we should refresh the associated cache entry
            logger.info('The playlist "%s" has been updated: refresh forced', key.name)
            raise KeyError(uri)

        return playlist


class TidalPlaylistsProvider(backend.PlaylistsProvider):

    def __init__(self, *args, **kwargs):
        super(TidalPlaylistsProvider, self).__init__(*args, **kwargs)
        self._playlists = PlaylistCache()

    def as_list(self):
        if not self._playlists:
            self.refresh()

        logger.debug("Listing TIDAL playlists..")
        refs = [
            Ref.playlist(uri=pl.uri, name=pl.name)
            for pl in self._playlists.values()]
        return sorted(refs, key=operator.attrgetter('name'))

    def get_items(self, uri):
        if not self._playlists:
            self.refresh()

        playlist = self._playlists.get(uri)
        if playlist is None:
            return []
        return [Ref.track(uri=t.uri, name=t.name) for t in playlist.tracks]

    def create(self, name):
        pass  # TODO

    def delete(self, uri):
        pass  # TODO

    def lookup(self, uri):
        return self._playlists.get(uri)

    def refresh(self):
        logger.info("Refreshing TIDAL playlists..")
        session = self.backend._session

        plists = session.user.favorites.playlists()
        for pl in plists:
            pl.name = "* " + pl.name
        # Append favourites to end to keep the tagged name if there are
        # duplicates
        plists = session.user.playlists() + plists

        for pl in plists:
            uri = "tidal:playlist:" + pl.id
            # Cache hit case
            if pl in self._playlists:
                continue

            # Cache miss case
            pl_tracks = session.get_playlist_tracks(pl.id)
            tracks = full_models_mappers.create_mopidy_tracks(pl_tracks)
            self._playlists[uri] = MopidyPlaylist(
                uri=uri,
                name=pl.name,
                tracks=tracks,
                last_modified=_to_timestamp(pl.last_updated),
            )

        backend.BackendListener.send('playlists_loaded')
        logger.info("TIDAL playlists refreshed")

    def save(self, playlist):
        pass  # TODO
