"""查演奏资料、实际音源能力与谱面适配；build/probe写索引，其他查询只读。"""
import argparse
import ast
import ctypes as C
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import subprocess
import sys

if __name__ == "__main__" and sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import soundfonts as F
import localization as I18N
import sf2_capabilities as SF
from fluidsynth_library import find_library as find_fluidsynth_library

ROOT = HERE.parent
DATA = ROOT / 'references/instruments.json'
SOURCES = ROOT / 'references/instrument-sources.json'
SNAPSHOT = ROOT / 'soundfonts/capabilities.json'
PROBES = ROOT / 'soundfonts/capability-probes.json'


def knowledge():
    return json.loads(DATA.read_text(encoding="utf-8"))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def profile_for(entry, data):
    ident = entry['id']
    if ident in data['preset_overrides']:
        return data['preset_overrides'][ident]
    if entry['source'] == 'generaluser-gs':
        if entry['bank'] in (120, 128):
            return 'drum-kit'
        return data['gm_profiles'][entry['program']]
    raise ValueError(f'{ident}尚无演奏资料映射；补充资料后再用于创作')


@lru_cache(maxsize=16)
def font_info(path):
    return SF.inspect(path)


@lru_cache(maxsize=1)
def synth_params():
    tree = ast.parse((HERE / 'render_score.py').read_text(encoding="utf-8"))
    result = {}
    for fn in tree.body:
        if isinstance(fn, ast.FunctionDef) and fn.name.startswith('i_'):
            result[fn.name[2:]] = sorted({node.args[0].value for node in ast.walk(fn)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name) and node.func.value.id == 'P'
                and node.func.attr == 'get' and node.args and isinstance(node.args[0], ast.Constant)})
    return result


def backend_contract(inst, engine=None):
    params = synth_params()
    sf2_params = ['strum'] + (['bend', 'vibrato'] if inst == 'erhu' else [])
    result = {
        'builtin_synth': {'params_read': params.get(inst, []) + (['strum'] if inst != 'drums' else []),
                          'identity': '基础合成近似；preset/gm/sf2/engine不决定此后端的声音。',
                          'expression': '音符力度、时值、humanize、swing及声部gain/pan/reverb/delay；参数支持见params_read。'},
        'sf2': {'params_read': ['strum'] if engine else sf2_params,
                'controls_sent': ['note_on velocity', 'note_off', 'CC7 gain', 'CC10 pan', 'CC91 reverb', 'CC11 section dynamics'],
                'erhu_pitch': '仅inst=erhu且显式bend/vibrato时发送单声部±2半音弯音。',
                'not_exposed': ['任意CC时间曲线', '延音踏板CC64', '自动奏法切换/keyswitch', '独立的真实连奏/换弓/吐音控制', '轮替采样选择'],
                'ignored_track_fields': ['delay', 'delay_beats'],
                'ignored_global_fields': ['reverb_level'],
                'caveat': 'SF2内部可能自带包络/调制；这不等于乐谱API暴露了这些控制。音符力度可改变音量/滤波等，不能仅由区域数推断实际听感。'},
    }
    if engine:
        result['sf2'].update({'controls_sent':[],
            'sampler_controls':['gain线性幅度','pan等功率声像','velocity选层/幅度依采样器分支','时值截取依采样器分支','dynamics乘到传入velocity','humanize','strum错开起点'],
            'ignored_track_fields':['delay','delay_beats','reverb'],
            'caveat':'VCSL直接采样后混入固定母带，不走MIDI CC；大鼓dynamics只影响选样，不保证连续幅度变化。'})
    return result


