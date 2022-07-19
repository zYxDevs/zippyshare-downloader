import asyncio
import tqdm
import os
import sys
import time
import logging
from .network import Net

log = logging.getLogger(__name__)

# re.compile('bytes=([0-9]{1,}|)-([0-9]{1,}|)', re.IGNORECASE)

class BaseDownloader:
    def download(self):
        """Download the file"""
        raise NotImplementedError

    def cleanup(self):
        "Do the cleanup, Maybe close the session or the progress bar ? idk."
        raise NotImplementedError

class FileDownloader(BaseDownloader):
    def __init__(self, url, file, progress_bar=True, replace=False, **headers) -> None:
        self.url = url
        self.file = f'{str(file)}.temp'
        self.real_file = file
        self.progress_bar = progress_bar
        self.replace = replace
        self.headers_request = headers
        if headers.get('Range') is not None and self._get_file_size(self.file):
            raise ValueError('"Range" header is not supported while in resume state')

        self._tqdm = None
    
    def _build_progres_bar(self, initial_size, file_sizes, desc='file_sizes'):
        if self.progress_bar:
            kwargs = {
                'initial': initial_size or 0,
                'total': file_sizes,
                'unit': 'B',
                'unit_scale': True
            }

            # Determine ncols progress bar
            length = len(desc)
            if length < 20:
                kwargs.setdefault('ncols', 80)
            elif length > 20 and length < 50:
                kwargs.setdefault('dynamic_ncols', True)
            elif length >= 50:
                desc = f'{desc[:20]}...'
                kwargs.setdefault('ncols', 90)

            kwargs.setdefault('desc', desc)

            self._tqdm = tqdm.tqdm(**kwargs)

    def _update_progress_bar(self, n):
        if self._tqdm:
            self._tqdm.update(n)

    def _get_file_size(self, file):
        return os.path.getsize(file) if os.path.exists(file) else None

    def _parse_headers(self, initial_sizes):
        headers = self.headers_request or {}

        if initial_sizes:
            headers['Range'] = f'bytes={initial_sizes}-'
        return headers

    def download(self):
        initial_file_sizes = self._get_file_size(self.file)

        # Parse headers
        headers = self._parse_headers(initial_file_sizes)

        # Initiate request
        resp = Net.requests.get(self.url, headers=headers, stream=True)

        # Grab the file sizes
        file_sizes = float(resp.headers.get('Content-Length'))

        # If "Range" header request is present
        # Content-Length header response is not same as full size
        if initial_file_sizes:
            file_sizes += initial_file_sizes

        real_file_sizes = self._get_file_size(self.real_file)
        if real_file_sizes and file_sizes == real_file_sizes and not self.replace:
            log.info('File exist and replace is False, cancelling download...')
            return

        # Build the progress bar
        self._build_progres_bar(initial_file_sizes, float(file_sizes))

        # Heavily adapted from https://github.com/choldgraf/download/blob/master/download/download.py#L377-L390
        chunk_size = 2 ** 16
        with open(self.file, 'ab' if initial_file_sizes else 'wb') as writer:
            while True:
                t0 = time.time()
                chunk = resp.raw.read(chunk_size)
                dt = time.time() - t0
                if dt < 0.005:
                    chunk_size *= 2
                elif dt > 0.1 and chunk_size > 2 ** 16:
                    chunk_size = chunk_size // 2
                if not chunk:
                    break
                writer.write(chunk)
                self._update_progress_bar(len(chunk))

        # Delete original file if replace is True and real file is exist
        if real_file_sizes and self.replace:
            os.remove(self.real_file)
        os.rename(self.file, self.real_file)

    def cleanup(self):
        # Close the progress bar
        if self._tqdm:
            self._tqdm.close()

class StdoutDownloader(BaseDownloader):
    def __init__(self, url) -> None:
        self.url = url
    
    def download(self):
        r = Net.requests.get(self.url, stream=True)
        stdout = open(sys.stdout.fileno(), 'wb')
        for content in r.iter_content(1024):
            stdout.write(content)
    
    def cleanup(self):
        pass

