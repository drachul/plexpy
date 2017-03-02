"""
"""
from datetime import date
import os
import os.path
import re
import util


class MusicPathParser:
    """ MusicPathParser """

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

    def __parse_music(self, path):
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

    def __parse(self, path):
        artist = None
        year = -1
        album = None
        track = -1
        title = None

        no_ext_path, ext_with_dot = os.path.splitext(path)
        # ext = ext_with_dot[1:].lower()

        for p in reversed(no_ext_path.split('/')):
            if (artist is not None and year != -1 and
                    track != -1 and title is not None):
                break

            a, y, b, t, s = self.__parse_music(p)
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

        self.__artist = artist
        self.__year = year
        self.__album = album
        self.__track = track
        self.__title = title

    def __init__(self, path):
        self.__parse(path)

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

    def artist(self):
        return self.__artist

    def album(self):
        return self.__album

    def year(self):
        return self.__year

    def track(self):
        return self.__track

    def title(self):
        return self.__title

    def confidence(self):
        c = util.Confidence()

        c.add(self.__artist is not None)
        c.add(self.__year != -1)
        c.add(self.__track != -1)
        c.add(self.__title is not None)

        return c.rate()


class MoviePathParser:
    """ MoviePathParser """

    def __clean_movie(self, path):
        path = re.sub(r"(part|cd|dvd|disc)\s*\d{1,2}", "", path)
        return util.clean_string(path)

    def __parse_movie(self, path):
        title = None
        year = -1
        yearpos = -1
        part = -1
        partpos = -1

        path = util.clean_media(path)

        # extract the year if available (scan backwards)
        ym = []
        for m in re.finditer(r"((?:19|20)\d{2})", path):
            y = int(m.group())
            if y <= date.today().year:
                ym.append([y, m.start()])

        if len(ym) > 0:
            year = ym[-1][0]
            yearpos = ym[-1][1]

        # extract the part if available
        m = re.search(r"""(?:
                        p(?:ar)?t|
                        cd|
                        disc
        )\s*(\d{1,2})[^\d]""", path, flags=re.I | re.X)
        if m is not None:
            part = int(m.group(1))
            partpos = m.start(1)

        pos = yearpos

        if partpos != -1 and partpos < yearpos:
            pos = partpos

        if pos > 1:
            title = util.clean_string(path[:pos-1])
        else:
            title = path

        return title, year, part

    def __parse(self, path):
        title = None
        year = -1
        part = -1

        no_ext_path, ext_with_dot = os.path.splitext(path)
        ext = ext_with_dot[1:].lower()

        for p in reversed(no_ext_path.split('/')):
            # if we have all the info we want, break out of the loop
            if title is not None and year != -1:
                break

            t, y, p = self.__parse_movie(p)

            if title is None and t is not None:
                title = t

            if year == -1 and y != -1:
                year = y

            if part == -1 and p != -1:
                part = p

        self.__title = title
        self.__year = year
        self.__part = part
        self.__ext = ext

    def __init__(self, path):
        self.__parse(path)

    def __str__(self):
        out = ''
        if self.__title is not None:
            out = self.__title
            if self.__year != -1:
                out += ' ({0})'.format(self.__year)

            if self.__part != -1:
                out += ' part {0}'.format(self.__part)
        return out

    def type(self):
        return 'movie'

    def title(self):
        return self.__title

    def year(self):
        return self.__year

    def part(self):
        return self.__part

    def confidence(self):
        c = util.Confidence()

        c.add(self.__title is not None)
        c.add(self.__year != -1)

        return c.rate()


