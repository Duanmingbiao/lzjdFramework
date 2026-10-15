"""Generate MQ lookup from the local, source-attributed parameter manifest."""
import json
from project_paths import ROOT,write_mq

def main():
    report=json.loads((ROOT/'reference/图色来源.json').read_text('utf-8'))
    lines=['// Original V5.510 color parameters; current game UI requires device testing.',
           'Function 查找图色(图色名称)','    命中X = -1','    命中Y = -1','    Select Case 图色名称']
    for r in report['profiles']:
        args=','.join(json.dumps(v,ensure_ascii=False) for v in r.get('effectiveDefinition',r['definition']))
        lines += ['    Case '+json.dumps(r['name'],ensure_ascii=False),
                  '        // Evidence: '+r['id'],'        FindMultiColor '+args+',命中X,命中Y']
    lines += ['    End Select','    查找图色 = 命中X >= 0 And 命中Y >= 0','End Function']
    write_mq(ROOT/'common/scripts/图色参数.mq','\n'.join(lines)+'\n')
    print('Generated',len(report['profiles']),'reviewed profiles from local manifest.')

if __name__=='__main__':main()
