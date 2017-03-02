
"""
"""
from info import Info
import os.path
from pathparse import MoviePathParser, MusicPathParser, ShowPathParser
import re
import util


class MusicParser:
    """ MusicParser """
    max_size = (1024 * 1024 * 70)

    def __parse_meta(self, mi):
        has_artist = False
        has_year = False
        if mi.format is not None and 'tags' in mi.format:
            for k, v in mi.format['tags'].iteritems():
                if not has_artist and re.search(r"^artist", k, re.I):
                    self.__artist = v
                elif re.search(r"album_?artist", k, re.I):
                    self.__artist = v
                    has_artist = True
                elif re.search(r"album", k, re.I):
                    self.__album = v
                elif not has_year and re.search(r"^year|date$", k, re.I):
                    m = re.search(r"((?:19|20)\d{2})", v, re.I)
                    if m is not None:
                        self.__year = int(m.group(1))
                        has_year = True
                elif re.search(r"track", k, re.I):
                    m = re.search(r"(\d+)", v)
                    if m is not None:
                        self.__track = int(m.group(1))
                elif re.search(r"title", k, re.I):
                        self.__title = v

    def __parse_path(self, path):
        pp = MusicPathParser(path)
        self.__artist = pp.artist()
        self.__album = pp.album()
        self.__year = pp.year()
        self.__track = pp.track()
        self.__title = pp.title()
        self.__c_path = pp.confidence()

    def __parse(self, path, mi):
        # media information
        self.__has_audio = mi.has_audio()
        self.__has_video = mi.has_video()
        self.__size = os.path.getsize(path)
        if self.__has_video:
            s = mi.best_video_stream()
            # mjpeg doesn't count
            if s['codec_name'] == 'mjpeg':
                self.__has_video = False

        # extract meta from path parsing first
        self.__parse_path(path)
        # extract meta embedded in media
        self.__parse_meta(mi)

    def __init__(self, path, minfo):
        self.__parse(path, minfo)

    def __str__(self):
        out = ''
        if self.__artist is not None:
            out = '"{0}"'.format(self.__artist)
            if self.__year != -1:
                out += ' [{0}]'.format(self.__year)

            if self.__album is not None:
                out += ' "{0}"'.format(self.__album)

            if self.__track != -1:
                out += ' {0:0=2}.'.format(self.__track)

            if self.__title is not None:
                out += ' "{0}"'.format(self.__title)

        return out

    def album(self):
        return self.__album

    def artist(self):
        return self.__artist

    def confidence(self):
        # smaller than half the confidence comes from the path
        # because it's harder to determine the details from
        # the music filename
        c_path = self.__c_path

        # if this doesn't have audio, force to 0
        if not self.__has_audio:
            return 0.0

        c = util.Confidence()
        # larger than half the confidence comes from
        # the media itself
        c.add(not self.__has_video)
        c.add(self.__size < MusicParser.max_size)
        c_media = c.rate()

        return (c_path * 0.3) + (c_media * 0.7)

    def title(self):
        return self.__title

    def track(self):
        return self.__track

    def type(self):
        return 'music'

    def year(self):
        return self.__year