class ShowPathParser:
    """ ShowPathParser """

    def __parse_show(self, path):
        show_name = None
        season = -1
        episode = -1
        episode_last = -1
        episode_name = None

        p = util.clean_media(path)

        # s??e?? type episodes
        m1 = re.search(
            r"s(\d{1,2})[\s\._]*((?:(?:\s*e|-e?|\+e?|&e?)\d{1,3})+)", p, re.I)
        # SSxEE type episodes
        m2 = re.search(r"(\d{1,2})((?:\s*(?:x|-)\s*\d{1,3})+)", p, re.I)
        # Season by itself
        m3 = re.search(r"s(?:eason)?\W?(\d{1,2})", p, re.I)
        # Episode by itself (start of name)
        m4 = re.search(r"^\s*(?:p(?:ar)?t)?\s*(\d{1,3})", p, re.I)
        # Episode by itself - miniseries (X of Y)
        m5 = re.search(r"(\d{1,2})\W?of\W?(\d{1,2})", p, re.I)
        if m1 is not None:
            season = int(m1.group(1))

            spos = m1.start(1) - 1
            if spos > 1:
                show_name = util.clean_string(p[:spos])

            epos = m1.end(2)
            if epos < len(p)-1:
                episode_name = util.clean_string(p[epos:])

            for ep in re.finditer(r"\s*(?:e|-e?|\+e?|&e?)(\d{1,3})",
                                  m1.group(2), re.I):
                e = int(ep.group(1))
                if episode == -1:
                    episode = e
                episode_last = e

        elif m2 is not None:
            season = int(m2.group(1))
            spos = m2.start(1) - 1
            if spos > 1:
                show_name = util.clean_string(p[:spos])

            epos = m2.end(2)
            if epos < len(p)-1:
                episode_name = util.clean_string(p[epos:])

            for ep in re.finditer(r"\s*-?\s*(\d{1,3})", m2.group(2), re.I):
                e = int(ep.group(1))
                if episode == -1:
                    episode = e
                episode_last = e

        elif m3 is not None:
            season = int(m3.group(1))
            spos = m3.start(1) - 1
            if spos > 1:
                show_name = util.clean_string(p[:spos])
        elif m4 is not None:
            episode = int(m4.group(1))
            epos = m4.end(1)
            if epos < len(p)-1:
                episode_name = util.clean_string(p[epos:])
        elif m5 is not None:
            # we're assuming this is a miniseries and the season is always 1
            season = 1
            episode = int(m5.group(1))
            spos = m5.start(1)
            if spos > 1:
                show_name = util.clean_string(p[:spos])
            epos = m5.end(2)
            if epos < len(p)-1:
                episode_name = util.clean_string(p[epos:])
        elif re.search(r"miniseries", p):
            p = util.clean_string(re.sub(r"miniseries", p, flags=re.I))

        return show_name, season, episode, episode_last, episode_name

    def __parse(self, path):
        show_name = None
        season = -1
        episode = -1
        episode_last = -1
        episode_name = None

        no_ext_path, ext_with_dot = os.path.splitext(path)
        ext = ext_with_dot[1:].lower()

        for p in reversed(no_ext_path.split('/')):
            # if we have all the info we want, break out of the loop
            if show_name is not None and season != -1 and episode != -1:
                break

            sn, s, e, el, en = self.__parse_show(p)

            if show_name is None and sn is not None:
                show_name = sn
            if season == -1 and s != -1:
                season = s
            if episode == -1 and e != -1:
                episode = e
            if episode_last == -1 and el != -1:
                episode_last = el
            if episode_name is None and en is not None:
                episode_name = en

        self.__show_name = show_name
        self.__season = season
        self.__episode = episode
        self.__episode_last = episode_last
        self.__episode_name = episode_name
        self.__ext = ext

    def __init__(self, path):
        self.__parse(path)

    def __str__(self):
        out = ''
        if self.__show_name is not None:
            out = self.__show_name
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
        c = util.Confidence()

        c.add(self.__show_name is not None)
        c.add(self.__season != -1)
        c.add(self.__episode != -1)
        c.add(self.__show_name is not None)

        return c.rate()


def determine_parser(path, min_confidence=0.0):
    parsers = [
        ShowPathParser(path),
        MoviePathParser(path),
        MusicPathParser(path)
    ]

    confidence = -1.0
    parser = None

    for p in parsers:
        c = p.confidence()
        if c >= min_confidence and c > confidence:
            confidence = c
            parser = p

    return parser, confidence


if __name__ == "__main__":
    import sys
    path = sys.argv[1]
    parser, confidence = determine_parser(path)

    print 'Input = {0}'.format(path)
    print 'Media type = {0}'.format(parser.type())
    print parser
