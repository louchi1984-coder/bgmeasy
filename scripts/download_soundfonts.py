#!/usr/bin/env python3
"""Install the pinned, separately licensed release soundfonts into this checkout."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(stream):
    result = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024*1024), b''):
        result.update(chunk)
    return result.hexdigest()


def install(archive, destination, spec):
    with Path(archive).open('rb') as stream:
        if digest(stream) != spec['sha256']:
            raise ValueError('Archive SHA-256 mismatch; nothing installed')
    base = Path(destination).resolve()
    with zipfile.ZipFile(archive) as bundle:
        entries = [info for info in bundle.infolist() if not info.is_dir()]
        if len(entries) != len(spec['files']) or {i.filename for i in entries} != set(spec['files']):
            raise ValueError('Archive file list does not match the release manifest')
        for info in entries:
            relative = PurePosixPath(info.filename)
            if relative.is_absolute() or '..' in relative.parts or '\\' in info.filename or relative.parts[0] != 'soundfonts' or stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError('Unsafe archive path')
            target = base.joinpath(*relative.parts)
            if not target.resolve().is_relative_to(base):
                raise ValueError('Destination resolves outside this checkout')
            with bundle.open(info) as stream:
                if digest(stream) != spec['files'][info.filename]:
                    raise ValueError('File SHA-256 mismatch: '+info.filename)
            if target.exists():
                with target.open('rb') as stream:
                    if digest(stream) != spec['files'][info.filename]:
                        raise ValueError('Existing file differs; use a clean checkout: '+info.filename)
        # Preflight checks above finish before writing any files.
        for info in entries:
            target = base.joinpath(*PurePosixPath(info.filename).parts)
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(info) as source, target.open('wb') as output:
                    shutil.copyfileobj(source, output)
    return len(entries)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Use a previously downloaded release ZIP')
    args = parser.parse_args()
    spec = json.loads((ROOT/'references/soundfont-bundle.json').read_text(encoding='utf-8'))
    try:
        with tempfile.TemporaryDirectory() as directory:
            archive = args.archive
            if archive is None:
                archive = Path(directory)/'soundfonts.zip'
                print('Downloading', spec['url'], flush=True)
                with urllib.request.urlopen(spec['url'], timeout=120) as source, archive.open('wb') as output:
                    shutil.copyfileobj(source, output)
            count = install(archive, ROOT, spec)
        print(f'Verified {count} soundfont files. DSK is not included.')
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        parser.exit(1, f'Soundfont setup failed: {error}\n')


if __name__ == '__main__':
    main()
