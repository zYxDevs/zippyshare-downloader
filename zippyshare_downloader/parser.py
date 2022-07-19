# zippyshare-downloader
# parser.py

import logging
import urllib.parse
from bs4 import BeautifulSoup
from typing import Dict
from .patterns import PATTERNS
from .errors import ParserError
from .network import Net

log = logging.getLogger(__name__)

def parse_info(url, body_html) -> Dict[str, str]:
    """
    Parse required informations from request Zippyshare url.
    """
    parser = BeautifulSoup(body_html, 'html.parser')
    list_infos = []
    log.debug('Getting Name file, size, date upload.')
    for element in parser.find_all('font'):
        str_element = str(element)
        # Size file, Uploaded
        if (
            str_element.startswith(
                '<font style="line-height:18px; font-size: 13px;">'
            )
            or str_element.startswith(
                '<font style="line-height:22px; font-size: 14px;">'
            )
            or str_element.startswith(
                '<font style="line-height:20px; font-size: 14px;">'
            )
        ):
            list_infos.append(element)
    log.debug('Getting download url.')
    for pattern in PATTERNS:
        try:
            download_url = pattern(body_html, url)
        except Exception as e:
            log.debug(
                f'{pattern.__name__} failed to get download url, {e.__class__.__name__}: {str(e)}'
            )

            continue
        else:
            log.debug(f'{pattern.__name__} success to get download url')
            return {
                "name_file": list_infos[0].decode_contents(),
                "size": list_infos[1].decode_contents(),
                "date_upload": list_infos[2].decode_contents(),
                'url': url,
                'download_url': download_url
            }
    log.exception('all patterns parser failed to get required informations')
    raise ParserError('all patterns parser is failed to get required informations')

def _get_absolute_filename(info):
    r = Net.requests.get(info['download_url'], stream=True)
    new_namefile = r.headers['Content-Disposition'].replace('attachment; filename*=UTF-8\'\'', '')
    info['name_file'] = urllib.parse.unquote(new_namefile)
    r.close()
    return info

async def _get_absolute_filename_coro(info):
    resp = await Net.aiohttp.get(info['download_url'])
    new_namefile = resp.headers['Content-Disposition'].replace('attachment; filename*=UTF-8\'\'', '')
    info['name_file'] = urllib.parse.unquote(new_namefile)
    resp.close()
    return info

async def __dummy_return(info):
    return info

def finalization_info(info, _async=False) -> Dict[str, str]:
    """
    Fix if required informations contains invalid info.
    """
    error = False
    # Fix https://github.com/mansuf/zippyshare-downloader/issues/4
    if '<img alt="file name" src="/fileName?key' in info['name_file']:
        log.warning('Filename is in image not in text, running additional fetch...')
        error = True

    # Fix https://github.com/mansuf/zippyshare-downloader/issues/5
    elif len(info['name_file']) > 70:
        log.warning('Filename is too long, running additional fetch...')
        error = True

    if error:
        return (
            _get_absolute_filename_coro(info)
            if _async
            else _get_absolute_filename(info)
        )

    return __dummy_return(info) if _async else info
