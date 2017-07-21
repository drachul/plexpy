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
import media.util
import media.probe
import os
import os.path
import plexpy
import threading


__HEADING = 'PlexPy Media Manager'

__movies_lock = threading.Lock()
__shows_lock = threading.Lock()
__music_lock = threading.Lock()


def __logdebug(text):
    logger.debug(u'{0} :: {1}'.format(__HEADING, text))


def __loginfo(text):
    logger.info(u'{0} :: {1}'.format(__HEADING, text))


def __logwarn(text):
    logger.warn(u'{0} :: {1}'.format(__HEADING, text))


def __path_in_results(path, results):
    """
    utility function to search a list of db results
    to see if it contains the given path
    """
    for r in results:
        if r['path'] == path:
            return True
    return False


def __verify_media(m_in, base_dir):
    """
    verifies if an an output exists given an input media file
    and if so compares the best audio and video streams to determine
    if the input media is an upgrade to the file which already exists
    """
    path = os.path.join(base_dir, m_in.dir, m_in.file)
    if os.path.isfile(path):
        p_in = m_in.probe
        p_out = media.probe.Probe(path)

        if p_in.has_video and not p_out.has_video:
            return True, True

        if p_in.has_video and p_out.has_video:
            vs_in = p_in.best_video_stream()
            vs_out = p_out.best_video_stream()
            vs_best = media.probe.Probe.better_video_stream(vs_in, vs_out)
            if vs_best == vs_in:
                return True, True

        if p_in.has_audio and not p_out.has_audio:
            return True, True

        if p_in.has_audio and p_out.has_audio:
            as_in = p_in.best_audio_stream()
            as_out = p_out.best_audio_stream()
            as_best = media.probe.Probe.better_audio_stream(as_in, as_out)
            if as_best == as_out:
                return True, True

        return True, False

    return False, False


def __del_files(db, table):
    """
    scans the given table for files that no longer exist and then
    remove them from the table
    """
    __logdebug(u'Scanning for deleted files in {0}'.format(table))
    try:
        query = 'SELECT id, path from {0}'.format(table)
        results = db.select(query=query)
    except Exception as e:
        __logwarn(u'Unable to execute db query "{0}": {1}'.format(query, e))
        return None

    ids_to_del = []

    for r in results:
        if not os.path.isfile(r['path']):
            __logdebug(u'Removing entry with file: "{0}"'.format(r['path']))
            ids_to_del.append(str(r['id']))

    #__logdebug("IDs to delete: {0}".format(ids_to_del))

    if len(ids_to_del) == 0:
        return None

    query = 'DELETE from {0} where id in ({1})'.format(
        table, '?' + ',?' * (len(ids_to_del)-1))

    #__logdebug("delete query: '{0}'".format(query))

    try:
        db.action(query, ids_to_del)
    except Exception as e:
        __logwarn(u"Unable to perform delete: {0}".format(e))

    __logdebug(u'Finished scanning for deleted files in {0}'.format(table))


def __add_movies(base_dir, db, tmdbapikey):
    """
    """
    __logdebug(u'Scanning for new movies in: {0}'.format(base_dir))

    try:
        query = 'SELECT path FROM mm_movies'
        results = db.select(query=query)
    except Exception as e:
        __logwarn(u'Unable to execute db query "{0}": {1}'.format(query, e))
        return None

    search = None

    if tmdbapikey is not None and len(tmdbapikey) > 0:
        search = media.movie.Search(tmdbapikey)

    for root, dirs, files in os.walk(base_dir):
        for file in files:
            path = os.path.join(root, file).decode('utf-8')
            # check to see if this entry is already in the DB
            if not __path_in_results(path, results):
                movie = media.movie.File(path, base_dir)
                if movie.confidence > 0.6:
                    processed = False
                    if search is not None:
                        search_movie = search.title_from_file(movie)
                        if search_movie is not None:
                            movie = search_movie
                            processed = True
                    exists, upgrade = __verify_media(movie, base_dir)
                    key_dict = {'path': path}
                    value_dict = {'title': movie.title,
                                  'year': movie.year,
                                  'part': movie.part,
                                  'movie_id': movie.id,
                                  'confidence': movie.confidence,
                                  'is_processed': processed,
                                  'already_exists': exists,
                                  'is_upgrade': upgrade}
                else:
                    key_dict = {'path': path}
                    value_dict = {'confidence': movie.confidence,
                                  'is_processed': True}
                __logdebug(u'Adding movie entry "{0}"'.format(path))
                try:
                    db.upsert('mm_movies', value_dict, key_dict)
                except Exception as e:
                    __logwarn(u"Unable to perform insert: {0}".format(e))
    __logdebug(u'Finished movies scan')


def process_movies():
    """
    process_movies
    Scans the movie upload directory for movies and stages
    them in the media manager movies table.
    Also processes movie meta searches
    """
    with media.util.Locker(__movies_lock):
        base_dir = plexpy.CONFIG.MM_MOVIE_UPLOAD_DIR
        tmdbapikey = plexpy.CONFIG.MM_MOVIE_APIKEY
        db = database.MonitorDatabase()
        __del_files(db, 'mm_movies')
        __add_movies(base_dir, db, tmdbapikey)