class AsyncFileDownloader(BaseDownloader):
    """FileDownloader for async process using aiohttp with resumeable support"""
    def __init__(self, url, file, progress_bar=True, replace=False, **headers) -> None:
        self.url = url
        self.file = f'{str(file)}.temp'
        self.real_file = file
        self.progress_bar = progress_bar
        self.replace = replace
        self.headers_request = headers
        if headers.get('Range') is not None and self._get_file_size(self.file):
            raise ValueError('"Range" header is not supported while in resume state')

        self._tqdm = None
    
    def _build_progres_bar(self, initial_size, file_sizes, desc='file_sizes'):
        if self.progress_bar:
            kwargs = {
                'initial': initial_size or 0,
                'total': file_sizes,
                'unit': 'B',
                'unit_scale': True
            }

            # Determine ncols progress bar
            length = len(desc)
            if length < 20:
                kwargs.setdefault('ncols', 80)
            elif length > 20 and length < 50:
                kwargs.setdefault('dynamic_ncols', True)
            elif length >= 50:
                desc = f'{desc[:20]}...'
                kwargs.setdefault('ncols', 90)

            kwargs.setdefault('desc', desc)

            self._tqdm = tqdm.tqdm(**kwargs)

    def _update_progress_bar(self, n):
        if self._tqdm:
            self._tqdm.update(n)

    def _get_file_size(self, file):
        return os.path.getsize(file) if os.path.exists(file) else None

    def _parse_headers(self, initial_sizes):
        headers = self.headers_request or {}

        if initial_sizes:
            headers['Range'] = f'bytes={initial_sizes}-'
        return headers

    async def download(self):
        initial_file_sizes = self._get_file_size(self.file)

        # Parse headers
        headers = self._parse_headers(initial_file_sizes)

        # Initiate request
        resp = await Net.aiohttp.get(self.url, headers=headers)

        # Grab the file sizes
        file_sizes = float(resp.headers.get('Content-Length'))

        # If "Range" header request is present
        # Content-Length header response is not same as full size
        if initial_file_sizes:
            file_sizes += initial_file_sizes

        real_file_sizes = self._get_file_size(self.real_file)
        if real_file_sizes and file_sizes == real_file_sizes and not self.replace:
            log.info('File exist and replace is False, cancelling download...')
            return

        # Build the progress bar
        self._build_progres_bar(initial_file_sizes, float(file_sizes))

        # Heavily adapted from https://github.com/choldgraf/download/blob/master/download/download.py#L377-L390
        chunk_size = 2 ** 16
        with open(self.file, 'ab' if initial_file_sizes else 'wb') as writer:
            while True:
                t0 = time.time()
                chunk = await resp.content.read(chunk_size)
                dt = time.time() - t0
                if dt < 0.005:
                    chunk_size *= 2
                elif dt > 0.1 and chunk_size > 2 ** 16:
                    chunk_size = chunk_size // 2
                if not chunk:
                    break
                writer.write(chunk)
                self._update_progress_bar(len(chunk))

        # Delete original file if replace is True and real file is exist
        if real_file_sizes and self.replace:
            os.remove(self.real_file)
        os.rename(self.file, self.real_file)

    async def cleanup(self):
        # Close the progress bar
        if self._tqdm:
            self._tqdm.close()

