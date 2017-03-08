# -*- coding: utf-8 -*-
"""

"""

import re
from difflib import SequenceMatcher


def sanitize_path(p):
    p = re.sub(ur"[\*\?]", "", p)
    p = re.sub(ur"\s*&\s*", " and ", p)
    p = re.sub(ur": ", " - ", p)
    p = re.sub(ur":", "-", p)
    p = re.sub(ur"\\", "-", p)
    p = re.sub(ur"/", "-", p)
    p = re.sub(ur" {2,}", " ", p)
    return p.strip().decode('utf-8')


def simplify_string(s):
    s = re.sub(ur"[^\wÀ-ý]+", "", s, re.UNICODE)
    s = re.sub(ur"_+", "", s)
    return s.strip().lower().decode('utf-8')


def string_similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def clean_string(s):
    s = re.sub(ur"_", " ", s)
    # s = re.sub(ur"[\W]", " ", s, re.UNICODE)
    # hack because \W doesn't work with UTF-8 strings?
    s = re.sub(ur"[^\wÀ-ý ]", " ", s, re.UNICODE)
    s = re.sub(ur" {2,}", " ", s)
    return s.strip()


def listRegexDel(l, s, f=0):
    rx = ur'({0})'.format("|".join(l))
    return re.sub(rx, "", s, flags=f)


def clean_media(s):
    # remove scene tags
    scene_tags = ['-2HD',
                  '-aAF', '-AMIABLE', '-AVCHD',
                  '-BATV', '-BLOW', '-BRMP', '-BTN', '-BTW',
                  '-CiNEFiLE', '-CREEPSHOW', '-CROOKS', '-CULTHD',
                  '-DEFLATE', '-DIMENSION',
                  '-ehMD', '\[ettv\]', '-EVO', '-EVOLVE',
                  '-FGT',
                  '-GECKOS', '-GUACAMOLE',
                  '-HDB', '-hV',
                  '-KILLERS',
                  '-KiNGS',
                  '-LiBRARiANS',
                  '-MARS', '-MAXSPEED', '-MCH', '-MOROSE', '-MOVEE',
                  '-mSD', 'MVGroup(?:\.org)?',
                  '-NOGRP', '-NTb',
                  '-PSYCHD',
                  '-REMARKABLE',
                  '-SADPANDA', '-SB', '-SERIOUSLY', '-SiNNERS', '-SORNY',
                  '-SPARKS', '-SPRiNTER',
                  '-RARBG', '\[rarbg\]', '\[rartv\]', '-RTN',
                  '-TASTETV', '-TiMELORDS', '-TrollU?HD',
                  '-VoMiT',
                  '-W4F', 'www\.torrenting\.com']
    s = listRegexDel(scene_tags, s, re.UNICODE)

    # remove source tags
    source_tags = ['hd\W?dvd\W?(rip)?', 'dvd(\W?rip)?',
                   'blu-?ray', 'bd(\W?rip)?',
                   '(hd)?tv(\W?rip)?', 'web\W?(rip|dl)?']
    s = listRegexDel(source_tags, s, re.I)

    # remove video format tags
    vidfmt_tags = ['4k', '2160p', '1080[ip]', '720p', '480p', 'hd', 'sd']
    s = listRegexDel(vidfmt_tags, s, re.I)

    # remove video codec tags
    vidcodec_tags = ['x264', 'x265',
                     'h\.?264', 'h\.265',
                     'mpe?g-?4?', '(8|10)-?bit',
                     'xvid', 'divx']
    s = listRegexDel(vidcodec_tags, s, re.I)

    # remove audio tags
    aud_tags = ['ac\W?3\W?(\d+\.\d)?',
                'dd\W?(\d+\.\d)',
                'aac\W?(\d\.\d)?',
                'mp3\W?(\d\.\d)?']
    s = listRegexDel(aud_tags, s, re.I)

    return clean_string(s)


def detect_meta(path, min_confidence=0.0):
    import movie
    import music
    import show
    best_c = 0.0
    meta = None
    media = [movie.Meta(path), music.Meta(path), show.Meta(path)]
    for m in media:
        c = m.confidence()
        if c > min_confidence and c > best_c:
            meta = m
            best_c = c

    return meta, best_c


class Confidence:

    """
    Confidence
    """

    def __init__(self):
        self.__count = 0
        self.__succeeded = 0

    def add(self, good):
        if good:
            self.__succeeded += 1
        self.__count += 1

    def rate(self):
        return float(self.__succeeded) / float(self.__count)
