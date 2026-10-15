"""Execute the actual MQ login control flow with mocked time/UI APIs.

The small source translator supports only this tested MQ subset. This is not
the assistant compiler, Android runtime, or a color-recognition/device test.
"""
import ast,json,re,unittest
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]

class Concat(ast.NodeTransformer):
    def visit_BinOp(self,node):
        self.generic_visit(node)
        if isinstance(node.op,ast.BitAnd):
            return ast.copy_location(ast.BinOp(ast.Call(ast.Name('str',ast.Load()),[node.left],[]),ast.Add(),ast.Call(ast.Name('str',ast.Load()),[node.right],[])),node)
        return node

def expr(value):
    parts=re.split(r'("[^"\n]*")',value)
    for i in range(0,len(parts),2):
        p=parts[i].replace('<>','!=')
        for a,b in [('And','and'),('Or','or'),('Not','not')]:p=re.sub(r'\b'+a+r'\b',b,p,flags=re.I)
        parts[i]=re.sub(r'(?<![<>=!])=(?!=)','==',p)
    tree=Concat().visit(ast.parse(''.join(parts),mode='eval'))
    return ast.unparse(ast.fix_missing_locations(tree))

def compile_mq(paths,globals_,wanted=None):
    output=[]
    for path in paths:
        lines=path.read_text('utf-8-sig').splitlines();i=0
        while i<len(lines):
            m=re.match(r'(Function|Sub) (\w+)\((.*)\)',lines[i].strip());i+=1
            if not m:continue
            kind,name,args=m.groups();body=[]
            while i<len(lines) and not re.match(r'End (Function|Sub)$',lines[i].strip()):body.append(lines[i]);i+=1
            i+=1
            if wanted and name not in wanted:continue
            params={v.strip() for v in args.split(',') if v.strip()}
            local={v.strip() for line in body if line.strip().startswith('Dim ') for v in line.strip()[4:].split(',')}
            output += [f'def {name}({args}):','    global '+','.join(sorted(globals_-params-local)),'    _result = None']
            depth=1
            for raw in body:
                s=raw.strip()
                if not s or s.startswith('//'):continue
                if s.startswith('Dim '):
                    for key in s[4:].split(','):output.append('    '*depth+key.strip()+' = 0')
                    continue
                if s=='End If':depth-=1;continue
                if s=='Loop':depth-=1;continue
                if s.startswith('ElseIf '):depth-=1;code='elif '+expr(s[7:-5])+':'
                elif s=='Else':depth-=1;code='else:'
                elif s.startswith('If '):code='if '+expr(s[3:-5])+':'
                elif s=='Do':code='while True:'
                elif s=='Exit Function':code='return _result'
                elif s=='Exit Sub':code='return'
                elif s.startswith('Call '):code=expr(s[5:])
                elif s=='ReleaseCapture':code='ReleaseCapture()'
                elif re.match(r'(Delay|Tap|RunApp|KillApp|WriteConfig) ',s):
                    command,arguments=s.split(' ',1);code=expr(command+'('+arguments+')')
                else:
                    a=re.match(r'(\w+) = (.*)',s)
                    if not a:raise ValueError('Unsupported test subset: '+s)
                    key='_result' if a[1]==name else a[1];code=key+' = '+expr(a[2])
                output.append('    '*depth+code)
                if code.endswith(':'):depth+=1
            output.append('    return _result')
    return '\n'.join(output)

