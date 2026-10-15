"""构建并同步到用户指定的现有手机助手脚本；不操作编辑器或运行游戏。"""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import sys
import time
from project_paths import ROOT, manifest


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def target_state(paths):
    # 手机助手保存MQ时会把CRLF改为LF；纯换行转换不算业务代码冲突。
    return [hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
            if p.exists() else None for p in paths]


def inputs():
    folders = ('app', 'common', 'flows', 'ui', 'tools', 'validation', 'reference')
    paths = [ROOT/'project.json', ROOT/'.editorconfig']
    for folder in folders:
        paths.extend(p for p in (ROOT/folder).rglob('*')
                     if p.is_file() and p.suffix.lower() in {'.mq', '.uip', '.py', '.json'}
                     and '__pycache__' not in p.parts)
    return tuple((str(p), digest(p)) for p in sorted(paths))


def sync(target, expected, dry_run=False):
    destinations = [target, target.with_suffix('.uip')]
    if expected is not None and target_state(destinations) != expected:
        raise RuntimeError('助手侧文件已被修改，已停止同步。请先核对并保存需要保留的修改，再重新启动同步工具。')
    for script in ('build_project.py', 'check_mq.py', 'verify_assets.py'):
        subprocess.run([sys.executable, '-X', 'utf8', str(ROOT/'tools'/script)],
                       cwd=ROOT, check=True)
    output = ROOT/manifest()['legacyDir']
    sources = [output/'日常任务.mq', output/'日常任务.uip']
    # 全部先检查再覆盖，构建或编码失败不会更新助手文件。
    for source in sources:
        source.read_bytes().decode('gbk', errors='strict')
    if dry_run:
        print('试运行通过，未更新助手文件：'+str(target))
        return target_state(destinations)
    if expected is not None and target_state(destinations) != expected:
        raise RuntimeError('构建期间助手侧文件发生修改，未同步；请核对两侧修改。')
    changed = [(source, destination) for source, destination in zip(sources, destinations)
               if digest(source) != digest(destination)]
    if changed:
        backup_config = json.loads((ROOT/'assistant-sync.json').read_text(encoding='utf-8'))
        backup_root = Path(backup_config['backupDir']).resolve()
        if backup_root.is_relative_to(ROOT):
            raise RuntimeError('备份目录必须位于当前工程以外。')
        backup = backup_root/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup.mkdir(parents=True)
        for _, destination in changed:
            if destination.exists():
                shutil.copy2(destination, backup/destination.name)
        for source, destination in changed:
            temporary = destination.with_suffix(destination.suffix+'.sync-tmp')
            with temporary.open('xb') as stream:
                stream.write(source.read_bytes())
            temporary.replace(destination)
        print('已同步。请关闭助手内脚本页并重新打开；备份：'+str(backup), flush=True)
    else:
        print('助手文件已是最新。', flush=True)
    return target_state(destinations)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, help='在助手中新建并保存的专用脚本MQ完整路径；默认读取本项目同步配置')
    parser.add_argument('--watch', action='store_true', help='持续监视源码，Ctrl+C停止')
    parser.add_argument('--dry-run', action='store_true', help='只检查构建，不覆盖助手文件')
    args = parser.parse_args()
    if args.target is None:
        config_path = ROOT/'assistant-sync.json'
        if not config_path.exists():
            parser.error('未配置同步目标，请提供--target或assistant-sync.json。')
        args.target = Path(json.loads(config_path.read_text(encoding='utf-8'))['target'])
    target = args.target.resolve()
    if target.suffix.lower() != '.mq' or not target.is_file() or not target.with_suffix('.prop').is_file():
        parser.error('目标必须是助手已创建的MQ文件，且存在同名.prop；请使用专门新建的脚本。')
    if target.is_relative_to(ROOT):
        parser.error('目标应位于助手脚本目录，不能覆盖本项目源码或构建输出。')
    # 首次同步前记录现状；之后任何助手侧改动都会阻止覆盖。
    expected = target_state([target, target.with_suffix('.uip')])
    previous = inputs()
    expected = sync(target, expected, args.dry_run)
    if not args.watch:
        return
    print('正在监视项目源码；助手侧请保持脚本页关闭，需运行时重新打开。Ctrl+C停止。', flush=True)
    while True:
        time.sleep(1)
        current = inputs()
        if current == previous:
            continue
        time.sleep(0.8)
        stable = inputs()
        if current != stable:
            continue
        try:
            expected = sync(target, expected, args.dry_run)
        except subprocess.CalledProcessError:
            print('构建/检查失败，未同步；修复并保存源码后重试。', flush=True)
        previous = stable


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('已停止同步。')
    except (RuntimeError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
