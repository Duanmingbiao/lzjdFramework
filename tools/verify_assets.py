"""Check profile provenance, module encoding and UI keys."""
import json,re
from project_paths import ROOT,manifest

cfg=manifest()
report=json.loads((ROOT/'reference/图色来源.json').read_text('utf-8'))
assert len(report['profiles'])==27
assert len({p['name'] for p in report['profiles']})==27
for r in report['profiles']:
    v=r['definition']
    assert len(v)==8 and 0<v[7]<=1
    assert re.fullmatch(r'[A-Fa-f0-9]{6}(?:-[A-Fa-f0-9]{6})?',v[4])
    assert isinstance(v[5],str) and '|' in v[5]
ui=(ROOT/cfg['ui']).read_text('utf-8-sig')
for key in ['操作超时秒数','登录超时秒数','邮件间隔秒数','立即检查邮件']:
    assert '名称:"'+key+'"' in ui
for path in [ROOT/cfg['entry'],ROOT/cfg['ui'],ROOT/cfg['probe']]+[ROOT/n for n in cfg['modules']]:
    b=path.read_bytes()
    assert b.startswith(b'\xef\xbb\xbf'),str(path)+' missing BOM'
    assert b'\n' not in b.replace(b'\r\n',b''),str(path)+' expected CRLF'
print('27 original color profiles, 4 UI keys and source encoding checked; UI compatibility needs device testing.')
