# zippyshare-downloader
# utils.py

import re
import os
import math
import tarfile
import zipfile
import logging
from pathlib import Path
from .errors import InvalidURL

log = logging.getLogger(__name__)

ALLOWED_NAMES = {
    k: v for k, v in math.__dict__.items() if not k.startswith("__")
}

# Credit for the evaluate() method: Leodanis Pozo Ramos  https://realpython.com/python-eval-function/
def evaluate(expression):
    """Evaluate a math expression."""

    # Compile the expression
    code = compile(expression, "<string>", "eval")

    # Validate allowed names
    for name in code.co_names:
        if name not in ALLOWED_NAMES:
                raise NameError("The use of '%s' is not allowed. Expression used: %s" % (name, expression))

    return eval(code, {"__builtins__": {}}, ALLOWED_NAMES)

REGEXS_ZIPPYSHARE_URL = [
    # View zippyshare url
    r'https:\/\/www[0-9]{1,3}\.zippyshare\.com\/v\/[0-9A-Za-z]{8}\/file\.html',
    r'https:\/\/www\.zippyshare\.com\/v\/[0-9A-Za-z]{8}\/file\.html',
    # Download Zippyshare url
    r'https:\/\/www[0-9]{1,3}\.zippyshare\.com\/d\/[0-9A-Za-z]{8}\/',
    r'https:\/\/www\.zippyshare\.com\/d\/[0-9A-Za-z]{8}\/',
]

def check_valid_zippyshare_url(url):
    """Check if given url is valid Zippyshare url"""
    for regex in REGEXS_ZIPPYSHARE_URL:
        if re.match(regex, url) is not None:
            return url
    raise InvalidURL('"%s" is not a zippyshare url' % (url))

# TODO: Document this !
def getStartandEndvalue(value: str, sub: str, second_sub=None):
    v = value[value.find(sub)+1:]
    return v[:v.find(second_sub)] if second_sub is not None else v[:v.find(sub)]

def extract_archived_file(file) -> None:
    """Extract all files from supported archive file (zip and tar)."""
    # Extracting tar files
    log.debug('Opening "%s" in tar archive format' % file)
    try:
        tar = tarfile.open(file, 'r')
    except tarfile.ReadError as e:
        log.debug('Failed to open "%s" in tar format, %s: %s' % (
            file,
            e.__class__.__name__,
            str(e)
        ))
    else:
        log.info('Extracting all files in "%s"' % file)
        tar.extractall(Path(file).parent)
        tar.close()
        return
    # Extracting zip files
    log.debug('Opening "%s" in zip archive format' % file)
    is_zip = zipfile.is_zipfile(file)
    if not is_zip:
        log.debug('File "%s" is not zip format' % file)
        return
    try:
        zip_file = zipfile.ZipFile(file)
    except zipfile.BadZipFile as e:
        log.debug('Failed to open "%s" in zip format, %s: %s' % (
            file,
            e.__class__.__name__,
            str(e)
        ))
    else:
        log.info('Extracting all files in "%s"' % file)
        zip_file.extractall(Path(file).parent)
        zip_file.close()


def archive_zip(downloaded_files, name):
    path = list(downloaded_files.values())[0]
    zip_path = (path.parent / name)
    with zipfile.ZipFile(zip_path, 'w') as zip_writer:
        for file, path in downloaded_files.items():
            log.debug('Writing "%s" to "%s"' % (
                path,
                zip_path
            ))
            zip_writer.write(path)
            os.remove(path)

def build_pretty_list_log(iterable, word, spacing=4):
    word = '%s = [\n' % word
    for context in iterable:

        # Build spacing
        for _ in range(spacing):
            word += ' '
        
        # Build name file
        word += '"%s",\n' % context
    
    word += ']'
    return word

