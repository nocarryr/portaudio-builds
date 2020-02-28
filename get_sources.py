#! /usr/bin/env python3

from loguru import logger
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import shutil
import argparse

import requests

BASE_PATH = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_PATH / 'tmp'
SRC_DIR = BASE_PATH / 'src'

PORTAUDIO_URL = 'https://github.com/nocarryr/portaudio/archive/pa_stable_v190600_20161030.zip'
ASIO_URL = 'https://www.steinberg.net/asiosdk'


class Cwd(object):
    def __init__(self, path: Path):
        self.path = path
        self.prev_path = None
    def __enter__(self):
        logger.debug(f'Entering "{self}"')
        assert self.prev_path is None
        self.prev_path = Path(os.getcwd())
        os.chdir(self.path)
        return self.path
    def __exit__(self, *args):
        logger.debug(f'Leaving "{self}"')
        os.chdir(self.prev_path)
        self.prev_path = None
    def __repr__(self):
        return f'<{self.__class__.__name__}: "{self}">'
    def __str__(self):
        return str(self.path)


class TempDir(object):
    def __init__(self, autoremove=True):
        self.root = None
        self.autoremove = autoremove
        self._acquire_count = 0
    def open(self):
        assert self.root is None
        p = tempfile.mkdtemp()
        self.root = Path(p)
    def close(self):
        if self.autoremove:
            shutil.rmtree(str(self.root))
        self.root = None
    def __enter__(self):
        if self._acquire_count == 0:
            self.open()
        self._acquire_count += 1
        return self.root
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._acquire_count -= 1
        if self._acquire_count == 0 and exc_type is None:
            self.close()

def unpack(archive: Path, root_dir: Path):
    contents = []
    with TempDir() as tmp:
        logger.debug(f'Unpacking {archive} to {tmp}')
        shutil.unpack_archive(archive, tmp)
        for p in tmp.iterdir():
            new_p = root_dir / p.name
            logger.debug(f'Moving {p} to {new_p}')
            p.rename(new_p)
            contents.append(new_p)
    return contents

def download(url: str, root_dir: Path):
    r = requests.get(url, stream=True)
    assert r.ok
    filename = r.url.split('/')[-1]
    filename = root_dir / filename
    logger.debug(f'Download filename: {filename}')

    with filename.open('wb') as fd:
        for chunk in r.iter_content(chunk_size=128):
            fd.write(chunk)
    return filename

def get_asiosdk(root: Path, url=ASIO_URL, download_dir=DOWNLOAD_DIR):
    logger.info(f'Downloading ASIOSDK to {root}')
    zip_file = download(url, download_dir)
    extracted = unpack(zip_file, root)
    assert len(extracted) == 1
    sdk_dir = extracted[0]
    logger.info(f'ASIOSDK source: {sdk_dir}')
    return sdk_dir

def get_portaudio_source(root: Path, url=PORTAUDIO_URL, download_dir=DOWNLOAD_DIR):
    logger.info(f'Downloading PortAudio to {root}')
    zip_file = download(url, download_dir)
    if zip_file.suffix != '.zip':
        new_fn = zip_file.with_suffix('.zip')
        logger.debug(f'Renaming {zip_file} to {new_fn}')
        zip_file.rename(new_fn)
        zip_file = new_fn
    extracted = unpack(zip_file, root)
    assert len(extracted) == 1
    src_dir = extracted[0]
    if src_dir.name != 'portaudio':
        new_p = src_dir.with_name('portaudio')
        logger.debug(f'Renaming {src_dir} to {new_p}')
        src_dir.rename(new_p)
        src_dir = new_p
    logger.info(f'PortAudio source: {src_dir}')
    return src_dir

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--download-dir', dest='download_dir', default=str(DOWNLOAD_DIR))
    p.add_argument('--src-dir', dest='src_dir', default=str(SRC_DIR))
    p.add_argument('--asio-url', dest='asio_url', default=ASIO_URL)
    p.add_argument('--portaudio-url', dest='portaudio_url', default=PORTAUDIO_URL)
    p.add_argument('--clean', dest='clean', action='store_true',
        help='Remove previously downloaded files before running',
    )

    args = p.parse_args()
    args.download_dir = Path(args.download_dir)
    args.src_dir = Path(args.src_dir)

    if args.clean:
        if args.download_dir.exists():
            shutil.rmtree(args.download_dir)
        if args.src_dir.exists():
            shutil.rmtree(args.src_dir)

    args.download_dir.mkdir(exist_ok=True, parents=True)
    args.src_dir.mkdir(exist_ok=True, parents=True)
    logger.debug(f'download: {args.download_dir!r}')
    logger.debug(f'src: {args.src_dir!r}')

    pa_dir = get_portaudio_source(args.src_dir, args.portaudio_url, args.download_dir)
    assert pa_dir.name == 'portaudio'

    asio_dir_orig = get_asiosdk(args.src_dir, args.asio_url, args.download_dir)
    asio_dir = asio_dir_orig.parent / 'ASIOSDK'
    logger.info(f'Move {asio_dir_orig} to {asio_dir}')
    asio_dir_orig.rename(asio_dir)

    return [asio_dir, pa_dir]

if __name__ == '__main__':
    try:
        sources = main()
    except Exception as exc:
        logger.exception(exc)
        raise
    logger.success('_SOURCES_ : {}'.format([str(p) for p in sources]))
