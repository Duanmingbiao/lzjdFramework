"""工程路径与文本编码约定。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def manifest():
    return json.loads((ROOT / 'project.json').read_text(encoding='utf-8'))


def write_mq(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'\xef\xbb\xbf' + text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n').encode('utf-8'))
