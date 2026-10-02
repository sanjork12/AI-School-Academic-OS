"""Exclusive atomic experiment writes. Reports are immutable and content addressed."""
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from ..ai_authoring.brief import serial
from ..ai_authoring.service import contains_secret


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value, identical_ok=False):
    path = Path(path)
    data = serial(value).encode('utf-8')
    if contains_secret(data.decode()): raise ValueError('Secret-like experiment output withheld')
    path.parent.mkdir(parents=True, exist_ok=True)
    if identical_ok and path.exists():
        if path.read_bytes() != data: raise ValueError('Existing artifact differs')
        return path
    with NamedTemporaryFile(dir=path.parent, prefix='.pending-', delete=False) as f:
        temporary = Path(f.name)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    try:
        os.link(temporary, path)
    finally:
        temporary.unlink()
    return path


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def checked_member(directory, name, expected):
    path = Path(directory) / name
    if Path(name).name != name or path.is_symlink(): raise ValueError('Invalid artifact path')
    if file_hash(path) != expected: raise ValueError('Experiment artifact digest mismatch')
    return path
