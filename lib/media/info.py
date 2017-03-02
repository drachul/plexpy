import json
import re
import subprocess


class Info:
    """simple media info ffprobe proxy utility class"""

    ffprobe_bin = '/usr/bin/ffprobe'

    @staticmethod
    def fetch(file):
        cmd = [Info.ffprobe_bin,
               '-v', 'quiet',
               '-show_format',
               '-show_streams',
               '-print_format', 'json',
               '-i', file]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        out, err = proc.communicate()
        return json.loads(out.decode())

    def __better_video_stream(self, a, b):
        if a['width'] > b['width']:
            return a
        if a['bit_rate'] > b['bit_rate']:
            return a
        return b

    def __better_audio_stream(self, a, b):
        cw = {
            'dts': 100,
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

        if a['bit_rate'] > b['bit_rate']:
            return a

        return b

    def __video_format(self, stream):
        format = None
        formats = {
            3000: '4k',
            1900: '1080',
            1200: '720',
            400:  '480',
            0:    'sd'
        }

        width = stream['width']
        is_progressive = re.search(r'p$', stream['pix_fmt']) is not None
        for w, f in formats:
            if width >= w:
                format = f
                if f != '4k':
                    if is_progressive:
                        format += 'p'
                    else:
                        format += 'i'
                break
        return format

    def __is_stream_actually_video(self, stream):
        # these are listed as video streams, even though they aren't
        if stream['codec_name'] in ('ansi', 'png', 'jpeg', 'bmp'):
            return False
        return True

    def __process(self, info):
        has_aud = False
        best_aud = None
        has_eng_aud = False
        eng_aud_idx = -1
        aud_idx = 0

        has_vid = False
        best_vid = None

        has_eng_subs = False

        title = None

        if 'tags' in info['format']:
            for k, v in info['format']['tags'].iteritems():
                # some streams store english audio stream
                # information in the format metadata tags
                m = re.search('IAS(\d+)', k, re.I)
                if m is not None:
                    if re.search('eng(lish)?', v, re.I):
                        eng_aud_idx = m.group(1)

                if re.search('title', k, re.I):
                    title = v

        if info is not None:
            for stream in info['streams']:
                ct = stream['codec_type']
                if ct == 'video' and self.__is_stream_actually_video(stream):
                    has_vid = True
                    if best_vid is None:
                        best_vid = stream
                    else:
                        best_vid = self.__better_video_stream(stream, best_vid)

                elif ct == 'audio':
                    has_aud = True
                    if best_aud is None:
                        best_aud = stream
                    else:
                        best_aud = self.__better_audio_stream(stream, best_aud)

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

        self.__info = info
        self.__has_video = has_vid
        self.__has_audio = has_aud
        self.__best_video_stream = best_vid
        self.__best_audio_stream = best_aud
        self.__has_eng_audio = has_eng_aud
        self.__has_eng_subtitles = has_eng_subs
        self.__title = title

    def __repr__(self):
        return json.dumps(self.__info, indent=2)

    def __str__(self):
        return json.dumps(self.__info, indent=2)

    def __init__(self, input=''):
        self.__process(Info.fetch(input))

    def __getattr__(self, attr):
        if self.__info is None:
            return None
        if attr == 'format' or attr == 'streams':
            return self.__info[attr]
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

    def has_english_subtitles(self):
        return self.__has_eng_subtitles


if __name__ == "__main__":
    import sys
    path = sys.argv[1]
    i = Info(path)
    print i