def sampler_info(ident):
    folder = F.ROOT / 'vcsl'
    meta = json.loads((folder / 'map.json').read_text(encoding="utf-8"))
    if ident == 'vcsl:dantranh':
        files = {k:v for k,v in meta.items() if k.startswith('Dan Tranh__')}
        roots = sorted({v['root'] for v in files.values()})
        return {'sample_files':len(files),'roots_midi':roots,'velocity_layers':['mf','f'],
                'selection':'velocity>=.75选f，否则mf；选最近根音，重采样移调夹在±5半音。',
                'duration':'保留max(note_duration,1.4)+0.6秒以内的样本并加内部收尾；短note不是精确制音。',
                'round_robin':'当前选择器不轮替','pitch_bend':'不支持乐谱bend/vibrato；没有真实按滑/连奏。',
                'identity':'越南筝录音，不能标成真实中国古筝。'}
    if ident == 'vcsl:gong':
        files = sorted(k for k in meta if k.startswith('Gong 1__'))
        return {'sample_files':files,'selection':'velocity>=.85选f，否则mf；当前代码不选择p文件。',
                'duration':'最多7秒，自带1.5秒收尾；跨越成品结尾还会按标准渲染器截尾。',
                'pitch':'不跟随音符音高','round_robin':'无轮替'}
    files = sorted(k for k in meta if k.startswith('Bass Drum 1__'))
    return {'sample_files':files,'selection':'按velocity索引选Bass Drum 1文件；不读取Bass Drum 2。',
            'duration':'最多2.5秒；内部0.4秒收尾。','velocity_amplitude':'选样后不再乘velocity；gain仍生效。',
            'pitch':'不跟随音符音高','round_robin':'文件名含rr1不代表当前实现会轮替'}


def capability(entry, data, zones=False):
    key = profile_for(entry, data)
    inst = {'pipa':'pipa','guzheng':'guzheng','erhu':'erhu'}.get(key,entry['track']['inst'])
    result = {'id':entry['id'],'name':entry['name'],'profile_id':key,
              'profile_evidence':data['profiles'][key]['evidence_level'],
              'listening_status':'not_listened','naturalness':'未验证；结构扫描/出声测试不等于适合主奏。',
              'inst_context':inst,'backend':backend_contract(inst, entry['track'].get('engine'))}
    if entry['kind'] == 'sample':
        result['sampler'] = sampler_info(entry['id'])
    else:
        info = dict(font_info(str(F.ROOT / entry['file']))[(entry['bank'],entry['program'])])
        if not zones:
            info.pop('zones')
            ranges=[]
            for note in info.pop('covered_midi_keys'):
                if ranges and ranges[-1][1]+1==note:
                    ranges[-1][1]=note
                else:
                    ranges.append([note,note])
            info['covered_midi_key_ranges']=ranges
        result['sf2'] = info
        result['file'] = entry['file']
        if entry['track'].get('drum_notes'):
            result['drum_notes'] = entry['track']['drum_notes']
        result['patch_notes'] = []
        if entry['source']=='ethnic-light/erhu-practice':
            result['user_audition'] = {'status':'user_accepted_timbre_trial','date':'2026-11-05',
                'reply':'都可以','scope':'仅A4/C5技术片段的音色；不认证完整音域、所有乐句或真实连奏。'}
            result['naturalness'] = '用户已认可该试听片段音色；代理未核听，其他写法与音域未据此验收。'
            result['patch_notes'].extend([
                'irzirgpznj的CC0练习录音切片；来源和转换记录见soundfonts/ethnic-light/erhu-practice-provenance.json。',
                '公开有损MP3试听源；映射仅A4/MIDI69和C5/MIDI72，保留原立体声与录制表情，不向整副键盘移调。',
                'A4样本约1.015秒，C5约2.05秒；无循环延长，超过样本长度会提前失声。',
                '无独立真实连奏转接、换弓、力度层或自动轮替；保留录制的揉弦，不是通用全音域二胡库。'])
        if entry['source']=='ethnic-light/erhu':
            result['patch_notes'].extend([
                'CC0录音转制；来源、哈希、处理与逐样本根音见soundfonts/ethnic-light/manifest.json。',
                'Long/Short/Tasto及Take是显式预设；不自动轮替、切奏法或选择真实力度层。',
                '无循环延长、真实连奏转接或额外揉弦；长音受原样本长度限制，保留原录音音准与起音差异。',
                '2026-11-05用户试听反馈：预设0持续摩擦刺耳，预设7偏乌、发闷；本库替代验收未通过，仅保留评估，不作为已认可升级。其他预设未据此验收。',
                '未核听；技术出声与更多采样不保证音色自然或优于DSK。'])
        if entry['program'] in (44,45) and entry['source']=='generaluser-gs':
            result['patch_notes'].append('颤弓/拨奏是独立预设，不是把普通弦乐note缩短后自动切换。')
        if entry['id']=='generaluser-gs:11:29':
            result['patch_notes'].append('原名含CC21；当前乐谱后端不发送CC21，不能声称已控制wah。')
        if 'noVel' in entry['name']:
            result['patch_notes'].append('原名提示noVel；实际力度响应需要测试，不能从名称推断已验证。')
    return result


