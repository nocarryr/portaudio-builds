#! /usr/bin/env python3

from loguru import logger
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import shutil
import argparse

def copy(src, dst):
    logger.debug(f'cp {src} -> {dst}')
    shutil.copy2(src, dst)

def copy_bin(args):
    logger.info(f'copying bin files to {args.bin_dest}')

    if args.platform == 'Win32':
        arch = 'x86'
        dll = f'portaudio_{arch}.dll'
    else:
        arch = 'x64'
        dll = 'portaudio.dll'

    source_filenames = [
        dll,
        f'portaudio_{arch}.exp',
        f'portaudio_{arch}.lib',
        f'portaudio_{arch}.pdb',
    ]

    args.bin_dest.mkdir(exist_ok=True, parents=True)

    for fn in source_filenames:
        src_p = args.build_src / fn
        copy(src_p, args.bin_dest)

def copy_include(args):
    logger.info(f'copying includes to {args.include_dest}')
    incl_src = args.src_root / 'include'
    args.include_dest.mkdir(exist_ok=True, parents=True)

    for p in incl_src.glob('*.h'):
        copy(p, args.include_dest)

def copy_logs(args):
    logger.info(f'copying build logs to {args.log_dest}')
    log_src = args.build_src / 'portaudio.tlog'
    args.log_dest.mkdir(exist_ok=True, parents=True)

    for p in log_src.iterdir():
        copy(p, args.log_dest)


def main():
    p = argparse.ArgumentParser()
    path_keys = ['src_root', 'pkg_dest', 'log_dest']
    all_keys = set(path_keys) | {'config', 'platform'}
    for key in all_keys:
        arg_name = '--{}'.format('-'.join(key.split('_')))
        p.add_argument(arg_name, dest=key, required=True)

    args = p.parse_args()

    for key in path_keys:
        p = Path(getattr(args, key))
        setattr(args, key, p)

    args.build_src = args.src_root / 'build' / 'msvc' / args.platform / args.config
    args.bin_dest = args.pkg_dest / 'bin'
    args.include_dest = args.pkg_dest / 'include'

    args.pkg_dest.mkdir()
    license = args.src_root / 'LICENSE.txt'
    copy(license, args.pkg_dest)

    copy_bin(args)
    copy_include(args)
    copy_logs(args)

if __name__ == '__main__':
    main()