class ShowParser:
    """ ShowParser """
    max_duration = float(60 * 60)  # 1hr
    min_size = (1024 * 1024 * 20)  # 20MB

    def __parse_path(self, path):
        pp = ShowPathParser(path)
        self.__show_name = pp.show_name()
        self.__season = pp.season()
        self.__episode, self.__episode_last = pp.episodes()
        self.__episode_name = pp.episode_name()
        self.__c_path = pp.confidence()

    def __parse(self, path, mi):
        self.__duration = 0.0
        self.__has_video = False
        self.__size = os.path.getsize(path)

        self.__parse_path(path)

        if mi.format is not None:
            self.__duration = float(mi.format["duration"])
            self.__has_video = mi.has_video()

    def __init__(self, path, minfo):
        self.__parse(path, minfo)

    def __str__(self):
        out = ''
        if self.__show_name is not None:
            out = '"{0}"'.format(self.__show_name)
            if self.__episode != -1:
                s = self.__season
                if s == -1:
                    s = 1
                out += ' - Season: {0:0=2},'.format(s)
                if self.__episode_last != self.__episode:
                    out += ' Episodes: {0:0=2}-{1:0=2}'.format(
                        self.__episode, self.__episode_last)
                else:
                    out += ' Episode: {0:0=2}'.format(self.__episode)

            if self.__episode_name is not None:
                out += ' - "{0}"'.format(self.__episode_name)

        return out

    def type(self):
        return 'show'

    def show_name(self):
        return self.__show_name

    def season(self):
        return self.__season

    def episodes(self):
        return self.__episode, self.__episode_last

    def episode_name(self):
        return self.__episode_name

    def confidence(self):
        # half the confidence is determined by the path parsing
        c_path = self.__c_path

        c = util.Confidence()
        # the other half is determined by the duration and format of the media
        c.add(self.__duration < ShowParser.max_duration)
        c.add(self.__has_video)
        c.add(self.__size >= ShowParser.min_size)
        c_media = c.rate()

        return (c_path * 0.5) + (c_media * 0.5)


class MovieParser:
    """ MovieParser """
    min_duration = float(45 * 60)   # 45mins
    min_size = (1024 * 1024 * 200)  # 200MB

    def __parse_meta(self, mi):
        if mi.format is not None and 'tags' in mi.format:
            for k, v in mi.format['tags'].iteritems():
                if re.search(r"^title$", k, re.I):
                    pp = MoviePathParser(v)
                    self.__title = pp.title()
                    if self.__year == -1:
                        self.__year = pp.year()
                    if self.__part == -1:
                        self.__part = pp.part()
                elif re.search(r"^(date|year)$", k, re.I):
                    m = re.search(r"((?:19|20)\d{2})", v)
                    if m is not None:
                        self.__year = int(m.group(1))

    def __parse_path(self, path):
        pp = MoviePathParser(path)
        self.__title = pp.title()
        self.__year = pp.year()
        self.__part = pp.part()
        self.__c_path = pp.confidence()

    def __parse(self, path, mi):
        self.__duration = 0.0
        self.__has_video = False
        self.__size = os.path.getsize(path)
        if mi.format is not None:
            self.__duration = float(mi.format["duration"])
        if mi.streams is not None:
            self.__has_video = mi.has_video()

        # extract meta data from the path
        self.__parse_path(path)

        # extract meta data embedded in the media
        self.__parse_meta(mi)

    def __init__(self, path, minfo):
        self.__parse(path, minfo)

    def __str__(self):
        out = ''
        if self.__title is not None:
            out = self.__title
            if self.__year != -1:
                out += ' ({0})'.format(self.__year)

            if self.__part != -1:
                out += ' part {0}'.format(self.__part)
        return out

    def title(self):
        return self.__title

    def year(self):
        return self.__year

    def part(self):
        return self.__part

    def type(self):
        return 'movie'

    def confidence(self):
        # half the confidence is determined by the path parsing
        c_path = self.__c_path

        c = util.Confidence()
        # the other half is determined by the duration and format of the media
        c.add(self.__duration >= MovieParser.min_duration)
        c.add(self.__has_video)
        c.add(self.__size >= MovieParser.min_size)

        c_media = c.rate()

        return (c_path * 0.5) + (c_media * 0.5)


def determine_parser(path, min_confidence=0.0):
    """ determine_parser """

    parser = None
    confidence = 0.0

    if os.path.isfile(path):
        mi = Info(path)
        parsers = [
            MusicParser(path, mi),
            ShowParser(path, mi),
            MovieParser(path, mi)
        ]

        for p in parsers:
            c = p.confidence()
            if c > min_confidence and c > confidence:
                parser = p
                confidence = c

    return parser, confidence


if __name__ == "__main__":
    import sys
    path = sys.argv[1]
    parser, c = determine_parser(path, 0.6)
    if parser is not None:
        print 'Input = {0}'.format(path)
        print 'Media type = {0} (confidence: {1})'.format(parser.type(), c)
        print parser
    else:
        print "Could not find a suitable parser"
