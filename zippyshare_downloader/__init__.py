# zippyshare-downloader
# __init__.py

"""
zippyshare-downloader

Download file from zippyshare directly from python
"""

__VERSION__ = 'v0.0.19'

from zippyshare_downloader.utils import getStartandEndvalue
from bs4 import BeautifulSoup
from download import download as dl
from .utils import check_valid_zippyshare_url
from .errors import ParserError, InvalidURL
from .patterns import PATTERNS
import requests
import os
import urllib.parse

class Zippyshare:

    def __init__(self, verbose=True, progress_bar=True, replace=True):
        self._verbose = verbose
        self._progress_bar = progress_bar
        self._replace = replace
    
    def _logger_info(self, message):
        if self._verbose:
            print('[INFO] %s' % (message))
        else:
            return

    def _logger_warn(self, message):
        if self._verbose:
            print('[WARN] %s' % (message))
        else:
            return

    def _logger_error(self, message):
        if self._verbose:
            print('[ERROR] %s' % (message))
        else:
            return

    def _get_url(self, u, r: requests.Request):
        self._logger_info('Getting Download URL from "%s"' % (u))
        for pattern in PATTERNS:
            try:
                result = pattern(r.text, u)
            except Exception:
                continue
            else:
                return result
        raise ParserError('all patterns parser is failed to get Download url')

    def _get_absolute_filename(self, info):
        r = requests.get(info['download_url'], stream=True)
        new_namefile = r.headers['Content-Disposition'].replace('attachment; filename*=UTF-8\'\'', '')
        info['name_file'] = urllib.parse.unquote(new_namefile)
        r.close()
        return info

    def _finalization_info(self, info):
        # Fix https://github.com/mansuf/zippyshare-downloader/issues/4
        if '<img alt="file name" src="/fileName?key' in info['name_file']:
            self._logger_warn('Filename is in image not in text, running additional fetch...')
            return self._get_absolute_filename(info)

        # Fix https://github.com/mansuf/zippyshare-downloader/issues/5
        elif len(info['name_file']) > 70:
            self._logger_warn('Filename is too long, running additional fetch...')
            return self._get_absolute_filename(info)
        else:
            return info


    def _get_info(self, u, r: requests.Request):
        self._logger_info('Parsing info')
        if 'File has expired and does not exist anymore on this server' in r.text:
            raise FileNotFoundError('File has expired and does not exist anymore')
        elif 'File does not exist on this server' in r.text:
            raise FileNotFoundError('File does not exist on this server')
        parser = BeautifulSoup(r.text, 'html.parser')
        list_infos = []
        for element in parser.find_all('font'):
            str_element = str(element)
            # Size file, Uploaded
            if str_element.startswith('<font style="line-height:18px; font-size: 13px;">'):
                list_infos.append(element)
            # Name file
            elif str_element.startswith('<font style="line-height:22px; font-size: 14px;">'):
                list_infos.append(element)
            # Name file
            elif str_element.startswith('<font style="line-height:20px; font-size: 14px;">'):
                list_infos.append(element)
        return self._finalization_info({
                'name_file': list_infos[0].decode_contents(),
                'size': list_infos[1].decode_contents(),
                'date_upload': list_infos[2].decode_contents(),
                'download_url': self._get_url(u, r)
            })

    def _request_get(self, url):
        self._logger_info('Fetching URL "%s"' % (url))
        return requests.get(url)

    def _extract_info(self, url, download=True, folder=None, custom_filename=None):
        try:
            check_valid_zippyshare_url(url)
        except InvalidURL as e:
            self._logger_error(str(e))
            raise e
        r = self._request_get(url)
        if r.status_code != 200:
            self._logger_error('Zippyshare send %s code' % (r.status_code))
        info = self._get_info(url, r)
        if download:
            self._logger_info('Downloading "%s"' % (info['name_file']))
            if folder is not None and isinstance(folder, str):
                self._logger_info(f'Using directory "{os.path.join(os.getcwd(), folder)}"')
                if custom_filename is not None and isinstance(custom_filename, str):
                    self._logger_info('Using custom filename "%s"' % (custom_filename))
                    path = os.path.join(os.getcwd(), folder, custom_filename)
                else:
                    path = os.path.join(os.getcwd(), folder, info['name_file'])
            else:
                path = info['name_file']
            dl(
                info['download_url'],
                path,
                progressbar=self._progress_bar,
                verbose=self._verbose,
                replace=self._replace
            )
            return info
        else:
            return info
        
    def _download(self, urls, folder=None):
        for url in urls:
            try:
                check_valid_zippyshare_url(url)
            except InvalidURL as e:
                self._logger_error(str(e))
                raise e
            r = self._request_get(url)
            if r.status_code != 200:
                self._logger_error('Zippyshare send %s code' % (r.status_code))
            info = self._get_info(url, r)
            self._logger_info('Downloading "%s"' % (info['name_file']))
            if folder is not None and isinstance(folder, str):
                self._logger_info(f'Using directory "{os.path.join(os.getcwd(), folder)}"')
                path = os.path.join(os.getcwd(), folder, info['name_file'])
            else:
                path = info['name_file']
            dl(
                info['download_url'],
                path,
                progressbar=self._progress_bar,
                verbose=self._verbose,
                replace=self._replace
            )

    def download(self, urls: list or tuple, folder=None):
        if isinstance(urls, list) or isinstance(urls, tuple):
            pass
        else:
            raise InvalidURL('urls expecting list or tuple type, got %s' % (type(urls)))
        self._download(urls, folder=folder)

    def extract_info(self, url: str, download=True, folder=None, custom_filename=None):
        return self._extract_info(
            url,
            download=download,
            folder=folder,
            custom_filename=custom_filename
        )


