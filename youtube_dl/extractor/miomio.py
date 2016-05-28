# coding: utf-8
from __future__ import unicode_literals

import random

from .common import InfoExtractor
from ..compat import compat_urlparse
from ..utils import (
    xpath_text,
    int_or_none,
    ExtractorError,
    sanitized_Request,
)


class MioMioIE(InfoExtractor):
    IE_NAME = 'miomio.tv'
    _VALID_URL = r'https?://(?:www\.)?miomio\.tv/watch/cc(?P<id>[0-9]+)'
    _TESTS = [{
        # "type=video" in flashvars
        'url': 'http://www.miomio.tv/watch/cc88912/',
        'md5': '317a5f7f6b544ce8419b784ca8edae65',
        'info_dict': {
            'id': '88912',
            'ext': 'flv',
            'title': '【SKY】字幕 铠武昭和VS平成 假面骑士大战FEAT战队 魔星字幕组 字幕',
            'duration': 5923,
        },
    }, {
        'url': 'http://www.miomio.tv/watch/cc184024/',
        'info_dict': {
            'id': '43729',
            'title': '《动漫同人插画绘制》',
        },
        'playlist_mincount': 86,
        'skip': 'This video takes time too long for retrieving the URL',
    }, {
        'url': 'http://www.miomio.tv/watch/cc173113/',
        'info_dict': {
            'id': '173113',
            'title': 'The New Macbook 2015 上手试玩与简评'
        },
        'playlist_mincount': 2,
    }, {
        # new 'h5' player
        'url': 'http://www.miomio.tv/watch/cc273295/',
        'md5': '',
        'info_dict': {
            'id': '273295',
            'ext': 'mp4',
            'title': 'アウト×デラックス 20160526',
        },
        'params': {
            # intermittent HTTP 500
            'skip_download': True,
        },
    }]

    def _extract_mioplayer(self, webpage, video_id, title, http_headers):
        xml_config = self._search_regex(
            r'flashvars="type=(?:sina|video)&amp;(.+?)&amp;',
            webpage, 'xml config')

        # skipping the following page causes lags and eventually connection drop-outs
        self._request_webpage(
            'http://www.miomio.tv/mioplayer/mioplayerconfigfiles/xml.php?id=%s&r=%s' % (id, random.randint(100, 999)),
            video_id)

        vid_config_request = sanitized_Request(
            'http://www.miomio.tv/mioplayer/mioplayerconfigfiles/sina.php?{0}'.format(xml_config),
            headers=http_headers)

        # the following xml contains the actual configuration information on the video file(s)
        vid_config = self._download_xml(vid_config_request, video_id)

        if not int_or_none(xpath_text(vid_config, 'timelength')):
            raise ExtractorError('Unable to load videos!', expected=True)

        entries = []
        for f in vid_config.findall('./durl'):
            segment_url = xpath_text(f, 'url', 'video url')
            if not segment_url:
                continue
            order = xpath_text(f, 'order', 'order')
            segment_id = video_id
            segment_title = title
            if order:
                segment_id += '-%s' % order
                segment_title += ' part %s' % order
            entries.append({
                'id': segment_id,
                'url': segment_url,
                'title': segment_title,
                'duration': int_or_none(xpath_text(f, 'length', 'duration'), 1000),
                'http_headers': http_headers,
            })

        return entries

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_meta(
            'description', webpage, 'title', fatal=True)

        mioplayer_path = self._search_regex(
            r'src="(/mioplayer(?:_h5)?/[^"]+)"', webpage, 'ref_path')

        if '_h5' in mioplayer_path:
            player_url = compat_urlparse.urljoin(url, mioplayer_path)
            player_webpage = self._download_webpage(
                player_url, video_id,
                note='Downloading player webpage', headers={'Referer': url})
            entries = self._parse_html5_media_entries(player_url, player_webpage)
            http_headers = {'Referer': player_url}
        else:
            http_headers = {'Referer': 'http://www.miomio.tv%s' % mioplayer_path}
            entries = self._extract_mioplayer(webpage, video_id, title, http_headers)

        if len(entries) == 1:
            segment = entries[0]
            segment['id'] = video_id
            segment['title'] = title
            segment['http_headers'] = http_headers
            return segment

        return {
            '_type': 'multi_video',
            'id': video_id,
            'entries': entries,
            'title': title,
            'http_headers': http_headers,
        }
