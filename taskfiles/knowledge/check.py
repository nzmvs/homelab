#!/usr/bin/env python3
"""Check this repository's compact OKF v0.2 profile, not arbitrary OKF bundles.

Optional OKF fields and intact links are local requirements here. No network,
secret decryption or live-state verification is performed.
"""

from datetime import datetime
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

import yaml

REPO = Path(__file__).resolve().parents[2]
BUNDLE = REPO / 'knowledge'
LINK = re.compile(r'\[[^\]]+\]\(([^\s)]+)\)')


def read_document(path):
    text = path.read_text(encoding='utf-8')
    match = re.match(r'\A---\n(.*?)\n---\n(.*)\Z', text, re.S)
    if not match:
        raise ValueError(f'{path.name}: missing or unterminated frontmatter')
    metadata = yaml.safe_load(match[1])
    if not isinstance(metadata, dict):
        raise ValueError(f'{path.name}: frontmatter must be a mapping')
    return metadata, match[2]


def target(path, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{path.name}: empty link/source')
    url = urlsplit(value)
    if url.scheme or url.netloc:
        return None
    base = BUNDLE if url.path.startswith('/') else path.parent
    resolved = (base / unquote(url.path).lstrip('/')).resolve() if url.path else path
    if not resolved.is_relative_to(REPO) or not resolved.is_file():
        raise ValueError(f'{path.name}: missing/outside-repository target {value}')
    if url.fragment:
        headings = re.findall(r'^#{1,6} +(.+)$', resolved.read_text(encoding='utf-8'), re.M)
        anchors = {re.sub(r'[^\w -]', '', h.lower()).replace(' ', '-') for h in headings}
        if unquote(url.fragment) not in anchors:
            raise ValueError(f'{path.name}: missing heading {value}')
    return resolved


def check():
    index = BUNDLE / 'index.md'
    metadata, listing = read_document(index)
    if metadata != {'okf_version': '0.2'}:
        raise ValueError('index.md: expected only okf_version: "0.2"')
    concepts = set(BUNDLE.glob('*.md')) - {index}
    if not concepts or set(BUNDLE.rglob('*.md')) != concepts | {index}:
        raise ValueError('Expected a flat bundle with index.md and concept documents')
    if BUNDLE / 'log.md' in concepts:
        raise ValueError('Use Git and the central worklog for history, not a concept named log.md')
    listed = {target(index, url) for url in LINK.findall(listing)}
    if listed & concepts != concepts:
        raise ValueError('index.md: every concept must be listed')
    total = 0
    for path in sorted(concepts):
        metadata, body = read_document(path)
        for key in ('type', 'title', 'description'):
            if not isinstance(metadata.get(key), str) or not metadata[key].strip():
                raise ValueError(f'{path.name}: expected non-empty {key}')
        generated = metadata.get('generated', {})
        actor = generated.get('by') if isinstance(generated, dict) else None
        if not isinstance(actor, str) or not re.fullmatch(
                r'(?:[^/\s:]+/[^/\s]+|(?:human|process):\S+)', actor):
            raise ValueError(f'{path.name}: expected producer/version, human:id or process:id in generated.by')
        timestamp = datetime.fromisoformat(str(generated.get('at', '')))
        if timestamp.tzinfo is None:
            raise ValueError(f'{path.name}: generated.at needs a UTC offset')
        sources = metadata.get('sources')
        if not isinstance(sources, list) or not sources:
            raise ValueError(f'{path.name}: expected source provenance')
        for source in sources:
            if not isinstance(source, dict):
                raise ValueError(f'{path.name}: source must be a mapping')
            target(path, source.get('resource'))
        linked = {target(path, url) for url in LINK.findall(body)}
        if not (linked & (concepts - {path})):
            raise ValueError(f'{path.name}: expected a relationship to another concept')
        entry = f'[{metadata["title"]}]({path.name}) - {metadata["description"]}'
        if entry not in listing:
            raise ValueError(f'{path.name}: index title/description differs')
        words = len(body.split())
        if words > 100:
            raise ValueError(f'{path.name}: {words} body words exceeds the local 100-word limit')
        total += words
    print(f'Knowledge OK: {len(concepts)} concepts, {total} body words; metadata, navigation and local sources resolve.')


if __name__ == '__main__':
    try:
        check()
    except (ValueError, OSError, yaml.YAMLError) as error:
        sys.exit(str(error))