def inventory(zones=False):
    data = knowledge()
    catalog = F.build_catalog()
    entries = [capability(e,data,zones) for e in catalog['entries']]
    files = {str(p.relative_to(ROOT)):digest(p) for p in sorted((F.ROOT).rglob('*.sf2'))}
    files.update({str(p.relative_to(ROOT)):digest(p) for p in [DATA,SOURCES,HERE/'render_score.py',HERE/'render_score_sf2.py',HERE/'sampler.py',HERE/'instruments.py',HERE/'sf2_capabilities.py',HERE/'soundfonts.py']})
    return {'schema_version':1,'scope':'安装的所有SF2预设、VCSL入口、基础合成类型和鼓件；不是世界乐器全集。',
            'counts':{**catalog['counts'],'profiles':len(data['profiles']),'builtin_types':len(data['builtin_profiles']),'drum_aliases':len(data['drum_profiles'])},
            'file_sha256':files,'presets':entries,'builtin_profiles':data['builtin_profiles'],
            'drum_profiles':data['drum_profiles'],
            'drum_routing':'SF2默认taiko/gong走VCSL；gm_drums=true走GM近似，drum_notes覆盖优先。其他鼓件按实际鼓组映射；drums共用通道10。',
            'listening_status':'所有条目初始未核听；不得自动升级为听感合格。'}


def lookup(ident, zones=False):
    data = knowledge()
    catalog = F.build_catalog()
    entry = next((e for e in catalog['entries'] if e['id']==ident), None)
    if not entry:
        raise ValueError(f'找不到实际预设 {ident}')
    cap = capability(entry,data,zones)
    profile = data['profiles'][cap['profile_id']]
    source_ids = sorted(set(profile['sources']+data['families'][profile['family']]['sources']))
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    probe = None
    if PROBES.exists():
        saved = json.loads(PROBES.read_text(encoding="utf-8"))
        match = saved.get('results',{}).get(ident)
        fresh = (saved.get('file_sha256',{}).get(entry['file']) == digest(F.ROOT/entry['file'])) if entry.get('file') else saved.get('sampler_fingerprint') == sampler_fingerprint()
        if entry['kind']=='sample':
            fresh = fresh and saved.get('renderer_sha256',{}).get('sampler.py') == digest(HERE/'sampler.py')
        if match and fresh:
            probe = match
    return {'profile':profile,'family_guidance':data['families'][profile['family']],
            'capability':cap,'technical_probe':probe,'sources':{k:sources[k] for k in source_ids},
            'configuration':{'preset':entry['id'],**entry['track'],'inst':cap['inst_context']}}


