# -*- coding: utf-8 -*-
"""

"""

from probe import Probe
import os.path
import re
import util


class Meta:
    """ Meta """
    max_duration = float(60 * 60)  # 1hr
    min_size = (1024 * 1024 * 20)  # 20MB

    def __parse_path(self, path):
        show_name = None
        season = -1
        episode = -1
        episode_last = -1
        episode_name = None

        p = util.clean_media(path)

        # s??e?? type episodes
        m1 = re.search(
            ur"s(\d{1,2})[\s\._]*((?:(?:\s*e|-e?|\+e?|&e?)\d{1,3})+)", p, re.I)
        # SSxEE type episodes
        m2 = re.search(ur"(\d{1,2})((?:\s*(?:x|-)\s*\d{1,3})+)", p, re.I)
        # Season by itself
        m3 = re.search(ur"s(?:eason)?\W?(\d{1,2})", p, re.I)
        # Episode by itself (start of name)
        m4 = re.search(ur"^\s*(?:p(?:ar)?t)?\s*(\d{1,3})", p, re.I)
        # Episode by itself - miniseries (X of Y)
        m5 = re.search(ur"(\d{1,2})\W?of\W?(\d{1,2})", p, re.I)
        if m1 is not None:
            season = int(m1.group(1))

            spos = m1.start(1) - 1
            if spos > 1:
                show_name = util.clean_string(p[:spos])

            epos = m1.end(2)
            if epos < len(p)-1:
                episode_name = util.clean_string(p[epos:])

            for ep in re.finditer(ur"\s*(?:e|-e?|\+e?|&e?)(\d{1,3})",
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

            for ep in re.finditer(ur"\s*-?\s*(\d{1,3})", m2.group(2), re.I):
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
        elif re.search(ur"miniseries", p):
            p = util.clean_string(re.sub(ur"miniseries", p, flags=re.I))

        return show_name, season, episode, episode_last, episode_name

    def __process_path(self, path):
        show_name = None
        season = -1
        episode = -1
        episode_last = -1
        episode_name = None

        no_ext_path, ext_with_dot = os.path.splitext(path)
        ext = ext_with_dot[1:].lower()

        for p in reversed(no_ext_path.split(os.sep)):
            # if we have all the info we want, break out of the loop
            if show_name is not None and season != -1 and episode != -1:
                break

            sn, s, e, el, en = self.__parse_path(p)

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

        self.__dict__['show_name'] = show_name
        self.__dict__['season'] = season
        self.__dict__['episode'] = episode
        self.__dict__['episode_last'] = episode_last
        self.__dict__['episode_name'] = episode_name
        self.__dict__['extension'] = ext

    def __process_probe(self, path):
        probe = Probe(path)

        self.__dict__['has_video'] = False
        self.__dict__['video_format'] = None
        self.__dict__['duration'] = 0.0

        if probe.format is not None:
            if 'duration' in probe.format:
                self.__dict__['duration'] = float(probe.format['duration'])
            ext = probe.extension()
            if ext is not None:
                self.__dict__['extension'] = ext

        if probe.streams is not None:
            self.__dict__['has_video'] = probe.has_video()
            self.__dict__['video_format'] = probe.video_format()

    def __modified_path(self, path, base_dir):
        if base_dir is not None:
            path = path.replace(base_dir, '')
        if path[0] == u'/':
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
            self.__process_path(path)
        self.__dict__['processed_path'] = process_path

        if process_probe:
            # extract meta data embedded in the media
            self.__process_probe(path)
        self.__dict__['processed_probe'] = process_probe

    def __confidence(self):
        # half the confidence is determined by the meta
        c_meta = util.Confidence()
        c_meta.add(self.show_name is not None)
        c_meta.add(self.season != -1)
        c_meta.add(self.episode != -1)
        c_meta.add(self.show_name is not None)

        # if this doesn't have video, force to 0
        if not self.has_video:
            return 0.0

        # the other half is determined by the duration and format of the media
        c_media = util.Confidence()
        c_media.add(self.duration < Meta.max_duration)
        c_media.add(self.size >= Meta.min_size)

        return (c_meta.rate() * 0.5) + (c_media.rate() * 0.5)

    def __build_file(self):
        out = ''
        if self.show_name is not None:
            out = self.show_name
            if self.season != -1:
                if self.episode_last != self.episode:
                    out += u' s{0:0=2}e{1:0=2}-e{2:0=2}'.format(
                        self.season, self.episode, self.episode_last)
                else:
                    out += u' s{0:0=2}e{1:0=2}'.format(
                        self.season, self.episode)

            if self.episode_name is not None:
                out += u' {0}'.format(self.episode_name)

            out += u'.{0}'.format(self.extension)
        return out

    def __build_dir(self):
        out = u''
        if self.show_name is not None:
            out = self.show_name
            if self.season != -1:
                out += u'/Season {0:0=2}'.format(self.season)
        return out

    def __getattr__(self, attr):
        if attr == 'file':
            return self.__build_file()
        elif attr == 'dir':
            return self.__build_dir()
        elif attr == 'type':
            return 'show'
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
    path = sys.argv[1].decode('utf-8')
    base_dir = None
    if len(sys.argv) > 2:
        base_dir = sys.argv[2].decode('utf-8')
    show = Meta(path, base_dir)
    if show is not None:
        print u'Input = "{0}" (confidence: {1})'.format(path, show.confidence)
        print u'Output = "{0}/{1}"'.format(show.dir, show.file)
