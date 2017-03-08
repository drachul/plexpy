# -*- coding: utf-8 -*-
"""
"""
from datetime import date
from probe import Probe
import os
import os.path
import re
import util


class Meta:
    """ Meta """
    min_duration = float(60 * 60)   # 60mins
    min_size = (1024 * 1024 * 600)  # 600MB

    def __parse_path(self, path):
        # print '__parse_path("{0}")'.format(path)
        title = None
        year = -1
        yearpos = -1
        part = -1
        partpos = -1

        path = util.clean_media(path)

        # extract the year if available (scan backwards)
        ym = []
        for m in re.finditer(ur"((?:19|20)\d{2})", path):
            y = int(m.group())
            if y <= date.today().year:
                ym.append([y, m.start()])

        if len(ym) > 0:
            year = ym[-1][0]
            yearpos = ym[-1][1]

        # extract the part if available
        m = re.search(ur"""(?:
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

    def __process_path(self, path):
        """ Process a path to extract meta information """
        # print '__process_path("{0}")'.format(path)
        title = None
        year = -1
        part = -1

        no_ext_path, ext_with_dot = os.path.splitext(path)
        ext = ext_with_dot[1:].lower()

        for p in reversed(no_ext_path.split('/')):
            # if we have all the info we want, break out of the loop
            if title is not None and year != -1:
                break

            t, y, p = self.__parse_path(p)

            if title is None and t is not None:
                title = t

            if year == -1 and y != -1:
                year = y

            if part == -1 and p != -1:
                part = p

        self.__dict__['title'] = title
        self.__dict__['year'] = year
        self.__dict__['part'] = part
        self.__dict__['extension'] = ext

    def __process_probe(self, path):
        """ Process a media probe for meta information """
        # print '__process_probe("{0}")'.format(path)
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
            if 'tags' in probe.format:
                for k, v in probe.format['tags'].iteritems():
                    if re.search(ur"^title$", k, re.I):
                        t, y, p = self.__parse_path(v)
                        self.__dict__['title'] = t.decode('utf-8')
                        if self.__dict__['year'] == -1:
                            self.__dict__['year'] = y
                        if self.__dict__['part'] == -1:
                            self.__dict__['part'] = p
                    elif re.search(ur"^(date|year)$", k, re.I):
                        m = re.search(ur"((?:19|20)\d{2})", v)
                        if m is not None:
                            self.__dict__['year'] = int(m.group(1))

        if probe.streams is not None:
            self.__dict__['has_video'] = probe.has_video()
            self.__dict__['video_format'] = probe.video_format()

    def __parse_support_file(self, path):
        import fileinput
        # print '__parse_support_file("{0}")'.format(path)
        lines = fileinput.input(path)
        # right now we're only looking for an imdb ID
        for line in lines:
            m = re.search(ur"(tt(\d{7}))", line, re.I)
            if m is not None:
                self.__dict__['imdbid'] = m.group(1).decode('utf-8')
                return True
        lines.close()
        return False

    def __process_support_files(self, path, base_dir):
        # print '__process_support_files("{0}", "{1}")'.format(path, base_dir)
        self.__dict__['imdbid'] = None
        search_dir = os.path.dirname(path)
        # if the base path was given, make sure we don't over-scan
        # if the given media file is in the base path
        if base_dir is not None and base_dir == search_dir:
            return
        # search directory of the given path for any supporting files
        # to attempt to extract information out of
        for node in os.listdir(search_dir):
            file = os.path.join(search_dir, node)
            if os.path.isfile(file):
                root, ext = os.path.splitext(node)
                if ext.lower() in ('.txt', '.nfo'):
                    if self.__parse_support_file(file):
                        return

    def __modified_path(self, path, base_dir):
        if base_dir is not None:
            path = path.replace(base_dir, '')
        if path[0] == '/':
            path = path[1:]
        return path

    def __process(self, path, base_dir,
                  process_path=True, process_probe=True,
                  process_support_files=False):

        """
        Assumes path and base_dir are unicode strings
        """

        # print u'__process("{0}", "{1}", process_path={2}, process_probe={3},
        # process_support_files={4})'.format(path, base_dir, process_path, process_probe, process_support_files)

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

        if process_support_files:
            # extract meta data from local supporting files
            self.__process_support_files(path, base_dir)
        self.__dict__['processed_support_files'] = process_support_files

    def __confidence(self):
        # half the confidence is determined by the meta
        c_meta = util.Confidence()
        c_meta.add(self.title is not None)
        c_meta.add(self.year != -1)

        # if this doesn't have video, force to 0
        if not self.has_video:
            return 0.0

        # the other half is determined by the duration and format of the media
        c_media = util.Confidence()
        if self.__dict__['processed_probe']:
            c_media.add(self.duration >= Meta.min_duration)
            c_media.add(self.has_video)
        c_media.add(self.size >= Meta.min_size)

        return (c_meta.rate() * 0.5) + (c_media.rate() * 0.5)

    def __build_file(self):
        out = ''
        if self.title is not None:
            out = self.title
            if self.year != -1:
                out += ' ({0})'.format(self.year)

            if self.video_format is not None:
                out += ' {0}'.format(self.video_format)

            if self.part != -1:
                out += ' part {0}'.format(self.part)

            out += '.{0}'.format(self.extension)
        return out

    def __build_dir(self):
        out = ''
        if self.title is not None:
            out = self.title
            if self.year != -1:
                out += ' ({0})'.format(self.year)
        return out

    def __getattr__(self, attr):
        if attr == 'file':
            return self.__build_file()
        elif attr == 'dir':
            return self.__build_dir()
        elif attr == 'type':
            return 'movie'
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
    movie = Meta(path, base_dir=base_dir)
    if movie is not None:
        print 'Input = "{0}" (confidence: {1})'.format(path, movie.confidence)
        print 'Output = "{0}/{1}"'.format(movie.dir, movie.file)
        if movie.imdbid is not None:
            print 'IMDB ID = {0}'.format(movie.imdbid)
