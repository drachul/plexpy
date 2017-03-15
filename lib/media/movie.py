# -*- coding: utf-8 -*-
"""
 This module will extract meta information for a movie from a given path.
 It utilizes parsing the actual path, probing the file with a media probe,
 and evaluating local supporting files in order to accumulate the metadata.
"""

from datetime import date
import imdb
import os
import os.path
from probe import Probe
import re
import tmdbsimple
import util


class File:
    """
    Encapsulates a movie file containing various metadata
    about it including formats and title/year/part information.
    """
    min_duration = float(60 * 60)   # 60mins
    min_size = (1024 * 1024 * 600)  # 600MB

    def __clean_string(self, s):
        # remove movie 'feature' tags
        feature_tags = ['directors?(\s*cut)?',
                        'extended',
                        'internal',
                        'remastered',
                        'theatrical release'
                        'uncut',
                        'unrated'
                        ]
        s = util.list_re_del(feature_tags, s, re.U | re.I)
        return util.clean_string(s)

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
            title = self.__clean_string(path[:pos-1])
        else:
            title = self.__clean_string(path)

        if year != -1:
            title = self.__clean_string(
                re.sub(ur"{0}".format(year), "", title))

        return title, year, part

    def __process_path(self, path):
        """ Process a path to extract meta information """
        # print '__process_path("{0}")'.format(path)
        title = None
        year = -1
        part = -1

        no_ext_path, ext_with_dot = os.path.splitext(path)
        ext = ext_with_dot[1:].lower()

        for p in reversed(no_ext_path.split(os.sep)):
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
        self.__dict__['probe'] = probe
        self.__dict__['has_video'] = False
        self.__dict__['has_audio'] = False
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
                        self.__dict__['title'] = self.__clean_string(t.decode('utf-8'))
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

        patterns = [
            ur"(?P<id>tt\d{7})",
            ur"https?://.*themoviedb.org/movie/(?P<id>\d+)"
        ]

        # right now we're only looking for an imdb ID
        for line in lines:
            m = util.list_re_search(patterns, line, re.I)
            if m is not None:
                self.__dict__['id'] = m.group('id').decode('utf-8')
                return True
        lines.close()
        return False

    def __process_support_files(self, path, base_dir):
        # print '__process_support_files("{0}", "{1}")'.format(path, base_dir)
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
        if path.startswith(os.sep):
            path = path[1:]
        return path

    def __process(self, path, base_dir,
                  process_path=True, process_probe=True,
                  process_support_files=False):
        """
        Assumes path and base_dir are unicode strings
        """
        # print u'__process("{0}", "{1}", process_path={2}, process_probe={3},
        # process_support_files={4})'.format(path, base_dir, process_path,
        # process_probe, process_support_files)

        modpath = self.__modified_path(path, base_dir)
        self.__dict__['modpath'] = modpath
        self.__dict__['path'] = path
        self.__dict__['size'] = os.path.getsize(path)
        self.__dict__['id'] = None

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
            c_media.add(self.duration >= File.min_duration)
            c_media.add(self.has_video)
        c_media.add(self.size >= File.min_size)

        return (c_meta.rate() * 0.5) + (c_media.rate() * 0.5)

    def __build_file(self):
        out = ''
        if self.title is not None:
            out = util.sanitize_path(self.title)
            if self.year != -1:
                out += ' ({0})'.format(self.year)

            if self.video_format is not None:
                out += ' {0}'.format(self.video_format)

            if self.part != -1:
                out += ' part{0}'.format(self.part)

            out += '.{0}'.format(self.extension)
        return out

    def __build_dir(self):
        out = ''
        if self.title is not None:
            out = util.sanitize_path(self.title)
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
    an even simpler wrapper around tmdbsimple to provide
    basic information and search capabilities based on targeted
    items and convenience functions to interact with movie.File
    objects
    """
    @staticmethod
    def url(id):
        if re.search(ur"tt\d{7}", id, re.I):
            return u"http://www.imdb.com/title/{0}/".format(id)
        else:
            return u"https://www.themoviedb.org/movie/{0}".format(id)

    @staticmethod
    def __title_filter(x):
        if re.search(ur"(tv.+episode\s+\d+)", x['title'], re.I):
            return False

        return True

    def __init__(self, apikey):
        tmdbsimple.API_KEY = apikey

    def __search_tmdb(self, title, year):
        """
        searches for a given movie title in The MovieDB and return
        a list of results in order of relevance, based on the year difference
        and the popularity of the entry.
        """
        if title is None:
            return []

        search = tmdbsimple.Search()
        search.movie(query=title)

        for r in search.results:
            y = -1
            y_d = 9999
            if year != -1:
                m = re.search(ur"((?:19|20)\d{2})", r['release_date'])
                if m is not None:
                    y = int(m.group(1))
                if y != -1:
                    y_d = abs(year - y)

            r['year'] = y
            r['year_delta'] = y_d

        results = sorted(
            search.results,
            key=lambda r: (r['year_delta'], -r['popularity']))

        return results

    def __search_imdb(self, title, year):
        im = imdb.IMDb()
        results = im.search_movie(title)

        if len(results) > 0:
            # filter out 'tv' entries
            results = filter(Search.__title_filter, results)
            for r in results:
                y_d = 9999
                if year != -1:
                    if 'year' in r and r['year'] != 0:
                        y_d = abs(year - r['year'])
                r['id'] = r.movieID
                r['year_delta'] = y_d

            results = sorted(
                results,
                key=lambda r: r['year_delta'])

        return results

    def title(self, title, year):
        """
        Search for a title, initially from TMDB then if
        no results are returned from that, IMDb.  Results
        will be ordered by proximity of the year given.
        """
        results = self.__search_tmdb(title, year)
        if len(results) == 0:
            results = self.__search_imdb(title, year)
        return results

    def title_from_file(self, movie):
        """
        a convenience function for doing a TMDB search using
        a movie.File object that already contains a title/year
        """
        results = self.title(movie.title, movie.year)

        if len(results) == 0:
            return None

        movie.title = results[0]['title']
        movie.year = results[0]['year']
        movie.id = results[0]['id']

        return movie


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Media Movie Module')
    parser.add_argument('--basedir', '-b', default=None,
                        help='The base directory to use for path filtering')
    parser.add_argument('--search', '-s', default=None, metavar='TMDB_APIKEY',
                        help='Flag to enable TMDB/IMDb processing')
    parser.add_argument('input', help='The input file to process')
    args = parser.parse_args()

    args.input = args.input.decode('utf-8')
    if args.basedir is not None:
        args.basedir = args.basedir.decode('utf-8')
    mov = File(args.input, args.basedir)
    updated_mov = None
    print u'Input = "{0}" (confidence:{1})'.format(args.input, mov.confidence)
    if args.search is not None:
        updated_mov = Search(args.search).title_from_file(mov)
        if updated_mov is not None:
            mov = updated_mov

    if mov is not None:
        print u'Output = "{0}/{1}"'.format(mov.dir, mov.file)
        if mov.id is not None:
            print 'Movie ID = {0}'.format(mov.id)
    else:
        print u'Something went wrong...'