def audit_score(path, backend='sf2'):
    import render_score as R
    import render_score_sf2 as S
    sc,bpb,tracks,arr,sections = R.load(str(path))
    data = knowledge()
    catalog = {e['id']:e for e in F.build_catalog()['entries']}
    resolved = F.resolve_tracks(tracks,str(F.ROOT/'GeneralUser-GS.sf2'),default_programs={k:v[0] for k,v in S.GM.items()}) if backend=='sf2' else tracks
    result = {'backend':backend,'tracks':{},'issues':[],'note':'只检查资料映射、控制支持与谱面风险，不判定好听/自然，也不修改乐谱。'}
    if backend=='sf2' and 'reverb_level' in sc:
        result['issues'].append('全局reverb_level不被SF2后端读取；该后端使用固定母带混响及各声部CC91。')
    performance = (sc.get('design') or {}).get('performance',{})
    for name,cfg in resolved.items():
        inst = cfg['inst']; issues = []
        if backend=='synth':
            profile_id = data['builtin_profiles'][inst]; cap = {'backend':backend_contract(inst)}
        else:
            if cfg.get('engine','').startswith('sampler:'):
                ident = 'vcsl:'+cfg['engine'][8:]
            else:
                font = str(cfg.get('sf2','GeneralUser-GS.sf2')).replace('\\','/').rsplit('.',1)[0].lower()
                ident = f'{font}:{cfg.get("gm",{}).get("bank",128 if inst=="drums" else 0)}:{cfg.get("gm",{}).get("program",0)}'
            if ident not in catalog:
                raise ValueError(f'{name}: {ident}未登记演奏资料')
            entry = catalog[ident]; profile_id = profile_for(entry,data); cap = capability(entry,data,True)
            cap['backend'] = backend_contract(inst,cfg.get('engine'))
            if data['profiles'][profile_id]['evidence_level']=='identity_unverified':
                issues.append('预设具体乐器身份待核实，保留原名，不按旧中文别名作结论。')
            if inst in ('dizi','xiao','erhu','guzheng','pipa') and profile_id!=data['builtin_profiles'][inst]:
                issues.append(f'inst={inst}的目标乐器与实际预设资料{profile_id}不同；确认近似替代。')
            for field in cap['backend']['sf2']['ignored_track_fields']:
                if cfg.get(field):
                    issues.append(f'{field}在SF2后端未实现。')
        allowed = cap['backend']['builtin_synth' if backend=='synth' else 'sf2']['params_read']
        ignored = sorted(set(cfg.get('params',{}))-set(allowed))
        if ignored:
            issues.append('当前后端不读取params: '+', '.join(ignored))
        if name not in performance:
            issues.append('缺少design.performance演奏意图/实现记录；写谱前先查资料并记录选择。')
        requested = performance.get(name,{}).get('instrument')
        if requested and requested not in data['profiles']:
            issues.append(f'演奏记录中的instrument={requested}不在资料库。')
        elif requested and requested!=profile_id:
            issues.append(f'演奏目标{requested}与实际音源资料{profile_id}不同，请说明替代。')
        events = [ev for a in arr for bar in sections[a][1].get(name,[None]*sections[a][0]) for ev in (bar or [])]
        routing = {}
        if inst=='drums' and backend=='sf2':
            for lane in sorted({event[1] for event in events}):
                if lane in cfg.get('drum_notes',{}):
                    routing[lane] = {'route':'custom_midi_note','note':cfg['drum_notes'][lane]}
                elif lane in ('taiko','gong') and not cfg.get('gm_drums'):
                    routing[lane] = {'route':'vcsl:bassdrum' if lane=='taiko' else 'vcsl:gong', 'identity':'低音大鼓近似' if lane=='taiko' else 'Gong采样'}
                elif lane in S.MELODIC_DRUMS:
                    routing[lane] = {'route':'default_generaluser_melodic_approximation','program':S.MELODIC_DRUMS[lane][0],'note':S.MELODIC_DRUMS[lane][1]}
                else:
                    routing[lane] = {'route':'selected_kit_midi_note','note':S.DRUM_NOTE[lane]}
        transposition = None
        if inst!='drums' and events and backend=='sf2' and 'sf2' in cap:
            keys = {n for pos,dur,notes,vel in events for n in notes}
            missing = sorted(keys-set(cap['sf2']['covered_midi_keys']))
            if missing:
                issues.append(f'SF2没有映射音高: {missing}')
            if ident=='ethnic-light/erhu-practice:0:0':
                durations={z['root_midi']:z['duration_seconds'] for z in cap['sf2']['zones']}
                if any(dur*60/float(sc.get('bpm',100))>durations[n]
                       for pos,dur,notes,vel in events for n in notes if n in durations):
                    issues.append('谱面持续音超过演奏切片原样本长度（A4约1.015秒、C5约2.05秒）；此预设无循环延长，会提前失声。')
            shifts = [abs(((z['fixed_key'] if z['fixed_key'] is not None else n)-z['root_midi'])*z['scale_tuning_cents_per_key']/100+z['coarse_tune_semitones']+z['fine_tune_cents']/100)
                      for n in keys for z in cap['sf2']['zones'] if z['root_midi'] is not None and z['keys'][0]<=n<=z['keys'][1]]
            if shifts:
                transposition = {'max_absolute_semitones':round(max(shifts),2),'basis':'键位/固定键、根音、scale tuning及调音生成器估算；不等于自然度判断。'}
                if max(shifts)>12:
                    issues.append('部分发声区域对样本移调超过八度，建议核听该音区；这不是音域违规判决。')
            if any(vel<=0 or not any(z['keys'][0]<=n<=z['keys'][1] and z['velocities'][0]<=int(max(1,min(127,vel*115)))<=z['velocities'][1]
                for z in cap['sf2']['zones']) for pos,dur,notes,vel in events for n in notes):
                issues.append('部分音符的实际MIDI力度/键位没有匹配区域，或0力度会被后端夹到1。')
        if backend=='sf2' and cfg.get('engine')=='sampler:dantranh' and events:
            roots = cap['sampler']['roots_midi']
            far = sorted({n for p,d,notes,v in events for n in notes if min(abs(n-r) for r in roots)>5})
            if far:
                issues.append(f'Dan Tranh请求音高{far}超过最近采样±5半音，当前代码会夹住移调，不能保证目标音高。')
        result['tracks'][name] = {'profile_id':profile_id,'lookup':f'python3 -I scripts/instruments.py instrument {profile_id}',
                                  'ignored_params':ignored,'listening_status':'not_listened','drum_routing':routing,'sample_transposition':transposition,'issues':issues}
        result['issues'].extend(f'{name}: {issue}' for issue in issues)
    return result


