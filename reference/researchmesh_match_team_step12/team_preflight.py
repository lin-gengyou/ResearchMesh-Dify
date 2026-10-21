"""Reference bridge; current/confirmation must be supplied by an authenticated backend.

These comparisons detect inconsistent snapshots, not forged client requests.
No identity authentication, state storage, contact, or publication occurs here.
"""
import copy
import datetime
import hashlib
import json
import math
import re

class BridgeError(ValueError):
    pass

NORMALIZED_KEYS = ('id','title','owner_id','need_version','hours_per_week','start_date','expires_date','location','requirements')

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def valid_text(value, limit=160):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit

def task_text(value):
    return re.sub(r'[\s，,；;。]+', '', value)

def task_proposal(handoff):
    """AI already extracts the task; this only separates its explicit clauses."""
    s = handoff.get('reviewed_snapshot', {})
    f = s.get('fields', {}).get('task', {})
    if f.get('status') != 'explicit' or not valid_text(f.get('value'), 3000):
        raise BridgeError('缺少AI提取且已审核的具体职责')
    parts = [x.strip() for x in re.split(r'[，；;\n]+', f['value']) if x.strip()]
    if not 1 <= len(parts) <= 6 or any(len(x) > 500 for x in parts):
        raise BridgeError('任务需明确整理为1至6项；未静默截断')
    return [{'id': 'R'+str(i+1), 'text': x, 'source_quote': x} for i,x in enumerate(parts)]

