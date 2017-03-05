"""
"""
from probe import Probe
import os.path
import re
import util


class Meta:
    """ Meta """
    max_size = (1024 * 1024 * 70)  # 70MB

    def __clean_music(self, path):
        # remove anything that isn't alphanumeric or a sparator
        path = re.sub(r"[^a-zA-Z0-9 ._-]", " ", path, re.I)
        # replace '.' and '_' separators with '-'
        path = re.sub(r"[._]", "-", path)
        # remove duplicate separators
        path = re.sub(r"-{2,}", "-", path)

        # if there are more than 3 separators, get rid of all of them
        if path.count('-') > 3:
            path = re.sub(r"-+", " ", path)

        # path = util.clean_string(path)
        # remove format tags
        format_tags = ['flac', 'ape', 'wav',
                       'mp3([@~](\d+)(k(bps|bits?)?)?)?',
                       'mp4([@~](\d+)(k(bps|bits?)?)?)?',
                       'aac([@~](\d+)(k(bps|bits?)?)?)?',
                       'vorbis([@~](\d+)(k(bps|bits?)?)?)?']
        path = util.listRegexDel(format_tags, path, re.I)
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

        # <track> | <artist> | <album> | <title>
        m1 = re.search(r"""^(?P<track>\d{1,2})
        \s*[-]?\s*
        (?P<artist>[^-]+)
        \s*[-]\s*
        (?P<album>[^-]+)
        \s*[-]\s*
        (?P<title>[^-]+)$""", path, re.X)

        # <artist> | <album> | <track> | <title>
        m2 = re.search(r"""^
        (?P<artist>[^-]+)
        \s*[-]\s*
        (?P<album>[^-]+)
        \s*[-]\s*
        (?P<track>\d{1,2})
        \s*[-]?\s*
        (?P<title>[^-]+)$""", path, re.X)

        # <track> | <title>
        m3 = re.search(r"^\s*(\d{1,2})(?:\s*-\s*|\s+)([^-]+)$", path)

        if m1 is not None:
            track = int(m1.group('track'))
            artist = util.clean_string(m1.group('artist'))
            album = util.clean_string(m1.group('album'))
            title = util.clean_string(m1.group('title'))
        elif m2 is not None:
            track = int(m2.group('track'))
            artist = util.clean_string(m2.group('artist'))
            album = util.clean_string(m2.group('album'))
            title = util.clean_string(m2.group('title'))
        elif m3 is not None:
            track = int(m3.group(1))
            title = m3.group(2)
        else:
            # attempt to extract a year
            m = re.search(r"((?:19|20)\d{2})", path)
            if m is not None:
                year = int(m.group(1))
                yearstart = m.start(1)
                yearend = m.end(1)

            # attempt to extract a track number
            m = re.search(r"(?:^|\D)(\d{1,2})\D", path)
            if m is not None:
                track = int(m.group(1))
                trackstart = m.start(1)
                trackend = m.end(1)

            if yearstart != -1:
                if yearstart > 2:
                    artist = util.clean_string(path[:yearstart-1])
                    m = re.search(r"^([^-]+)\s*-\s*([^-]+)$", artist)
                    if m is not None:
                        artist = util.clean_string(m.group(1))
                        album = util.clean_string(m.group(2))
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

        for p in reversed(no_ext_path.split('/')):
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
        self.__dict__['has_video'] = False
        self.__dict__['video_format'] = None
        probe = Probe(path)
        has_artist = False
        has_year = False
        if probe.format is not None:
            if 'tags' in probe.format:
                for k, v in probe.format['tags'].iteritems():
                    if not has_artist and re.search(r"^artist", k, re.I):
                        self.__dict__['artist'] = v
                    elif re.search(r"album_?artist", k, re.I):
                        self.__dict__['artist'] = v
                        has_artist = True
                    elif re.search(r"album", k, re.I):
                        self.__dict__['album'] = v
                    elif not has_year and re.search(r"^year|date$", k, re.I):
                        m = re.search(r"((?:19|20)\d{2})", v, re.I)
                        if m is not None:
                            self.__dict__['year'] = int(m.group(1))
                            has_year = True
                    elif re.search(r"^track$", k, re.I):
                        m = re.search(r"(\d+)", v)
                        if m is not None:
                            self.__dict__['track'] = int(m.group(1))
                    elif re.search(r"title", k, re.I):
                            self.__dict__['title'] = v

            ext = probe.extension()
            if ext is not None:
                self.__dict__['extension'] = ext

            if probe.streams is not None:
                self.__dict__['has_video'] = probe.has_video()
                self.__dict__['has_audio'] = probe.has_audio()

    def __modified_path(self, path, base_dir):
        if base_dir is not None:
            path = path.replace(base_dir, '')
        if path[0] == '/':
            path = path[1:]
        return path

    def __process(self, path, base_dir,
                  process_path=True, process_probe=True):

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

        # the other half is determined by the duration and format of the media
        c_media = util.Confidence()
        c_media.add(not self.has_video)
        c_media.add(self.size < Meta.max_size)

        return (c_meta.rate() * 0.3) + (c_media.rate() * 0.7)

    def __build_file(self):
        out = ''
        if self.track != -1:
            out = '{0:0=2}.'.format(self.track)

        if self.title is not None:
            out += ' {0}'.format(self.title)

        out += '.{0}'.format(self.extension)
        return util.sanitize_path(out)

    def __build_dir(self):
        out = util.sanitize_path(self.artist)
        if self.album is not None:
            out += '/{0}'.format(util.sanitize_path(self.album))
            if self.year != -1:
                out += ' ({0})'.format(self.year)
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
        self.__process(path, base_dir)

    def __str__(self):
        return self.__build_file()


if __name__ == "__main__":
    import sys
    path = sys.argv[1]
    base_dir = None
    if len(sys.argv) > 2:
        base_dir = sys.argv[2]
    music = Meta(path, base_dir)
    if music is not None:
        print 'Input = "{0}" (confidence: {1})'.format(path, music.confidence)
        print 'Output = "{0}/{1}"'.format(music.dir, music.file)