def sampler_fingerprint():
    return hashlib.sha256(''.join(digest(p) for p in sorted((F.ROOT/'vcsl').glob('*')) if p.suffix in ('.wav','.json')).encode()).hexdigest()


def probe_all(output):
    """Raw FluidSynth smoke test, separate from rendering/artistic audition."""
    import numpy as np
    path = find_fluidsynth_library()
    if not path:
        raise ValueError('找不到FluidSynth动态库，不能执行出声测试')
    lib = C.CDLL(path); P,I = C.c_void_p,C.c_int
    def bind(name,rest,args):
        fn = getattr(lib,name);fn.restype,fn.argtypes=rest,args;return fn
    settings_new=bind('new_fluid_settings',P,[])
    setnum=bind('fluid_settings_setnum',I,[P,C.c_char_p,C.c_double])
    setint=bind('fluid_settings_setint',I,[P,C.c_char_p,I])
    new=bind('new_fluid_synth',P,[P]);load=bind('fluid_synth_sfload',I,[P,C.c_char_p,I])
    select=bind('fluid_synth_program_select',I,[P,I,I,I,I]);on=bind('fluid_synth_noteon',I,[P,I,I,I]);off=bind('fluid_synth_all_sounds_off',I,[P,I])
    write=bind('fluid_synth_write_float',I,[P,I,P,I,I,P,I,I])
    delete=bind('delete_fluid_synth',None,[P]);delete_settings=bind('delete_fluid_settings',None,[P])
    groups={}
    for entry in F.build_catalog()['entries']:
        if entry['kind']!='sample':groups.setdefault(entry['file'],[]).append(entry)
    version=bind('fluid_version_str',C.c_char_p,[])()
    result={'schema_version':1,'fluidsynth_version':version.decode(),'method':'raw FluidSynth program_select + mapped note at velocity80, 0.6s; retry 1.5s on silence. No master/normalization.','scope':'测试实际SF2预设出声与有限数值，不证明MIDI流程全部控制、演奏自然度或主奏适合性。','listening_status':'not_listened','file_sha256':{},'results':{}}
    for relative,entries in groups.items():
        settings=settings_new();setnum(settings,b'synth.sample-rate',22050.0);setnum(settings,b'synth.gain',.2)
        setint(settings,b'synth.reverb.active',0);setint(settings,b'synth.chorus.active',0)
        synth=new(settings)
        try:
            sid=load(synth,str(F.ROOT/relative).encode(),0)
            if sid<0:raise ValueError('FluidSynth加载失败: '+relative)
            info=font_info(str(F.ROOT/relative));result['file_sha256'][relative]=digest(F.ROOT/relative)
            for entry in entries:
                cap=info[(entry['bank'],entry['program'])];covered=cap['covered_midi_keys']
                candidates=[36] if entry['bank'] in (120,128) or entry['kind']=='drums' else [60]
                candidates += cap['root_midi_notes']
                candidates = list(dict.fromkeys(n for n in candidates if n in covered)) or covered[:1]
                measured=[];status='no_audible_energy'
                for note in candidates[:4]:
                    for seconds in [.6,1.5]:
                        off(synth,0);code=select(synth,0,sid,entry['bank'],entry['program'])
                        if code<0:raise ValueError('FluidSynth预设选择失败: '+entry['id'])
                        on(synth,0,note,80);n=round(seconds*22050);left=np.zeros(n,dtype='float32');right=left.copy()
                        if write(synth,n,left.ctypes.data,0,1,right.ctypes.data,0,1)<0:raise ValueError('FluidSynth渲染失败')
                        x=np.stack([left,right]);rms=float(np.sqrt(np.mean(x*x)));peak=float(abs(x).max())
                        measured.append({'note':note,'seconds':seconds,'rms':rms,'peak':peak,'finite':bool(np.isfinite(x).all())})
                        if not measured[-1]['finite']:raise ValueError('非有限音频: '+entry['id'])
                        if rms>1e-7:status='rendered';break
                    if status=='rendered':break
                result['results'][entry['id']]={'status':status,'attempts':measured,'listening_status':'not_listened'}
        finally:
            delete(synth);delete_settings(settings)
    import render_score as R
    import sampler as SMP
    sample=SMP.Sampler()
    for ident,inst in [('vcsl:dantranh','dantranh'),('vcsl:bassdrum','bassdrum'),('vcsl:gong','gong')]:
        note=60 if inst!='dantranh' else round(next(v['root'] for v in sample.cat.values() if v.get('root')))
        attempts=[]
        for vel in [.4,.9]:
            x=sample.note(inst,note,vel,.4);attempts.append({'velocity':vel,'rms':float(np.sqrt(np.mean(x*x))),'finite':bool(np.isfinite(x).all())})
        result['results'][ident]={'status':'rendered' if all(a['finite'] and a['rms']>1e-7 for a in attempts) else 'no_audible_energy','attempts':attempts,'listening_status':'not_listened'}
    result['sampler_fingerprint']=sampler_fingerprint()
    for inst,fn in R.INST.items():
        x=fn(60,.4,.7,{},np.random.default_rng(7))
        result['results']['builtin:'+inst]={'status':'rendered' if np.isfinite(x).all() and np.mean(x*x)>1e-10 else 'no_audible_energy','listening_status':'not_listened'}
    for name in knowledge()['drum_profiles']:
        x=R.drum_shot(name,np.random.default_rng(7))
        result['results']['drum:'+name]={'status':'rendered' if np.isfinite(x).all() and np.mean(x*x)>1e-10 else 'no_audible_energy','listening_status':'not_listened'}
    result['scope']+=' 另测试VCSL三入口、基础合成函数和鼓件函数出声，均不等于完整标准渲染流程或听感验收。'
    result['renderer_sha256']={p.name:digest(p) for p in [HERE/'render_score.py',HERE/'render_score_sf2.py',HERE/'sampler.py']}
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n', encoding="utf-8")
    return {'tested':len(result['results']),'rendered':sum(v['status']=='rendered' for v in result['results'].values()),'output':str(output)}


