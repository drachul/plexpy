# -*- coding: utf-8 -*-
"""
 The media manager manages locally discovered media and arranges it to be
 updated and pushed to the library paths.
"""

import database
import logger
import media.movie
import media.music
import media.show
import os
import os.path
import plexpy
import threading


__HEADING = 'PlexPy Media Manager'


def __logdebug(text):
    logger.debug(u'{0} :: {1}'.format(__HEADING, text))


def __loginfo(text):
    logger.info(u'{0} :: {1}'.format(__HEADING, text))


def __logwarn(text):
    logger.warn(u'{0} :: {1}'.format(__HEADING, text))


def __path_in_results(path, results):
    for r in results:
        if r['path'] == path:
            return True
    return False


def scan_movies():
    """
    scan_movies
    Scans the movie upload directory for movies and stages
    them in the media manager movies table.
    """
    base_dir = plexpy.CONFIG.MM_MOVIE_UPLOAD_DIR
    __logdebug(u'Scanning for movies in: {0}'.format(base_dir))
    db = database.MonitorDatabase()
    try:
        query = 'SELECT path FROM mm_movies'
        results = db.select(query=query)
    except Exception as e:
        __logwarn(u'Unable to execute db query "{0}": {1}'.format(query, e))
        return None

    for root, dirs, files in os.walk(base_dir):
        for file in files:
            path = os.path.join(root, file).decode('utf-8')
            # check to see if this entry is already in the DB
            if not __path_in_results(path, results):
                movie = media.movie.Meta(path, base_dir)
                # we want a confidence of at least 60%
                if movie.confidence >= 0.6:
                    key_dict = {'path': path}
                    value_dict = {'title': movie.title,
                                  'year': movie.year,
                                  'part': movie.part,
                                  'confidence': movie.confidence}
                    __logdebug(u'Adding movie entry "{0}"'.format(path))
                    try:
                        db.upsert('mm_movies', value_dict, key_dict)
                    except Exception as e:
                        __logwarn(u"Unable to perform insert: {0}".format(e))
    __logdebug(u'Finished movies scan')


def scan_shows():
    """
    scan_shows
    Scans the TV show upload directory for TV shows and stages
    them in the media manager shows table.
    """
    base_dir = plexpy.CONFIG.MM_SHOW_UPLOAD_DIR
    __logdebug(u'Scanning for TV shows in: {0}'.format(base_dir))
    db = database.MonitorDatabase()
    try:
        query = 'SELECT path FROM mm_shows'
        results = db.select(query=query)
    except Exception as e:
        __logwarn(u'Unable to execute db query "{0}": {1}'.format(query, e))
        return None

    for root, dirs, files in os.walk(base_dir):
        for file in files:
            path = os.path.join(root, file).decode('utf-8')
            # check to see if this entry is already in the DB
            if not __path_in_results(path, results):
                show = media.show.Meta(path, base_dir)
                # we want a confidence of at least 60%
                if show.confidence >= 0.6:
                    key_dict = {'path': path}
                    value_dict = {'show_name': show.show_name,
                                  'season': show.season,
                                  'episode': show.episode,
                                  'episode_last': show.episode_last,
                                  'episode_name': show.episode_name,
                                  'confidence': show.confidence}
                    __logdebug(u'Adding show entry "{0}"'.format(path))
                    try:
                        db.upsert('mm_shows', value_dict, key_dict)
                    except Exception as e:
                        __logwarn(u"Unable to perform insert: {0}".format(e))
    __logdebug(u'Finished TV shows scan')


def scan_music():
    """
    scan_music
    Scans the music upload directory for music and stages
    them in the media manager music table.
    """
    base_dir = plexpy.CONFIG.MM_MUSIC_UPLOAD_DIR
    __logdebug(u'Scanning for music in: {0}'.format(base_dir))
    db = database.MonitorDatabase()
    try:
        query = 'SELECT path FROM mm_music'
        results = db.select(query=query)
    except Exception as e:
        __logwarn(u'Unable to execute db query "{0}": {1}'.format(query, e))
        return None

    for root, dirs, files in os.walk(base_dir):
        for file in files:
            path = os.path.join(root, file).decode('utf-8')
            # check to see if this entry is already in the DB
            if not __path_in_results(path, results):
                music = media.music.Meta(path, base_dir)
                # we want a confidence of at least 60%
                if music.confidence >= 0.6:
                    key_dict = {'path': path}
                    value_dict = {'artist': music.artist,
                                  'album': music.album,
                                  'year': music.year,
                                  'track': music.track,
                                  'title': music.title,
                                  'confidence': music.confidence}
                    __logdebug(u'Adding music entry "{0}"'.format(path))
                    try:
                        db.upsert('mm_music', value_dict, key_dict)
                    except Exception as e:
                        __logwarn(u"Unable to perform insert: {0}".format(e))
    __logdebug(u'Finished music scan')


def scan_media(media_type=None):
    if media_type == 'movies':
        threading.Thread(target=scan_movies).start()
    elif media_type == 'shows':
        threading.Thread(target=scan_shows).start()
    elif media_type == 'music':
        threading.Thread(target=scan_music).start()
    else:
        __logwarn(u'Invalid media type given to scan: {0}'.format(media_type))
