# -*- coding: utf-8 -*-
"""
 This module will extract meta information for music from a given path.
 It utilizes parsing the actual path and probing the file with a media probe
 in order to accumulate the metadata.
"""

import musicbrainzngs
import os.path
from probe import Probe
import re
import util


class File:
    """
    Encapsulates a music file containing various metadata
    about it including format and artist/song information.
    """
    max_size = (1024 * 1024 * 70)  # 70MB

    def __clean_music(self, path):
        # remove anything that isn't alphanumeric or a sparator
        path = re.sub(ur"[^\wÀ-ý .-]", " ", path, re.I | re.UNICODE)
        # replace '.' and '_' separators with '-'
        path = re.sub(ur"[._]", "-", path)
        # remove duplicate separators
        path = re.sub(ur"-{2,}", "-", path)

        # if there are more than 3 separators, get rid of all of them
        if path.count('-') > 3:
            path = re.sub(ur"-+", " ", path)

        # path = util.clean_string(path)
        # remove format tags
        format_tags = ['flac', 'ape', 'wav',
                       'mp3([@~](\d+)(k(bps|bits?)?)?)?',
                       'mp4([@~](\d+)(k(bps|bits?)?)?)?',
                       'aac([@~](\d+)(k(bps|bits?)?)?)?',
                       'vorbis([@~](\d+)(k(bps|bits?)?)?)?']
        path = util.list_re_del(format_tags, path, re.I)
        return path.strip()

    def __parse_path(self, path):
        artist = None
        year = -1
        yearstart = -1
        yearend = -1
        album = None
        track = -1
        trackstart = -1
        trackend = -1
        title = None

        path = self.__clean_music(path)

        patterns = [
            # <track> | <artist> | <album> | <title>
            ur"""^(?P<track>\d{1,2})
            \s*[-]?\s*
            (?P<artist>[^-]+)
            \s*[-]\s*
            (?P<album>[^-]+)
            \s*[-]\s*
            (?P<title>[^-]+)$""",
            # <artist> | <album> | <track> | <title>
            ur"""^
            (?P<artist>[^-]+)
            \s*[-]\s*
            (?P<album>[^-]+)
            \s*[-]\s*
            (?P<track>\d{1,2})
            \s*[-]?\s*
            (?P<title>[^-]+)$""",

            # <track> | <title>
            ur"^\s*(?P<track>\d{1,2})(?:\s*-\s*|\s+)(?P<title>[^-]+)$"
        ]

        m = util.list_re_search(patterns, path, re.X)
        if m is not None:
            gd = m.groupdict()
            if 'track' in gd:
                track = int(gd['track'])
            if 'artist' in gd:
                artist = util.clean_string(gd['artist'])
            if 'album' in gd:
                album = util.clean_string(gd['album'])
            if 'title' in gd:
                title = util.clean_string(gd['title'])
        else:
            # attempt to extract a year
            m = re.search(ur"(?P<year>(?:19|20)\d{2})", path)
            if m is not None:
                year = int(m.group('year'))
                yearstart = m.start('year')
                yearend = m.end('year')

            # attempt to extract a track number
            m = re.search(ur"(?:^|\D)(?P<track>\d{1,2})\D", path)
            if m is not None:
                track = int(m.group('track'))
                trackstart = m.start('track')
                trackend = m.end('track')

            if yearstart != -1:
                if yearstart > 2:
                    artist = util.clean_string(path[:yearstart-1])
                    m = re.search(ur"^(?P<artist>[^-]+)\s*-\s*(?P<album>[^-]+)$", artist)
                    if m is not None:
                        artist = util.clean_string(m.group('artist'))
                        album = util.clean_string(m.group('album'))
                else:
                    album = util.clean_string(path[yearend:])

            if trackstart != -1:
                title = util.clean_string(path[trackend:])
                if trackstart > 1:
                    if yearstart != -1 and yearstart < trackstart:
                        album = util.clean_string(path[yearend:trackstart-1])
                    else:
                        album = util.clean_string(path[:trackstart-1])

            if album is None:
                if yearstart != -1:
                    album = util.clean_string(path[yearend:])
                else:
                    artist = util.clean_string(path)

        # hack for bad matches
        if artist is not None and len(artist) < 2:
            artist = None

        return artist, year, album, track, title

    def __process_path(self, path):
        artist = None
        year = -1
        album = None
        track = -1
        title = None

        no_ext_path, ext_with_dot = os.path.splitext(path)
        ext = ext_with_dot[1:].lower()

        for p in reversed(no_ext_path.split(os.sep)):
            if (artist is not None and year != -1 and
                    track != -1 and title is not None):
                break

            a, y, b, t, s = self.__parse_path(p)
            if artist is None and a is not None:
                artist = a
            if year == -1 and y != -1:
                year = y
            if album is None and b is not None:
                album = b
            if track == -1 and t != -1:
                track = t
            if title is None and s is not None:
                title = s

        self.__dict__['artist'] = artist
        self.__dict__['year'] = year
        self.__dict__['album'] = album
        self.__dict__['track'] = track
        self.__dict__['title'] = title
        self.__dict__['extension'] = ext

    def __process_probe(self, path):
        """ Process a media probe for meta information """
        probe = Probe(path)
        self.__dict__['probe'] = probe
        self.__dict__['has_audio'] = False
        self.__dict__['has_video'] = False
        self.__dict__['video_format'] = None
        self.__dict__['duration'] = 0.0
        has_artist = False
        has_year = False
        if probe.format is not None:
            if 'duration' in probe.format:
                self.__dict__['duration'] = float(probe.format['duration'])
            if 'tags' in probe.format:
                for k, v in probe.format['tags'].iteritems():
                    if not has_artist and re.search(ur"^artist", k, re.I):
                        self.__dict__['artist'] = self.__clean_music(v)
                    elif re.search(ur"album_?artist", k, re.I):
                        self.__dict__['artist'] = self.__clean_music(v)
                        has_artist = True
                    elif re.search(ur"album", k, re.I):
                        self.__dict__['album'] = self.__clean_music(v)
                    elif not has_year and re.search(ur"^year|date$", k, re.I):
                        m = re.search(ur"((?:19|20)\d{2})", v, re.I)
                        if m is not None:
                            self.__dict__['year'] = int(m.group(1))
                            has_year = True
                    elif re.search(ur"^track$", k, re.I):
                        m = re.search(ur"(\d+)", v)
                        if m is not None:
                            self.__dict__['track'] = int(m.group(1))
                    elif re.search(ur"title", k, re.I):
                            self.__dict__['title'] = self.__clean_music(v)

            ext = probe.extension()
            if ext is not None:
                self.__dict__['extension'] = ext

            if probe.streams is not None:
                self.__dict__['has_video'] = probe.has_video()
                self.__dict__['has_audio'] = probe.has_audio()

    def __modified_path(self, path, base_dir):
        if base_dir is not None:
            path = path.replace(base_dir, '')
        if path[0] == os.sep:
            path = path[1:]
        return path

    def __process(self, path, base_dir,
                  process_path=True, process_probe=True):
        """
        Assumes path and base_dir are unicode strings
        and exist
        """

        self.__dict__['artist_id'] = None
        self.__dict__['album_id'] = None
        self.__dict__['title_id'] = None

        modpath = self.__modified_path(path, base_dir)
        self.__dict__['modpath'] = modpath
        self.__dict__['path'] = path
        self.__dict__['size'] = os.path.getsize(path)

        if process_path:
            # extract meta data from the path
            self.__process_path(modpath)
        self.__dict__['processed_path'] = process_path

        if process_probe:
            # extract meta data embedded in the media
            self.__process_probe(path)
        self.__dict__['processed_probe'] = process_probe

    def __confidence(self):
        # half the confidence is determined by the meta
        c_meta = util.Confidence()
        c_meta.add(self.artist is not None)
        c_meta.add(self.album is not None)
        # c_meta.add(self.year != -1)
        c_meta.add(self.track != -1)
        # c.add(self.title is not None)

        # if this doesn't have audio, force to 0
        if not self.has_audio:
            return 0.0

        # the other half is determined by format of the media
        c_media = util.Confidence()
        c_media.add(not self.has_video)
        c_media.add(self.size < File.max_size)

        return (c_meta.rate() * 0.3) + (c_media.rate() * 0.7)

    def __build_file(self):
        out = u''
        if self.track != -1:
            out = u'{0:0=2}.'.format(self.track)

        if self.title is not None:
            out += u' {0}'.format(util.sanitize_path(self.title))

        out += u'.{0}'.format(self.extension)
        return out

    def __build_dir(self):
        out = util.sanitize_path(self.artist)
        if self.album is not None:
            out += u'/{0}'.format(util.sanitize_path(self.album))
            if self.year != -1:
                out += u' ({0})'.format(self.year)
        return out

    def __getattr__(self, attr):
        if attr == 'file':
            return self.__build_file()
        elif attr == 'dir':
            return self.__build_dir()
        elif attr == 'type':
            return 'music'
        elif attr == 'confidence':
            return self.__confidence()
        elif attr in self.__dict__:
            return self.__dict__[attr]
        return None

    def __setattr__(self, attr, val):
        if attr in self.__dict__:
            self.__dict__[attr] = val

    def __init__(self, path, base_dir=None):
        if not os.path.isfile(path):
            raise ValueError(u'Path "{0}" is not a valid file'.format(path))
            return

        if base_dir is not None and not os.path.isdir(base_dir):
            raise ValueError(
                u'Base directory "{0}" is not a valid directory'.format(
                    base_dir))
            return

        self.__process(path, base_dir)

    def __str__(self):
        return self.__build_file()


