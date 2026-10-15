"""Write the explicit first-phase module inventory and normalize maintenance text."""
import json
from project_paths import ROOT,write_mq

modules=[
    'common/scripts/常量.mq','common/scripts/日志.mq','common/scripts/配置读取.mq',
    'common/scripts/运行计时.mq','common/scripts/游戏控制.mq','common/scripts/点击操作.mq',
    'common/scripts/图色参数.mq','common/scripts/页面识别.mq','common/scripts/返回大厅.mq',
    'common/scripts/任务状态.mq','common/scripts/任务分派.mq',
    'flows/001_游戏重连/scripts/启动游戏.mq','flows/001_游戏重连/scripts/登录游戏.mq',
    'flows/001_游戏重连/scripts/游戏重连.mq','flows/168_领邮件奖励/scripts/领邮件奖励.mq',
]
cfg={'format':3,'entry':'app/入口.mq','modules':modules,
     'ui':'ui/最小闭环.uip','probe':'validation/最小环境检查.mq',
     'viewDir':'dist/UTF-8查看版','legacyDir':'dist/手机助手3.8导入版',
     'phase':'最小邮件闭环 v0.2：QQ授权和独立登录超时','registeredTaskIds':[1,168]}
(ROOT/'project.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
for path in [ROOT/cfg['entry'],ROOT/cfg['ui'],ROOT/cfg['probe']]+[ROOT/p for p in modules]:
    write_mq(path,path.read_text('utf-8-sig'))
print('Prepared first-phase module inventory and UTF-8 BOM/CRLF source files.')
