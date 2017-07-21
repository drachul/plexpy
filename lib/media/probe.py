# -*- coding: utf-8 -*-
"""
"""

import json
import os.path
import re
import subprocess


class Probe:
    """simple media info ffprobe proxy utility class"""
    ffprobe_bin = '/usr/bin/ffprobe'

    @staticmethod
    def better_video_stream(a, b):
        cw = {
            'hevc': 100,
            'h264': 90,
            'mpeg4': 70,
            'mpeg2video': 40,
            'mpeg1video': 20
        }

        if a['width'] > b['width']:
            return a

        cn_a = a['codec_name']
        cn_b = b['codec_name']
        if cn_a in cw and cn_b in cw:
            if cw[cn_a] > cw[cn_b]:
                return a

        if 'bit_rate' in a and 'bit_rate' in b:
            if a['bit_rate'] > b['bit_rate']:
                return a

        return b

    @staticmethod
    def better_audio_stream(a, b):
        cw = {
            'flac': 100,
            'dts': 99,
            'ac3': 90,
            'wmapro': 80,
            'aac': 70,
            'mp3': 60,
            'vorbis': 59,
            'wma': 50,
            'mp2': 40}

        cn_a = a['codec_name']
        cn_b = b['codec_name']
        if cn_a in cw and cn_b in cw:
            if cw[cn_a] > cw[cn_b]:
                return a

        if a['channels'] > b['channels']:
            return a

        if 'bit_rate' in a and 'bit_rate' in b:
            if a['bit_rate'] > b['bit_rate']:
                return a

        return b

    def __ffprobe(self, path):
        cmd = [Probe.ffprobe_bin,
               '-v', 'quiet',
               '-show_format',
               '-show_streams',
               '-show_frames',
               '-read_intervals', '%+#200',
               '-print_format', 'json',
               '-i', path]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        out, err = proc.communicate()
        if out is not None and len(out):
            return json.loads(out)
        else:
            return None

    def __is_stream_actually_video(self, stream):
        cn = stream['codec_name']
        # these are listed as video streams, even though they aren't
        if cn in ('ansi', 'png', 'jpeg', 'bmp'):
            return False
        if cn == 'mjpeg' and 'bit_rate' not in stream:
            return False
        return True

    def __extension(self, format):
        formats = {
            'asf': u'wmv',
            'avi': u'avi',
            'flac': u'flac',
            'mp3': u'mp3',
            'mpeg': u'mpg',
            'mpegts': u'ts',
            'matroska,webm': u'mkv',
            'ogg': u'ogm',
        }
        fn = format['format_name']
        if fn in formats:
            return formats[fn]
        return None

    def __video_format(self, stream):
        format = None
        formats = [
            [3000, '4k'],
            [1900, '1080'],
            [1200, '720'],
            [400,  '480'],
            [0,    'sd']
        ]

        width = int(stream['width'])
        is_progressive = True
        if 'progressive' in stream:
            is_progressive = stream['progressive']
        for fmt in formats:
            w, f = fmt
            if width >= w:
                format = f
                if f != '4k' and f != 'sd':
                    if is_progressive:
                        format += 'p'
                    else:
                        format += 'i'
                break
        return format.decode('utf-8')

    def __video_description(self, stream):
        format = '{0} {1}'.format(stream['codec_long_name'],
                                  self.__video_format(stream))
        if 'bit_rate' in stream:
            format += ' {0}kbps'.format(int(stream['bit_rate']) / 1000)

        return format

    def __audio_description(self, stream):
        format = stream['codec_long_name']
        if 'channel_layout' in stream:
            format += ' {0}'.format(stream['channel_layout'])
        if 'bit_rate' in stream:
            format += ' {0}kbps'.format(int(stream['bit_rate']) / 1000)
        return format

    def __process(self, path):
        has_aud = False
        best_aud = None
        has_eng_aud = False
        eng_aud_idx = -1
        aud_idx = 0

        has_vid = False
        best_vid = None

        has_eng_subs = False

        title = None

        ext = os.path.splitext(path)[1][1:].lower()

        probe = self.__ffprobe(path)

        if probe is not None and 'format' in probe and 'streams' in probe:
            format = probe['format']
            streams = probe['streams']

            ext = self.__extension(format)

            self.__format = format
            self.__streams = streams

            if 'tags' in format:
                for k, v in format['tags'].iteritems():
                    # some streams store english audio stream
                    # information in the format metadata tags
                    m = re.search('IAS(\d+)', k, re.I)
                    if m is not None:
                        if re.search('eng(lish)?', v, re.I):
                            eng_aud_idx = m.group(1)

                    if re.search('title', k, re.I):
                        title = v

            for stream in streams:
                ct = stream['codec_type']
                if ct == 'video' and self.__is_stream_actually_video(stream):
                    has_vid = True
                    if best_vid is None:
                        best_vid = stream
                    else:
                        best_vid = Probe.better_video_stream(stream, best_vid)
                    if 'frames' in probe:
                        for frame in probe['frames']:
                            # some frames may not have a stream index
                            if 'stream_index' in frame and frame['stream_index'] == stream['index']:
                                is_progressive = frame['interlaced_frame'] == 0
                                stream['progressive'] = is_progressive
                                break

                elif ct == 'audio':
                    has_aud = True
                    if best_aud is None:
                        best_aud = stream
                    else:
                        best_aud = Probe.better_audio_stream(stream, best_aud)

                    # attempt to determine if there is an english audio stream
                    if not has_eng_aud:
                        if eng_aud_idx != -1:
                            if aud_idx == eng_aud_idx:
                                has_eng_aud = True
                        else:
                            if 'tags' in stream:
                                for k, v in stream['tags'].iteritems():
                                    if re.search("^lang(uage)?$", k, re.I):
                                        if re.search('eng?(lish)?', v, re.I):
                                            has_eng_aud = True
                                        break
                    aud_idx += 1

                elif ct == 'subtitle':
                    if 'tags' in stream:
                        for k, v in stream['tags'].iteritems():
                            if re.search('^lang(uage)$', k, re.I):
                                if re.search('eng?(lish)?', v, re.I):
                                    has_eng_aud = True

        self.__has_video = has_vid
        self.__has_audio = has_aud
        self.__best_video_stream = best_vid
        self.__best_audio_stream = best_aud
        self.__has_eng_audio = has_eng_aud
        self.__has_eng_subtitles = has_eng_subs
        self.__title = title
        self.__extension = ext

    def __repr__(self):
        vst = self.best_video_stream()
        ast = self.best_audio_stream()
        out = self.__format['format_long_name']
        if vst is not None:
            out += ' - {0}'.format(self.__video_description(vst))
        if ast is not None:
            out += ' - {0}'.format(self.__audio_description(vst))
        return out

    def __str__(self):
        vst = self.best_video_stream()
        ast = self.best_audio_stream()
        out = self.__format['format_long_name']
        if vst is not None:
            out += ' - {0}'.format(self.__video_description(vst))
        if ast is not None:
            out += ' - {0}'.format(self.__audio_description(ast))
        return out

    def __init__(self, path):
        self.__process(path)

    def __getattr__(self, attr):
        if attr == 'format':
            return self.__format
        elif attr == 'streams':
            return self.__streams
        else:
            return None

    def has_audio(self):
        return self.__has_audio

    def has_english_audio(self):
        return self.__has_eng_audio

    def best_audio_stream(self):
        return self.__best_audio_stream

    def has_video(self):
        return self.__has_video

    def best_video_stream(self):
        return self.__best_video_stream

    def video_format(self, stream=None):
        format = None
        if stream is None:
            stream = self.best_video_stream()

        if stream is not None:
            format = self.__video_format(stream)

        return format

    def audio_format(self, stream=None):
        format = None
        if stream is None:
            stream = self.best_audio_stream()

        if stream is not None:
            format = self.__audio_format(stream)

        return format

    def has_english_subtitles(self):
        return self.__has_eng_subtitles

    def extension(self):
        return self.__extension


if __name__ == "__main__":
    import sys
    path = sys.argv[1]
    print Probe(path)
