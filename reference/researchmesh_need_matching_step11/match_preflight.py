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


import json,datetime,math
def main(arg1: str,arg2: str):
    def dump(x): return json.dumps(x,ensure_ascii=False)
    def stop(msg,excluded=None):
        packet={"schema_version":"match_demo_0.1","route":"blocked","reason":msg,"excluded":excluded or []}
        return {"route":"blocked","payload":dump(packet),"result":"# 研织｜匹配暂未进入AI评估\n"+msg+"\n本轮没有推荐或联系任何人。","excluded":dump(excluded or [])}
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
        if need.get("module")=="review_handoff":
            try: need=prepare_review_need(need.get("handoff"),need.get("confirmation"),need.get("current"))
            except BridgeError as e: return stop(str(e))
        if need.get("status")!="open": return stop("需求尚未开放或已结束，请先核对需求状态。")
        if need.get("owner_confirmed") is not True: return stop("需求条件尚未确认，先保留为探索草稿。")
        reqs=need.get("requirements")
        if not isinstance(reqs,list) or not 1<=len(reqs)<=6: return stop("需提供1至6项有ID的任务要求。")
        ids=set()
        for r in reqs:
            if not isinstance(r,dict) or not text(r.get("id"),50) or len(r["id"])>50 or not text(r.get("text"),500) or len(r["text"])>500: return stop("任务要求缺少ID或具体描述。")
            if r["id"] in ids: return stop("任务要求ID重复。")
            ids.add(r["id"])
            for k in ["must","allow_adjacent","independent_required"]:
                if not isinstance(r.get(k),bool): return stop("每项要求需明确must、allow_adjacent和independent_required布尔值。")
            r["text"]=text(r["text"],500)
        if not num(need.get("hours_per_week")) or need["hours_per_week"]==0: return stop("每周预计工时需为0至168之间的正数。")
        start=date(need["start_date"])
        if need.get("expires_date") and date(need["expires_date"])<datetime.date.today(): return stop("需求已过期，请重新确认。")
        loc=text(need.get("location"))
        if not loc:return stop("请提供线上或明确的场地约束。")
        safe_need={k:need.get(k) for k in ["id","title","status","owner_confirmed","hours_per_week","start_date","location","expires_date","owner_id","need_version","provenance","skill_requirements","requirements_policy","learning_support"]}
        safe_need["requirements"]=reqs
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
            if h is None: pending.append("可投入工时待确认")
            elif not num(h): return stop("候选工时格式异常。")
            elif h<need["hours_per_week"]: reasons.append("每周可投入工时不足")
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
            eligible.append({"id":pid,"name":text(p.get("name")) or pid,"pending":pending,"evidence":cleaned})
        if not eligible:return stop("本轮候选均未通过状态、授权、工时或场地条件检查。",excluded)
        packet={"schema_version":"match_demo_0.1","need":safe_need,"candidates":eligible,"excluded":excluded,
           "data_mode":"supplied_demo_packet","identity_verified":False,"auto_contact":False}
        packet['assessment_slots']=[{'candidate_id':p['id'],'requirement_id':r['id']} for p in eligible for r in reqs]
        packet['expected_assessment_count']=len(packet['assessment_slots'])
        return {"route":"ready","payload":dump(packet),"result":"","excluded":dump(excluded)}
    except Exception:
        return stop("输入结构、日期或JSON格式异常，请核对演示数据；没有默认放行。")