class World:
    def __init__(self,timeout=600,hall_at=None,front='com.tencent.mobileqq',profiles=()):
        self.now=0;self.hall_at=hall_at;self.front=front;self.profiles=list(profiles);self.taps=[];self.kills=[];self.logs=[];self.starts=[]
        globals_={v.strip() for line in (ROOT/'app/入口.mq').read_text('utf-8-sig').splitlines() if line.startswith('Dim ') for v in line[4:].split(',')}
        self.env={key:0 for key in globals_}
        self.env.update(任务成功=1,任务等待=0,任务失败=-1,任务超时=-2,游戏包名='com.tencent.tmgp.dragonball',登录超时秒数=timeout,操作超时秒数=1,邮件间隔秒数=30,当前任务编号=1,登录等待原因='')
        def delay(ms):
            self.now+=ms
            if self.now>4000000:raise RuntimeError('Test loop exceeded budget')
        def find(name):
            found=bool(self.profiles and self.profiles[0]==name)
            self.env['命中X']=400 if found else -1;self.env['命中Y']=800 if found else -1
            return found
        def tap(x,y):
            self.taps.append((self.now,x,y))
            if self.profiles:
                if self.profiles[0]=='QQ一键登录' and len(self.taps)%2==1:return
                self.profiles.pop(0)
                if not self.profiles:self.hall_at=self.now+1000
        self.env.update(str=str,Int=int,TickCount=lambda:self.now,Delay=delay,
            写日志=self.logs.append,WriteConfig=lambda *a:None,ReadConfig=lambda *a:0,
            Sys=SimpleNamespace(GetFront=lambda:self.front,AppIsFront=lambda name:self.front==name,IsRunning=lambda name:True),
            查找图色=find,Tap=tap,ReleaseCapture=lambda:None,
            确认当前在大厅=lambda:self.hall_at is not None and self.now>=self.hall_at,
            等待确认大厅=lambda:self.hall_at is not None and self.now>=self.hall_at,
            处理已知弹窗=lambda:False,点击匹配图色=lambda *a:False,
            点击游戏坐标=lambda *a:False,识别绿色返回箭头=lambda:False,
            设置任务状态=lambda *a:None,RunApp=self.starts.append,
            KillApp=lambda app:self.kills.append((self.now,app)))
        paths=[ROOT/'common/scripts/运行计时.mq',ROOT/'common/scripts/游戏控制.mq',
               ROOT/'flows/001_游戏重连/scripts/登录游戏.mq',ROOT/'flows/001_游戏重连/scripts/启动游戏.mq',
               ROOT/'flows/001_游戏重连/scripts/游戏重连.mq']
        exec(compile_mq(paths,globals_),self.env)
        recovery=compile_mq([ROOT/'common/scripts/任务分派.mq'],globals_,{'恢复未完成任务'})
        exec(recovery,self.env)

class LoginControlTests(unittest.TestCase):
    def test_qq_foreground_can_exceed_old_180_seconds(self):
        w=World(hall_at=200000)
        self.assertEqual(w.env['执行游戏重连'](),1)
        self.assertGreaterEqual(w.now,200000)
        self.assertEqual(w.kills,[])
        self.assertEqual(w.starts,[])
        self.assertFalse(w.env['登录计时中'])

    def test_authorize_agree_confirm_are_clicked_in_qq(self):
        w=World(profiles=['QQ授权登录一','QQ授权同意','QQ授权确认'])
        self.assertEqual(w.env['执行游戏重连'](),1)
        self.assertEqual(len(w.taps),3)
        self.assertEqual(w.kills,[])

    def test_unknown_authorization_host_waits_until_deadline(self):
        w=World(timeout=30,front='com.tencent.mtt')
        self.assertEqual(w.env['执行游戏重连'](),-2)
        self.assertEqual(w.now,30000)
        self.assertEqual(w.kills,[])
        w.env['恢复未完成任务'](-2)
        self.assertEqual(w.kills,[(30000,'com.tencent.tmgp.dragonball')])

    def test_start_timer_is_not_reset_by_reentry(self):
        w=World(timeout=30)
        w.now=5000;w.env['开始登录计时']()
        w.now=10000;w.env['开始登录计时']()
        self.assertEqual(w.env['登录计时起点'],5000)
        w.now=34999;self.assertFalse(w.env['登录是否超时']())
        w.now=35000;self.assertTrue(w.env['登录是否超时']())

    def test_recovery_refuses_to_kill_before_login_timeout(self):
        w=World(timeout=600)
        w.env['开始登录计时']();w.now=1000
        w.env['恢复未完成任务'](-1)
        self.assertEqual(w.kills,[])
        self.assertTrue(w.env['登录计时中'])

    def test_one_click_login_uses_original_relative_offsets(self):
        w=World(profiles=['QQ一键登录'])
        self.assertEqual(w.env['执行游戏重连'](),1)
        self.assertEqual([(x,y) for _,x,y in w.taps],[(249,886),(463,800)])

    def test_known_auth_patterns_do_not_click_other_apps(self):
        w=World(timeout=30,front='com.example.other',profiles=['QQ授权同意'])
        self.assertEqual(w.env['执行游戏重连'](),-2)
        self.assertEqual(w.taps,[])

if __name__=='__main__':unittest.main(verbosity=2)