def __add_shows(base_dir, db, tvdbapikey):
    """
    """
    __logdebug(u'Scanning for new TV shows in: {0}'.format(base_dir))
    try:
        query = 'SELECT path FROM mm_shows'
        results = db.select(query=query)
    except Exception as e:
        __logwarn(u'Unable to execute db query "{0}": {1}'.format(query, e))
        return None

    search = None

    if tvdbapikey is not None and len(tvdbapikey) > 0:
        search = media.show.Search(tvdbapikey)

    for root, dirs, files in os.walk(base_dir):
        for file in files:
            path = os.path.join(root, file).decode('utf-8')
            # check to see if this entry is already in the DB
            if not __path_in_results(path, results):
                show = media.show.File(path, base_dir)
                if show.confidence > 0.6:
                    processed = False
                    if search is not None:
                        search_show = search.episode_from_file(show)
                        if search_show is not None:
                            show = search_show
                            processed = True
                    exists, upgrade = __verify_media(show, base_dir)
                    key_dict = {'path': path}
                    value_dict = {'show_name': show.show_name,
                                  'show_id': show.show_id,
                                  'season': show.season,
                                  'episode': show.episode,
                                  'episode_id': show.episode_id,
                                  'episode_last': show.episode_last,
                                  'episode_name': show.episode_name,
                                  'confidence': show.confidence,
                                  'is_processed': processed,
                                  'already_exists': exists,
                                  'is_upgrade': upgrade}
                else:
                    key_dict = {'path': path}
                    value_dict = {'confidence': show.confidence,
                                  'is_processed': True}

                __logdebug(u'Adding show entry "{0}"'.format(path))
                try:
                    db.upsert('mm_shows', value_dict, key_dict)
                except Exception as e:
                    __logwarn(u"Unable to perform insert: {0}".format(e))
    __logdebug(u'Finished TV shows scan')


def process_shows():
    """
    process_shows
    Scans the TV show upload directory for TV shows and stages
    them in the media manager shows table.
    """
    with media.util.Locker(__music_lock):
        base_dir = plexpy.CONFIG.MM_SHOW_UPLOAD_DIR
        tvdbapikey = plexpy.CONFIG.MM_SHOW_APIKEY
        db = database.MonitorDatabase()
        __del_files(db, 'mm_shows')
        __add_shows(base_dir, db, tvdbapikey)


def __add_music(base_dir, db):
    """
    """
    __logdebug(u'Scanning for music in: {0}'.format(base_dir))
    try:
        query = 'SELECT path FROM mm_music'
        results = db.select(query=query)
    except Exception as e:
        __logwarn(u'Unable to execute db query "{0}": {1}'.format(query, e))
        return None

    search = media.music.Search()

    for root, dirs, files in os.walk(base_dir):
        for file in files:
            path = os.path.join(root, file).decode('utf-8')
            # check to see if this entry is already in the DB
            if not __path_in_results(path, results):
                music = media.music.File(path, base_dir)
                if music.confidence > 0.6:
                    processed = False
                    if search is not None:
                        search_music = search.track_from_file(music)
                        if search_music is not None:
                            music = search_music
                            processed = True
                    exists, upgrade = __verify_media(music, base_dir)
                    key_dict = {'path': path}
                    value_dict = {'artist': music.artist,
                                  'artist_id': music.artist_id,
                                  'album': music.album,
                                  'album_id': music.album_id,
                                  'year': music.year,
                                  'track': music.track,
                                  'track_id': music.track_id,
                                  'title': music.title,
                                  'confidence': music.confidence,
                                  'is_processed': processed,
                                  'already_exists': exists,
                                  'is_upgrade': upgrade}
                else:
                    key_dict = {'path': path}
                    value_dict = {'confidence': music.confidence,
                                  'is_processed': True}
                __logdebug(u'Adding music entry "{0}"'.format(path))
                try:
                    db.upsert('mm_music', value_dict, key_dict)
                except Exception as e:
                    __logwarn(u"Unable to perform insert: {0}".format(e))
    __logdebug(u'Finished music scan')


def process_music():
    """
    process_music
    Scans the music upload directory for music and stages
    them in the media manager music table.
    """
    with media.util.Locker(__music_lock):
        base_dir = plexpy.CONFIG.MM_MUSIC_UPLOAD_DIR
        db = database.MonitorDatabase()
        __del_files(db, 'mm_music')
        __add_music(base_dir, db)


def process_media(media_type):
    """
    processes media for the given media type will launch
    a thread with the associated process function
    """
    if media_type == 'movies':
        threading.Thread(target=process_movies).start()
    elif media_type == 'shows':
        threading.Thread(target=process_shows).start()
    elif media_type == 'music':
        threading.Thread(target=process_music).start()
    else:
        __logwarn(
            u'Invalid media type given to process: {0}'.format(media_type))