class AsyncFastFileDownloader(BaseDownloader):
    """FAST FileDownloader with 2 connections simultaneously for async process using aiohttp with resumeable support"""
    def __init__(self, url, file, progress_bar=True, replace=False, **headers) -> None:
        self.url = url
        self.real_file = file
        self.progress_bar = progress_bar
        self.replace = replace
        self.headers_request = headers
        if headers.get('Range') is not None:
            raise ValueError('"Range" header is not supported in fast download')

        self._tqdm = None

    def _build_progres_bar(self, initial_size, file_sizes, desc='file_sizes'):
        if self.progress_bar:
            kwargs = {
                'initial': initial_size or 0,
                'total': file_sizes,
                'unit': 'B',
                'unit_scale': True
            }

            # Determine ncols progress bar
            length = len(desc)
            if length < 20:
                kwargs.setdefault('ncols', 80)
            elif length > 20 and length < 50:
                kwargs.setdefault('dynamic_ncols', True)
            elif length >= 50:
                desc = f'{desc[:20]}...'
                kwargs.setdefault('ncols', 90)

            kwargs.setdefault('desc', desc)

            self._tqdm = tqdm.tqdm(**kwargs)

    def _update_progress_bar(self, n):
        if self._tqdm:
            self._tqdm.update(n)

    def _close_progress_bar(self):
        if self._tqdm:
            self._tqdm.close()

    def _get_file_size(self, file):
        return os.path.getsize(file) if os.path.exists(file) else None

    def _parse_headers(self, initial_sizes, end_sizes):
        headers = self.headers_request or {}

        headers['Range'] = f'bytes={int(initial_sizes)}-{int(end_sizes)}'
        return headers

    def _get_temp_file(self, part):
        return f'{str(self.real_file)}.temp.{str(part)}'

    async def _prepare_download(self, part, start_size, end_size):
        file = self._get_temp_file(part)
        initial_file_sizes = self._get_file_size(file) or 0
        pure_temp_file_sizes = initial_file_sizes

        exist = bool(initial_file_sizes)

        # If temp part file exist
        # addition it with start_size
        initial_file_sizes += start_size

        # Parse headers
        headers = self._parse_headers(initial_file_sizes, end_size)

        # initiate request
        resp = await Net.aiohttp.get(self.url, headers=headers)

        return pure_temp_file_sizes, resp, file, exist

    async def _download(self, file, resp, exist):
        # Heavily adapted from https://github.com/choldgraf/download/blob/master/download/download.py#L377-L390
        chunk_size = 2 ** 16
        with open(file, 'ab' if exist else 'wb') as writer:
            while True:
                t0 = time.time()
                chunk = await resp.content.read(chunk_size)
                dt = time.time() - t0
                if dt < 0.005:
                    chunk_size *= 2
                elif dt > 0.1 and chunk_size > 2 ** 16:
                    chunk_size = chunk_size // 2
                if not chunk:
                    break
                writer.write(chunk)
                self._update_progress_bar(len(chunk))

    def _get_parts_size(self, length: int):
        divided = length / 2
        return (
            [0, divided - 1, divided, length]
            if divided.is_integer()
            else [0, divided - 0.5, divided + 0.5, length]
        )

    def _merge_files(self, parts, file_sizes):
        self._close_progress_bar()
        with open(self.real_file, 'wb') as writer:

            self._build_progres_bar(0, file_sizes, 'merging_files')

            for part in parts:
                chunks_size = 2 ** 16
                file = self._get_temp_file(part)
                with open(file, 'rb') as read:
                    while True:
                        chunks = read.read(chunks_size)
                        if not chunks:
                            break
                        writer.write(chunks)
                        self._update_progress_bar(len(chunks))

            self._close_progress_bar()

    async def download(self):
        # Grab the file sizes
        resp = await Net.aiohttp.get(self.url)
        file_sizes = float(resp.headers.get('Content-Length'))
        resp.close()

        # TODO: Add explanation below this.
        parts_size = self._get_parts_size(file_sizes)

        part1_kwargs = {
            'part': 1,
            'start_size': parts_size[0],
            'end_size': parts_size[1]
        }

        part2_kwargs = {
            'part': 2,
            'start_size': parts_size[2],
            'end_size': parts_size[3]
        }

        ifs_p1, resp_p1, f1, e1 = await self._prepare_download(**part1_kwargs)
        ifs_p2, resp_p2, f2, e2 = await self._prepare_download(**part2_kwargs)

        self._build_progres_bar(ifs_p1 + ifs_p2, file_sizes)

        fut1 = asyncio.ensure_future(self._download(
            f1,
            resp_p1,
            e1
        ))
        fut2 = asyncio.ensure_future(self._download(
            f2,
            resp_p2,
            e2
        ))

        await asyncio.gather(fut1, fut2)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._merge_files([1, 2], file_sizes))

        for part in [1,2]:
            os.remove(self._get_temp_file(part))

    async def cleanup(self):
        # Close the progress bar
        if self._tqdm:
            self._tqdm.close()

