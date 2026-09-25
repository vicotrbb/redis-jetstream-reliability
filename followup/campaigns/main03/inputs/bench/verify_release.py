"""Verify a supplied release without broker access or third-party Python packages."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile

from checksums import paths, sha256


def parse_manifest(raw):
    entries={}
    for line in raw.decode('utf-8').splitlines():
        digest,name=line.split('  ',1)
        path=PurePosixPath(name)
        if (not re.fullmatch(r'[0-9a-f]{64}',digest) or path.is_absolute()
                or '..' in path.parts or '\\' in name or name!=path.as_posix()
                or name in entries):
            raise ValueError('Invalid or duplicate manifest entry')
        entries[name]=digest
    if not entries:
        raise ValueError('Empty manifest')
    return entries


def check_core(read, entries):
    release=json.loads(read('release/manifest.json'))
    metadata=json.loads(read('release/metadata.json'))
    if release['version']!=metadata['version']:
        raise ValueError('Release metadata version mismatch')
    cff=read('CITATION.cff').decode()
    if f"version: {release['version']}\n" not in cff:
        raise ValueError('Citation version mismatch')
    for name,expected in release['core_sha256'].items():
        # Every entry was already checked against bytes before this function.
        if entries.get(name)!=expected:
            raise ValueError(f'Core identity mismatch: {name}')
    for name in ('LICENSE.md','LICENSES/CC-BY-4.0.txt','LICENSES/MIT.txt',
                 'paper/main.log','paper/main.bbl','data/derived/visual-review.json'):
        if name not in entries:
            raise ValueError(f'Missing release requirement: {name}')
    return {'version':release['version'],'files_verified':len(entries),
            'pdf_sha256':release['core_sha256']['output/pdf/redis-jetstream-reliability.pdf']}


def verify_directory(root):
    entries=parse_manifest((root/'SHA256SUMS').read_bytes())
    actual={p.relative_to(root).as_posix() for p in paths(root)}
    if actual!=set(entries):
        raise ValueError(f'Delivered file set mismatch: missing={sorted(set(entries)-actual)}, extra={sorted(actual-set(entries))}')
    for name,expected in entries.items():
        if sha256(root/name)!=expected:
            raise ValueError(f'Content changed: {name}')
    return check_core(lambda name:(root/name).read_bytes(),entries)


def verify_archive(archive):
    with tarfile.open(archive,'r|gz') as tf:
        names=[]; actual={}; retained={}
        keep={'SHA256SUMS','release/manifest.json','release/metadata.json','CITATION.cff'}
        for member in tf:
            if not member.isfile() or member.name in actual:
                raise ValueError('Duplicate or non-regular archive member')
            names.append(member.name)
            relative=member.name.partition('/')[2]
            stream=tf.extractfile(member)
            h=hashlib.sha256(); chunks=[]
            if relative in keep and member.size>8*1024*1024:
                raise ValueError('Unexpectedly large release metadata')
            with stream:
                for block in iter(lambda:stream.read(1<<20),b''):
                    h.update(block)
                    if relative in keep:chunks.append(block)
            actual[member.name]=h.hexdigest()
            if relative in keep:retained[member.name]=b''.join(chunks)
        roots={PurePosixPath(name).parts[0] for name in names}
        if len(roots)!=1:
            raise ValueError('Archive must have one top-level directory')
        prefix=roots.pop()+'/'
        def read(name):
            return retained[prefix+name]
        entries=parse_manifest(read('SHA256SUMS'))
        if set(names)!={prefix+name for name in entries}|{prefix+'SHA256SUMS'}:
            raise ValueError('Archive contains missing or unlisted members')
        for name,expected in entries.items():
            if actual[prefix+name]!=expected:raise ValueError(f'Archive content changed: {name}')
        result=check_core(read,entries)
        if prefix!=f"redis-jetstream-reliability-v{result['version']}/":
            raise ValueError('Archive directory and version disagree')
        result['archive_sha256']=sha256(archive)
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--directory',type=Path)
    group.add_argument('--archive',type=Path)
    args=parser.parse_args()
    result=verify_directory(args.directory) if args.directory else verify_archive(args.archive)
    print(json.dumps({'status':'pass',**result},indent=2))


if __name__=='__main__':main()
