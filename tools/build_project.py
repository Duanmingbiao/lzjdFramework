"""Build standalone MQ/UIP in UTF-8 and GBK; does not invoke the assistant compiler."""
from pathlib import Path
import hashlib,json
from project_paths import ROOT, manifest, write_mq

def main():
    cfg=manifest()
    paths=[cfg['entry']]+cfg['modules']
    actual={p.relative_to(ROOT).as_posix() for folder in ['app','common','flows'] for p in (ROOT/folder).rglob('*.mq')}
    if actual!=set(paths) or len(paths)!=len(set(paths)):
        raise RuntimeError('Module inventory does not match project.json')
    pieces=[]
    for name in paths:
        text=(ROOT/name).read_text('utf-8-sig')
        if '\ufffd' in text:raise RuntimeError('Invalid source encoding: '+name)
        pieces.append('// Module: '+name+'\n'+text)
    view=ROOT/cfg['viewDir']; legacy=ROOT/cfg['legacyDir']
    write_mq(view/'日常任务.mq','\n\n'.join(pieces))
    write_mq(view/'日常任务.uip',(ROOT/cfg['ui']).read_text('utf-8-sig'))
    write_mq(view/'最小环境检查.mq',(ROOT/cfg['probe']).read_text('utf-8-sig'))
    legacy.mkdir(parents=True,exist_ok=True)
    for p in view.iterdir():
        if p.suffix in ['.mq','.uip']:
            (legacy/p.name).write_bytes(p.read_text('utf-8-sig').encode('gbk',errors='strict'))
    report={'modules':paths,'registeredTasks':[1,168],
        'outputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in legacy.iterdir()},
        'validation':'source concatenation and strict GBK encoding only; not assistant compilation or device testing'}
    (ROOT/'reports/构建结果.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Built standalone MQ/UIP: tasks 1 and 168; UTF-8 view + GBK assistant import.')

if __name__=='__main__':main()