def audition(ident,out):
    """Make a technical gesture clip through the unchanged standard renderer."""
    import render_score as R
    data=lookup(ident,True)
    if ident.startswith('vcsl:') or data['configuration']['inst']=='drums':
        raise ValueError('该入口使用专门的鼓/采样检查，不能用有音高乐句探针')
    cap=data['capability']['sf2'];keys=cap['covered_midi_keys']
    reference_range=data['profile']['sounding_range']['notes']
    if reference_range:
        low,high=map(R.midi_of,reference_range);keys=[k for k in keys if low<=k<=high]
    candidates=[n for n in [60,62,64,67,65] if n in keys]
    if not candidates and keys:
        candidates=sorted(keys,key=lambda k:abs(k-72))[:5]
    if not candidates:raise ValueError('缺少探针键位')
    names=['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B']
    note=lambda n:names[n%12]+str(n//12-1)
    a=note(candidates[0]);b=note(candidates[min(1,len(candidates)-1)]);c=note(candidates[-1])
    score={'bpm':100,'humanize_ms':0,'tracks':{'probe':data['configuration']},'sections':{'TEST':{'probe':[
        f'{a}:1.5@.6 {b}:.5@.6 {c}:1.5@.6 r:.5',f'({a}:.25@.6 r:.25)*8',
        f'{a}:1@.3 {a}:1@.5 {a}:1@.7 {a}:.75@.9 r:.25']}},'arrangement':['TEST'],
        'design':{'purpose':'技术探针：连接、短音、重复与力度，不是符合该乐器习惯的演奏示范，也不是作品。'}}
    out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():raise ValueError(f'输出已存在: {out}')
    fixture=out.with_suffix('.score.json')
    if fixture.exists():raise ValueError(f'输出已存在: {fixture}')
    fixture.write_text(json.dumps(score,ensure_ascii=False,indent=2)+'\n', encoding="utf-8")
    subprocess.run([sys.executable,'-I',str(HERE/'render_score_sf2.py'),str(fixture),str(out),'--duration','8','--tail','.8'],check=True)
    return {'audio':str(out),'score':str(fixture),'listening_status':'not_listened'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    find=sub.add_parser('search');find.add_argument('query',nargs='?',default='')
    inst=sub.add_parser('instrument');inst.add_argument('id')
    preset=sub.add_parser('preset');preset.add_argument('id');preset.add_argument('--zones',action='store_true')
    build=sub.add_parser('build');build.add_argument('--out',type=Path,default=SNAPSHOT)
    probe=sub.add_parser('probe-all');probe.add_argument('--out',type=Path,default=PROBES)
    check=sub.add_parser('score');check.add_argument('path',type=Path);check.add_argument('--backend',choices=['synth','sf2'],default='sf2')
    aud=sub.add_parser('audition');aud.add_argument('id');aud.add_argument('--out',type=Path,required=True)
    I18N.add_argument(parser)
    for command in (find, inst, preset, build, probe, check, aud):
        command.add_argument('--lang', choices=I18N.LANGUAGES, default=argparse.SUPPRESS)
    args=parser.parse_args()
    I18N.use_language(args.lang)
    try:
        if args.command=='search':
            data=knowledge();words=I18N.search_words(args.query)
            result={'instruments':[{**{k:p[k] for k in ['id','name','aliases','family','evidence_level']}, 'instrument_name':I18N.instrument_name(p['id'],args.lang)} for p in data['profiles'].values() if all(w in I18N.normalize(' '.join([p['id'],p['name'],*p['aliases']])) for w in words)],
                    'presets':[{'id':e['id'],'name':e['name'],'profile_id':profile_for(e,data),'instrument_name':I18N.instrument_name(profile_for(e,data),args.lang)} for e in F.search(F.build_catalog(),args.query)]}
        elif args.command=='instrument':
            data=knowledge();profile=data['profiles'][args.id];sources=json.loads(SOURCES.read_text(encoding="utf-8"));family=data['families'][profile['family']]
            result={'profile':profile,'instrument_name':I18N.instrument_name(args.id,args.lang),'family_guidance':family,'sources':{s:sources[s] for s in sorted(set(profile['sources']+family['sources']))}}
        elif args.command=='preset':
            result=lookup(args.id,args.zones)
            result['instrument_name']=I18N.instrument_name(result['profile_id'],args.lang)
        elif args.command=='score':result=audit_score(args.path,args.backend)
        elif args.command=='probe-all':result=probe_all(args.out)
        elif args.command=='audition':result=audition(args.id,args.out)
        else:
            result=inventory(False);args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n', encoding="utf-8");result={'counts':result['counts'],'output':str(args.out)}
    except (ValueError,KeyError) as e:
        parser.error(str(e))
    result['report_language']=args.lang
    result['reference_text_language']='original'
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