def prepare_review_need(handoff, confirmation, current):
    if not all(isinstance(x, dict) for x in (handoff, confirmation, current)):
        raise BridgeError('缺少审核交接、规范化确认或当前状态')
    if handoff.get('schema_version') != 'need_matching_handoff_0.1' or handoff.get('route') != 'await_backend_confirmation' or handoff.get('review_status') != 'human_confirmed_in_demo':
        raise BridgeError('需求尚未通过本次审核')
    snapshot = handoff.get('reviewed_snapshot')
    source_hash = handoff.get('source_draft_sha256')
    run_id = handoff.get('source_workflow_run_id')
    if not isinstance(snapshot, dict) or not valid_text(run_id, 160) or source_hash != digest(snapshot):
        raise BridgeError('所审内容与来源指纹不一致')
    if snapshot.get('execution_checks', {}).get('ready_for_owner_review') is not True or snapshot.get('requirements_checks', {}).get('ready_for_owner_review') is not True:
        raise BridgeError('执行条件或能力要求尚未齐备')
    normalized = confirmation.get('normalized_need')
    if not isinstance(normalized, dict) or confirmation.get('accepted') is not True:
        raise BridgeError('AI预填的匹配条件尚未由负责人核对')
    if set(normalized) != set(NORMALIZED_KEYS):
        raise BridgeError('规范化需求字段缺失或包含未约定字段')
    nhash = digest(normalized)
    if confirmation.get('normalized_sha256') != nhash:
        raise BridgeError('规范化条件已改变，请重新核对')
    bindings = {'need_id': normalized.get('id'), 'owner_id': normalized.get('owner_id'),
                'need_version': normalized.get('need_version'), 'source_workflow_run_id': run_id,
                'source_draft_sha256': source_hash, 'normalized_sha256': nhash}
    if any(confirmation.get(k) != v or current.get(k) != v for k,v in bindings.items()):
        raise BridgeError('需求已换版、来源不符或确认内容已过期')
    if current.get('active') is not True or current.get('status') != 'open' or confirmation.get('actor_id') != normalized.get('owner_id'):
        raise BridgeError('需求未开放或确认角色不符')
    if not valid_text(normalized.get('id'), 120) or not valid_text(normalized.get('owner_id'), 120) or type(normalized.get('need_version')) is not int or normalized['need_version'] < 1:
        raise BridgeError('需求标识、负责人或版本无效')
    if not valid_text(normalized.get('title'), 160) or not valid_text(normalized.get('location'), 160):
        raise BridgeError('标题或协作场地尚未明确')
    hours = normalized.get('hours_per_week')
    if not isinstance(hours, (int,float)) or isinstance(hours,bool) or not math.isfinite(hours) or not 0 < hours <= 168:
        raise BridgeError('每周预计工时无效，不能以项目总预算替代')
    time_field = snapshot.get('fields',{}).get('time_commitment',{})
    time_quote = time_field.get('quote','') if isinstance(time_field,dict) else ''
    weekly_mentions = re.finditer(r'每周[^0-9。；;\n]{0,24}([0-9]+(?:\.[0-9]+)?)\s*(?:小时|钟头|h)',time_quote,re.I)
    for mention in weekly_mentions:
        amount=float(mention.group(1)); clause=mention.group(0)
        valid = hours <= amount if re.search(r'上限|最多|不超过|至多|不多于',clause) else hours >= amount if re.search(r'至少|下限|不少于',clause) else hours == amount
        if not valid:raise BridgeError('每周工时与已审核原文不一致；不能把总计工时当每周工时')
    try:
        if any(not isinstance(normalized.get(k), str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',normalized[k]) for k in ('start_date','expires_date')):raise ValueError()
        start = datetime.date.fromisoformat(normalized['start_date'])
        expiry = datetime.date.fromisoformat(normalized['expires_date'])
        if expiry < datetime.date.today():
            raise ValueError()
    except (KeyError, ValueError, TypeError):
        raise BridgeError('需确认有效的开始日期和招募有效期')
    reqs = normalized.get('requirements')
    source_task = snapshot.get('fields', {}).get('task', {})
    task = source_task.get('value', '')
    if source_task.get('status') != 'explicit' or not valid_text(task, 3000) or not isinstance(reqs,list) or not 1 <= len(reqs) <= 6:
        raise BridgeError('需确认1至6项具体任务；未静默截断')
    ids = set(); texts = []
    for r in reqs:
        if not isinstance(r,dict) or not valid_text(r.get('id'),50) or r['id'] in ids or not valid_text(r.get('text'),500):
            raise BridgeError('任务标识重复、描述为空或超过长度')
        ids.add(r['id']); texts.append(r['text'])
        if r['text'] != r.get('source_quote') or r['text'] not in task:
            raise BridgeError('任务必须保留已审核职责的原文，新增职责需重新审核')
        if any(type(r.get(k)) is not bool for k in ('must','allow_adjacent','independent_required')):
            raise BridgeError('任务范围、相邻经历和独立程度需要明确核对')
    if task_text(''.join(texts)) != task_text(task):
        raise BridgeError('任务出现遗漏、重复或顺序改变，请重新整理')
    skills = snapshot.get('requirements', [])
    # A mixed independent/guided task cannot be generalized from a single skill row.
    if skills and all(x.get('independence') == 'guided' for x in skills) and any(r['independent_required'] for r in reqs):
        raise BridgeError('原审核仅要求指导下完成，不能升级为必须独立')
    need = copy.deepcopy(normalized)
    need.update({'status':'open', 'owner_confirmed':True,
                 'skill_requirements':copy.deepcopy(skills),
                 'requirements_policy':copy.deepcopy(snapshot.get('requirements_policy',{})),
                 'learning_support':copy.deepcopy(snapshot.get('learning_support',{})),
                 'provenance':{**bindings, 'mode':'review_handoff_demo', 'identity_verified':False},
                 'identity_verified':False, 'auto_publish':False, 'auto_contact':False})
    return need

def check_current_match(packet, current):
    """Call before preparing team/agreement inputs; backend must load current state."""
    if not isinstance(packet,dict) or not isinstance(current,dict):
        raise BridgeError('缺少匹配结果或当前需求状态')
    need = packet.get('need',{})
    if not isinstance(need,dict):raise BridgeError('匹配需求结构无效')
    provenance = need.get('provenance',{})
    if not isinstance(provenance,dict) or provenance.get('mode') != 'review_handoff_demo':
        raise BridgeError('旧式演示输入缺少审核与版本来源，不能直接接续组队')
    keys = ('need_id','owner_id','need_version','source_workflow_run_id','source_draft_sha256','normalized_sha256')
    if current.get('active') is not True or current.get('status') != 'open' or any(current.get(k) != provenance.get(k) for k in keys):
        raise BridgeError('需求已换版或关闭，旧匹配不能接续组队')
    if need.get('id') != current.get('need_id') or need.get('owner_id') != current.get('owner_id') or need.get('need_version') != current.get('need_version'):
        raise BridgeError('匹配结果的需求标识与来源不一致')
    if digest({k:need.get(k) for k in NORMALIZED_KEYS}) != provenance.get('normalized_sha256'):
        raise BridgeError('匹配中的任务或条件已改变，不能沿用旧确认')
    try:
        expiry = datetime.date.fromisoformat(need['expires_date'])
        if expiry < datetime.date.today():raise ValueError()
    except (KeyError,ValueError,TypeError):
        raise BridgeError('匹配所据招募已过期')
    return copy.deepcopy(need)


"""Bridge for fictional regression and future authenticated backend use.
Current records and confirmations are not authenticated by Dify itself.
"""
import copy
import datetime
import math


def positive(x):
    return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and 0 < x <= 168

def team_from_match(envelope, people):
    packet=envelope.get('decision_packet'); current=envelope.get('current')
    need=check_current_match(packet,current)
    if current.get('latest_matching_sha256') != digest(packet):
        raise BridgeError('匹配结果不是后端当前保存的那一次')
    confirm=envelope.get('planning_confirmation',{})
    planning=confirm.get('planning')
    if not isinstance(planning,dict) or confirm.get('accepted') is not True or confirm.get('actor_id') != need['owner_id']:
        raise BridgeError('指定周的任务工时尚未由负责人核对')
    if confirm.get('need_version') != need['need_version'] or confirm.get('matching_sha256') != digest(packet) or confirm.get('planning_sha256') != digest(planning):
        raise BridgeError('周计划已改变或采用了旧匹配，请重新核对')
    if current.get('planning_sha256') != digest(planning):
        raise BridgeError('周计划不是后端当前保存的确认记录')
    try:
        start=datetime.date.fromisoformat(planning['week_start'])
        if start.isoformat() != planning['week_start'] or start.weekday()!=0 or start<datetime.date.fromisoformat(need['start_date']):raise ValueError()
    except (KeyError,TypeError,ValueError):
        raise BridgeError('请确认不早于需求开始日的周一日期')
    if type(planning.get('max_people')) is not int or not 1<=planning['max_people']<=3:
        raise BridgeError('本版分配人数为1至3人')
    hours=planning.get('task_hours'); reqs=need['requirements']
    if not isinstance(hours,list) or len(hours)!=len(reqs) or any(not isinstance(r,dict) for r in hours):
        raise BridgeError('周计划必须逐项保留当前任务及工时')
    ids=[r.get('id') for r in hours]
    if len(set(ids))!=len(ids) or set(ids)!={r['id'] for r in reqs} or any(not positive(r.get('hours')) for r in hours):
        raise BridgeError('周任务标识重复、遗漏或工时无效')
    budget=planning.get('weekly_task_budget')
    if not positive(budget) or sum(r['hours'] for r in hours)>budget+1e-9:
        raise BridgeError('本周任务超过明确确认的本周任务预算')
    candidates=packet.get('candidates',[])
    allowed={p['id'] for p in candidates}
    if not isinstance(people,list) or not people or any(not isinstance(p,dict) or p.get('id') not in allowed for p in people):
        raise BridgeError('候选包包含未在本次匹配中评估的人')
    if len({p['id'] for p in people})!=len(people):raise BridgeError('候选标识重复')
    existing=planning.get('existing_member_ids',[])
    if not isinstance(existing,list) or len(set(existing))!=len(existing) or any(pid not in {p['id'] for p in people} for pid in existing):
        raise BridgeError('已有成员必须有本次授权候选记录')
    hourmap={r['id']:r['hours'] for r in hours}
    result=copy.deepcopy(need)
    result.update({'period':'one_week','start_date':start.isoformat(),'week_start':start.isoformat(),
        'week_end':(start+datetime.timedelta(days=6)).isoformat(),
        'weekly_task_budget':budget,'max_people':planning['max_people'],'existing_member_ids':existing,
        'source_matching_need':copy.deepcopy(need),
        'planning_provenance':{'matching_sha256':digest(packet),'planning_sha256':digest(planning),
            'need_version':need['need_version'],'mode':'matched_week_plan_demo'},
        'requirements':[{**copy.deepcopy(r),'hours':hourmap[r['id']]} for r in reqs]})
    return result

def agreement_from_team(packet, *, current, plan_index, performer_id, agreement_id):
    """Build one person's one-week draft; never accept it or multiply weekly hours."""
    if not isinstance(packet,dict) or packet.get('status')!='proposed':
        raise BridgeError('组队尚无可供复核的方案')
    need=packet.get('need',{}); provenance=need.get('planning_provenance',{})
    check_current_match({'need':need.get('source_matching_need')},current)
    if provenance.get('planning_sha256')!=current.get('planning_sha256') or provenance.get('matching_sha256')!=current.get('latest_matching_sha256'):
        raise BridgeError('组队所据周计划或匹配已改变')
    if current.get('latest_team_sha256')!=digest(packet):raise BridgeError('组队方案不是后端当前保存的那一版')
    plans=packet.get('plans',[])
    if type(plan_index) is not int or not 0<=plan_index<len(plans):raise BridgeError('方案索引无效')
    plan=plans[plan_index]
    if plan.get('pending_count')!=0 or performer_id not in plan.get('member_ids',[]):
        raise BridgeError('参与者条件未齐备或不在当前方案中')
    if not isinstance(agreement_id,str) or not agreement_id.strip():raise BridgeError('缺少约定标识')
    if performer_id==need.get('owner_id'):raise BridgeError('负责人和承担者需区分')
    byid={r['id']:r for r in need['requirements']}
    mine=[a for a in plan['assignments'] if a['person_id']==performer_id]
    persons=[p for p in packet['candidates'] if p['id']==performer_id]
    if len(persons)!=1 or not mine:raise BridgeError('缺少本人的任务或可用工时')
    available=persons[0]['hours_per_week']
    budget=sum(a['hours'] for a in mine)
    if not positive(available) or not positive(budget) or budget>available+1e-9:
        raise BridgeError('本人同一周累计工时超出可用工时')
    snapshot=current.get('reviewed_snapshot',{})
    if digest(snapshot)!=need.get('provenance',{}).get('source_draft_sha256'):
        raise BridgeError('缺少与需求审核指纹对应的原始快照')
    source='\n'.join(f.get('quote','') for k,f in snapshot.get('fields',{}).items() if k in ('goal','problem','task','acceptance','onboarding_owner','input_materials','dependencies','execution_readiness') and isinstance(f,dict) and f.get('status')=='explicit')
    support=snapshot.get('learning_support',{}).get('quote','')
    context={'agreement_id':agreement_id,'need_id':need['id'],'need_version':need['need_version'],
        'owner_id':need['owner_id'],'performer_id':performer_id,'available_hours':budget,
        'time_window':need['week_start']+'至'+need['week_end']+'（仅这一周的任务预算，非全项目总工时）',
        'tasks':[{'id':a['task_id'],'text':byid[a['task_id']]['text'],'hours':a['hours']} for a in mine],
        'source_text':source+'\n'+support+'\n本次确认的阶段工作时段为'+need['week_start']+'至'+need['week_end']+'，不是全项目最终截止日期。',
        'provenance':copy.deepcopy(need['provenance']),
        'planning_provenance':copy.deepcopy(provenance),'source_team_sha256':digest(packet)}
    return {'module':'agreement','context':context}


import json,datetime,math
def _filter(arg1: str,arg2: str):
    def dump(x): return json.dumps(x,ensure_ascii=False)
    def stop(msg,excluded=None):
        packet={"schema_version":"team_demo_0.1","route":"blocked","reason":msg,"excluded":excluded or []}
        details="\n".join(str(p.get("name",p.get("id","候选")))+"："+ "；".join(p.get("reasons",[])) for p in (excluded or []))
        return {"route":"blocked","payload":dump(packet),"result":"# 研织｜组队暂未进入评估\n"+msg+("\n\n"+details if details else "")+"\n本轮没有生成正式团队或联系任何人。","excluded":dump(excluded or [])}
    def text(x,n=160):
        return x.strip()[:n] if isinstance(x,str) else ""
    def num(x):
        return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and 0<=x<=168
    def date(x):
        return datetime.date.fromisoformat(x)
    try:
        need=json.loads(arg1); people=json.loads(arg2)
        if not isinstance(need,dict) or not isinstance(people,list): return stop("需求应为JSON对象，候选应为JSON数组。")
        if not 1<=len(people)<=10: return stop("本版每次评估1至10名候选；不静默截断。")
        if need.get("status")!="open": return stop("需求尚未开放或已结束，请先核对需求状态。")
        if need.get("owner_confirmed") is not True: return stop("需求条件尚未确认，先保留为探索草稿。")
        reqs=need.get("requirements")
        if not isinstance(reqs,list) or not 1<=len(reqs)<=6: return stop("需提供1至6项有ID的任务要求。")
        ids=set()
        for r in reqs:
            if not isinstance(r,dict) or not text(r.get("id"),50) or not text(r.get("text"),500): return stop("任务要求缺少ID或具体描述。")
            if r["id"] in ids: return stop("任务要求ID重复。")
            ids.add(r["id"])
            for k in ["must","allow_adjacent","independent_required"]:
                if not isinstance(r.get(k),bool): return stop("每项要求需明确must、allow_adjacent和independent_required布尔值。")
            r["text"]=text(r["text"],500)
        if need.get("period")!="one_week": return stop("本版只处理同一周的工时分配，period需为one_week。")
        if not isinstance(need.get("max_people"),int) or isinstance(need["max_people"],bool) or not 1<=need["max_people"]<=3: return stop("参与分配人数上限为1至3人。")
        if not any(r["must"] for r in reqs): return stop("至少需要一项必需任务。")
        for r in reqs:
            if not num(r.get("hours")) or r["hours"]<=0: return stop("每项任务需有同一周内大于0的预计工时。")
        existing=need.get("existing_member_ids",[])
        if not isinstance(existing,list) or any(not isinstance(x,str) for x in existing): return stop("已有成员ID格式异常。")
        start=date(need["start_date"])
        if need.get("expires_date") and date(need["expires_date"])<datetime.date.today(): return stop("需求已过期，请重新确认。")
        loc=text(need.get("location"))
        if not loc:return stop("请提供线上或明确的场地约束。")
        safe_need={k:need.get(k) for k in ["id","title","status","owner_confirmed","period","max_people","existing_member_ids","start_date","location","expires_date","owner_id","need_version","provenance","planning_provenance","source_matching_need","week_start","week_end","weekly_task_budget","skill_requirements","learning_support"]}
        safe_need["requirements"]=reqs
        safe_need["existing_member_ids"]=existing
        eligible=[]; excluded=[]; pids=set()
        for p in people:
            if not isinstance(p,dict) or not text(p.get("id"),50): return stop("候选缺少有效ID。")
            pid=p["id"]
            if pid in pids: return stop("候选ID重复。")
            pids.add(pid); reasons=[]; pending=[]
            if p.get("visible") is not True: reasons.append("未获本次评估可见授权")
            if p.get("status") in ["unavailable","busy","withdrawn"]: reasons.append("当前不可参与")
            elif p.get("status")!="available": pending.append("当前状态待确认")
            if p.get("intent")=="declined": reasons.append("本人明确不考虑")
            elif p.get("intent")!="interested": pending.append("本人合作意愿待确认")
            h=p.get("hours_per_week")
            if h is None: reasons.append("可投入工时待确认，暂不进行工时分配")
            elif not num(h): return stop("候选工时格式异常。")
            elif h==0: reasons.append("本周没有可分配工时")
            if p.get("available_from"):
                if date(p["available_from"])>start: reasons.append("无法在要求日期前开始")
            else: pending.append("可开始日期待确认")
            ploc=text(p.get("location"))
            if loc!="线上":
                if not ploc: pending.append("场地条件待确认")
                elif ploc!=loc: reasons.append("场地不符")
            if reasons: excluded.append({"id":pid,"name":text(p.get("name")) or pid,"reasons":reasons}); continue
            evs=p.get("evidence",[])
            if not isinstance(evs,list) or len(evs)>3: return stop("每人仅传入最多3条相关证据，不静默截断。")
            cleaned=[]; eids=set()
            for e in evs:
                if not isinstance(e,dict) or not text(e.get("id"),50) or not text(e.get("text"),1600):return stop("证据需有ID及原文。")
                if e["id"] in eids:return stop("同一候选的证据ID重复。")
                eids.add(e["id"])
                cleaned.append({"id":e["id"],"text":text(e["text"],1600),
                   "personal_contribution":e.get("personal_contribution") is True,
                   "student_confirmed":e.get("student_confirmed") is True,
                   "task_scope_accepted":e.get("task_scope_accepted") is True,
                   "support_type":e.get("support_type") if e.get("support_type") in ["provided_excerpt","self_reported","link_only"] else "unknown",
                   "independence":e.get("independence") if e.get("independence") in ["independent","guided"] else "unknown"})
            eligible.append({"id":pid,"name":text(p.get("name")) or pid,"pending":pending,"evidence":cleaned,"hours_per_week":h,"existing_member":pid in existing})
        if any(x not in pids for x in existing): return stop("已有成员必须在本次候选包中有记录，避免虚构现有分工。")
        if not eligible:return stop("本轮候选均未通过状态、授权、工时或场地条件检查。",excluded)
        packet={"schema_version":"team_demo_0.1","need":safe_need,"candidates":eligible,"excluded":excluded,
           "data_mode":"supplied_demo_packet","identity_verified":False,"auto_contact":False}
        return {"route":"ready","payload":dump(packet),"result":"","excluded":dump(excluded)}
    except Exception:
        return stop("输入结构、日期或JSON格式异常，请核对演示数据；没有默认放行。")


import json
def _solve(arg1: str,arg2: str=""):
    d=json.loads(arg1); need=d["need"]; reqs=need["requirements"]
    people={p["id"]:p for p in d["candidates"]}
    matrix={(c["candidate_id"],c["requirement_id"]):c for c in d["matrix"]}
    def safe(x):return str(x or "").replace("\n"," ").replace("|","／")[:1600]
    options={}
    for r in reqs:
        options[r["id"]]=[pid for pid,p in people.items() if p["hours_per_week"]>=r["hours"] and matrix[(pid,r["id"])]["effective"] in ["direct","adjacent"]]
    missing=[r for r in reqs if r["must"] and not options[r["id"]]]
    ordered=sorted(reqs,key=lambda r:(not r["must"],len(options[r["id"]]),-r["hours"],r["id"]))
    best={}; visits=0; complete=True
    def quality(plan):
        return (plan["optional_covered"],plan["direct_count"],-plan["adjacent_count"],-plan["max_utilization"])
    def walk(i,loads,assignments):
        nonlocal visits,complete
        visits+=1
        if visits>250000:complete=False;return
        if i==len(ordered):
            ids=tuple(sorted(loads))
            if not ids:return
            cs=[people[x] for x in ids]
            plan={"member_ids":list(ids),"assignments":list(assignments),"loads":dict(loads),
                "new_people":sum(not p["existing_member"] for p in cs),"team_size":len(ids),
                "pending_count":sum(bool(p["pending"]) for p in cs),
                "optional_covered":sum(not next(r for r in reqs if r["id"]==a["task_id"])["must"] for a in assignments),
                "direct_count":sum(a["support"]=="direct" for a in assignments),
                "adjacent_count":sum(a["support"]=="adjacent" for a in assignments),
                "max_utilization":max(loads[x]/people[x]["hours_per_week"] for x in ids)}
            if ids not in best or quality(plan)>quality(best[ids]):best[ids]=plan
            return
        r=ordered[i]
        for pid in options[r["id"]]:
            current=loads.get(pid,0); total=current+r["hours"]
            if total>people[pid]["hours_per_week"]+1e-9:continue
            if pid not in loads and len(loads)>=need["max_people"]:continue
            cell=matrix[(pid,r["id"])]
            loads[pid]=total
            assignments.append({"task_id":r["id"],"person_id":pid,"hours":r["hours"],"support":cell["effective"],"evidence_id":cell["evidence_id"],"quote":cell["quote"]})
            walk(i+1,loads,assignments)
            assignments.pop()
            if current:loads[pid]=current
            else:loads.pop(pid,None)
            if not complete:return
        if not r["must"]:walk(i+1,loads,assignments)
    if not missing:walk(0,{},[])
    allplans=list(best.values())
    def metrics(p):return (p["pending_count"],p["new_people"],p["team_size"],-p["optional_covered"],-p["direct_count"],p["adjacent_count"])
    def dominates(a,b):
        av=metrics(a);bv=metrics(b)
        return all(x<=y for x,y in zip(av,bv)) and any(x<y for x,y in zip(av,bv))
    frontier=[p for p in allplans if not any(dominates(q,p) for q in allplans)]
    frontier.sort(key=lambda p:(p["pending_count"],p["new_people"],-p["optional_covered"],-p["direct_count"],p["team_size"],p["adjacent_count"],p["member_ids"]))
    chosen=frontier[:3]
    payload={"schema_version":"team_assignment_0.1","need":need,"candidates":d["candidates"],
        "plans":chosen,"feasible_team_sets":len(best),"search_complete":complete,"search_visits":visits,
        "missing_required_ids":[r["id"] for r in missing],"excluded":d["excluded"],"warnings":d["warnings"],
        "status":"proposed" if chosen else ("no_feasible_assignment" if complete else "search_incomplete"),
        "data_mode":"supplied_demo_packet","identity_verified":False,"auto_create_team":False,"auto_contact":False}
    lines=["# 研织｜组队组合与工时分配（演示）","目标："+safe(need.get("title") or need.get("id")),
      "按同一周工时计算，每项任务只分配一名主责人；可以一人承担多项，但累计不得超出其可用工时。参与分配人数最多 "+str(need["max_people"])+" 人。",
      "已有成员优先用于减少新增招募；先满足全部必需项，再比较材料支持、人数、可选项与适应成本。不直接拼个人排行榜。"]
    if need.get('planning_provenance'):
        lines += ['需求版本：'+str(need.get('need_version'))+'；计划周：'+str(need.get('week_start'))+'至'+str(need.get('week_end'))+'。',
          '复用本次匹配已核对的逐动作证据，不再次调用模型判断同一经历；本周分工不是全项目工时承诺。']
    if not chosen:
        lines+=["","## 当前没有可行的完整分工"]
        if missing:lines+=["缺少足够个人证据或单项可用工时的必需任务："]+[safe(r["text"])+"（本周 "+str(r["hours"])+" 小时）" for r in missing]
        elif complete:lines+=["每项必需任务单独都有人可承担，但同时分配时触发累计工时或人数上限；不能把同一人的空闲时间重复使用。"]
        else:lines+=["搜索达到本版计算上限，尚不能宣称没有可行方案。"]
        lines+=["下一步：核对个人任务范围，调整任务工时或人数边界，或补充真正覆盖缺口的候选；系统没有代人承诺。"]
    for n,p in enumerate(chosen,1):
        names="、".join(safe(people[x]["name"]) for x in p["member_ids"])
        lines+=["","## 方案 "+str(n)+"："+names,
          "参与 "+str(p["team_size"])+" 人；其中新增 "+str(p["new_people"])+" 人；直接支持 "+str(p["direct_count"])+" 项，相邻经验 "+str(p["adjacent_count"])+" 项，可选任务覆盖 "+str(p["optional_covered"])+" 项。"]
        for pid in p["member_ids"]:
            person=people[pid]; mine=[a for a in p["assignments"] if a["person_id"]==pid]
            lines+=["","**"+safe(person["name"])+"（"+("已有成员" if person["existing_member"] else "候选新增成员")+"）**",
                "本周拟分配 "+str(round(p["loads"][pid],3))+" / 可用 "+str(person["hours_per_week"])+" 小时，余量 "+str(round(person["hours_per_week"]-p["loads"][pid],3))+" 小时。"]
            for a in mine:
                r=next(r for r in reqs if r["id"]==a["task_id"])
                lines += ["任务："+safe(r["text"])+"；"+str(a["hours"])+" 小时；"+("直接支持" if a["support"]=="direct" else "相邻经验，需适应")+"。",
                  "依据 ["+safe(a["evidence_id"])+"]：“"+safe(a["quote"])+"”"]
            if person["pending"]:lines+=["待确认："+"；".join(safe(x) for x in person["pending"])]
        unassigned=[r["text"] for r in reqs if not r["must"] and r["id"] not in [a["task_id"] for a in p["assignments"]]]
        if unassigned:lines+=["尚未安排的可选任务："+"；".join(safe(x) for x in unassigned)]
        lines+=["方案状态："+("有人意愿或条件待确认，不能直接发起组队。" if p["pending_count"] else "可供相关人复核分工，尚未形成团队。")]
    if chosen:lines+=["","对满足必需项的 "+str(len(best))+" 个可行成员集合进行比较，展示最多3个在人数、新增成员、覆盖与适应成本上不被明显支配的方案；不为凑数增加团队成员。"]
    if not complete:lines+=["计算提示：搜索未完成，当前方案只代表已检查部分，不宣称全局最优。"]
    if d["excluded"]:lines+=["","## 本轮未参与分配"]+[safe(p["name"])+"："+ "；".join(safe(x) for x in p["reasons"]) for p in d["excluded"]]
    if d["warnings"]:lines+=["","校验提示："+"；".join(safe(x) for x in d["warnings"])]
    lines+=["","边界：工时和确认标记来自输入数据包，未核验身份或具体日程交集；不处理任务拆分、复杂并行依赖或真实名额锁定。方案需本人和负责人复核；不会自动联系、邀请或建立团队。"]
    return {"result":"\n".join(lines),"payload":json.dumps(payload,ensure_ascii=False)}



def main(arg1: str,arg2: str):
    def blocked(message):
        packet={'schema_version':'team_demo_0.1','route':'blocked','reason':str(message),'excluded':[]}
        return {'route':'blocked','result':'# 研织｜组队前暂需核对\n'+str(message)+'\n没有创建团队、联系人员或接受约定。','payload':json.dumps(packet,ensure_ascii=False),'excluded':'[]'}
    try:
        envelope=json.loads(arg1)
        if not isinstance(envelope,dict) or envelope.get('module')!='team_from_match':
            return _filter(arg1,arg2)
        people=json.loads(arg2)
        if envelope['current'].get('matching_candidates_sha256')!=digest(people):
            raise BridgeError('候选资料与本次匹配时保存的快照不同，应重新匹配')
        source=envelope['decision_packet']
        if source.get('recommendation_status')!='discussion_draft':raise BridgeError('不是完整匹配结果')
        need=team_from_match(envelope,people)
        checked=_filter(json.dumps(need,ensure_ascii=False),arg2)
        if checked['route']!='ready':return checked
        packet=json.loads(checked['payload'])
        keys={(p['id'],r['id']) for p in packet['candidates'] for r in need['requirements']}
        source_cells=source.get('matrix',[])
        matrix=[]
        for key in sorted(keys):
            found=[c for c in source_cells if (c.get('candidate_id'),c.get('requirement_id'))==key]
            if len(found)!=1:raise BridgeError('上游匹配矩阵有缺项或重复，不能拼出可行分工')
            cell=copy.deepcopy(found[0])
            if cell.get('effective') in ('direct','adjacent'):
                person=next(p for p in packet['candidates'] if p['id']==key[0])
                evidence=[e for e in person['evidence'] if e['id']==cell.get('evidence_id')]
                if len(evidence)!=1:raise BridgeError('匹配引用的证据已缺失')
                e=evidence[0]; checks=cell.get('task_action_checks',[])
                if (not cell.get('quote') or cell['quote'] not in e['text'] or e['support_type']!='provided_excerpt'
                    or not e['personal_contribution'] or not e['student_confirmed'] or not e['task_scope_accepted']
                    or cell.get('task_actions_complete') is not True or not checks
                    or any(c.get('status')!='supported' or not c.get('quote') or c['quote'] not in e['text'] for c in checks)):
                    raise BridgeError('逐动作证据未通过复核，不能升为任务覆盖')
            matrix.append(cell)
        packet.update({'schema_version':'team_matrix_0.2','matrix':matrix,'warnings':source.get('warnings',[]),
            'source_mode':'reused_matching_matrix','identity_verified':False})
        solved=_solve(json.dumps(packet,ensure_ascii=False))
        return {'route':'matched_plan','payload':solved['payload'],'result':solved['result'],'excluded':checked['excluded']}
    except Exception as e:
        return blocked(e)