class Search:
    """
    Simplified wrapper to the MusicBrainz online database
    """
    def __init__(self):
        musicbrainzngs.set_useragent(
            "PlexPy - Media Manager", "0.1", "drachul@gmail.com")
        self._cache = {}

    def __artist(self, artist):
        results = musicbrainzngs.search_artists(artist=artist, limit=5)

        if 'artist-list' not in results:
            return []

        results = sorted(
            results['artist-list'],
            key=lambda r: -int(r['ext:score']))

        return results

    def track(self, artist, album, track):
        artist_key = util.simplify_string(artist)
        album_key = util.simplify_string(album)

        _release = None
        _artist = None
        _year = -1

        if artist_key in self._cache:
            _artist = self._cache[artist_key]['info']
        else:
            results = self.__artist(artist)
            if len(results) == 0:
                return None
            _artist = results[0]
            self._cache[artist_key] = {
                'info': _artist,
                'releases': {}
            }

        if album_key in self._cache[artist_key]['releases']:
            _release = self._cache[artist_key]['releases'][album_key]
        else:
            results = musicbrainzngs.search_releases(
                artist=artist,
                release=album,
                limit=1)
            if 'release-list' not in results:
                return None
            if len(results['release-list']) == 0:
                return None
            result = musicbrainzngs.get_release_by_id(
                results['release-list'][0]['id'], includes=['recordings'])
            if 'release' not in result:
                return None
            _release = result['release']
            if 'date' in _release:
                m = re.search(ur"((?:19|20)\d{2})", _release['date'])
                if m is not None:
                    _year = int(m.group(1))
            self._cache[artist_key]['releases'][album_key] = _release

        if _release['medium-count'] == 0:
            return None

        _medium = None
        for m in _release['medium-list']:
            if m['format'] == 'CD':
                _medium = m
                break

        if track < 1 or track > _medium['track-count']:
            return None

        _track = _medium['track-list'][track - 1]

        return {
            'artist': _artist['name'],
            'artist-id': _artist['id'],
            'album': _release['title'],
            'album-id': _release['id'],
            'year': _year,
            'title': _track['recording']['title'],
            'title-id': _track['recording']['id']
        }

    def track_from_file(self, music):
        track = self.track(music.artist, music.album, music.track)

        if track is not None:
            music.artist = track['artist']
            music.artist_id = track['artist-id']
            music.album = track['album']
            music.album_id = track['album-id']
            if track['year'] != -1:
                music.year = track['year']
            music.title = track['title']
            music.title_id = track['title-id']

        return music


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Media Music Module')
    parser.add_argument('--basedir', '-b', default=None, metavar='DIR',
                        help='The base directory to use for path filtering')
    parser.add_argument('--search', '-s', action='store_true',
                        help='Flag to enable MusicBrainz processing')
    parser.add_argument('input', help='The input file to process')
    args = parser.parse_args()

    args.input = args.input.decode('utf-8')
    if args.basedir is not None:
        args.basedir = args.basedir.decode('utf-8')

    music = File(args.input, args.basedir)
    print u'Input = "{0}" (confidence:{1})'.format(args.input, music.confidence)
    if args.search:
        music = Search().track_from_file(music)

    if music is not None:
        print u'Output = "{0}/{1}"'.format(music.dir, music.file)
    else:
        print u'Something went wrong...'
