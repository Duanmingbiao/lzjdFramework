"""MQ structural and call checks, not the official compiler."""
import re
from project_paths import ROOT,manifest

def check(path):
    source=path.read_text('utf-8-sig')
    stack=[];decl=set();calls=[];errors=[]
    builtins={'readuiconfig','readconfig','tickcount','time','date','getscreenx','getscreeny','isnumeric','int','cdbl'}
    for n,raw in enumerate(source.splitlines(),1):
        s=re.sub(r'"(?:[^"\n]|"")*"','""',raw).split('//',1)[0].strip()
        if not s:continue
        if re.search(r'=\s*\{\s*\}',s):errors.append((n,'unsupported empty table'))
        m=re.match(r'(Sub|Function)\s+([^\s(]+)\(',s,re.I)
        if m:
            name=m[2].lower()
            if name in decl:errors.append((n,'duplicate '+name))
            decl.add(name);stack.append((m[1].lower(),n))
        elif re.match(r'End (Sub|Function|If|Select)$',s,re.I):
            k=s.split()[1].lower()
            if not stack or stack[-1][0]!=k:errors.append((n,'unmatched '+s))
            else:stack.pop()
        elif re.match(r'If\b.*Then$',s,re.I):stack.append(('if',n))
        elif re.match(r'Select Case\b',s,re.I):stack.append(('select',n))
        elif re.match(r'Do$',s,re.I):stack.append(('do',n))
        elif re.match(r'Loop$',s,re.I):
            if not stack or stack[-1][0]!='do':errors.append((n,'unmatched Loop'))
            else:stack.pop()
        if s.count('(')!=s.count(')'):errors.append((n,'unbalanced parentheses'))
        for m in re.finditer(r'(?<![\w.])([\w\u4e00-\u9fff]+)\s*\(',s):
            if not re.match(r'(Sub|Function)\b',s,re.I):calls.append((m[1].lower(),n))
    errors.extend((n,'unclosed '+k) for k,n in stack)
    errors.extend((n,'unknown function '+name) for name,n in calls if name not in decl|builtins)
    if errors:raise RuntimeError(str(path)+'\n'+'\n'.join(f'{n}: {text}' for n,text in errors))
    print(path.name+': structural checks passed; '+str(len(decl))+' procedures/functions')

if __name__=='__main__':
    cfg=manifest()
    check(ROOT/cfg['viewDir']/'日常任务.mq')
    check(ROOT/cfg['probe'])
