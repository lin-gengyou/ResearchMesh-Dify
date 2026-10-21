"""ResearchMesh versioned agreement domain logic; demo identities, no database writes."""
import copy
import datetime as dt
import hashlib
import json
import re


class AgreementError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def text(value, limit=3000):
    if not isinstance(value, str) or len(value) > limit:
        raise AgreementError("字段必须为长度受限的文本")
    return value.strip()


def number(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and 0 < value <= 168


def extract_field(raw, source, proposal=True):
    """Only an exact quotation plus literal value supports a source claim."""
    if not isinstance(raw, dict):
        return {"value": "", "basis": "unknown", "quote": ""}
    value = text(raw.get("value", ""))
    quote = text(raw.get("quote", ""), 12000)
    basis = raw.get("basis")
    if value and basis == "source" and quote and quote in source and value in quote:
        return {"value": value, "basis": "source", "quote": quote}
    if value and basis == "proposal" and proposal:
        return {"value": value, "basis": "proposal", "quote": ""}
    return {"value": "", "basis": "unknown", "quote": ""}


def material(packet):
    return {k: packet[k] for k in (
        "agreement_id", "version", "need_id", "need_version", "owner_id",
        "performer_id", "terms", "revision_request"
    )}


def seal(packet):
    packet["terms_hash"] = digest(material(packet))
    return packet


def check(packet):
    if packet.get("terms_hash") != digest(material(packet)):
        raise AgreementError("约定内容与快照不符，请重新读取当前版本")


def blockers(packet):
    reasons = []
    if packet["revision_request"]:
        reasons.append("修改尚未整理成新版本")
    if packet.get("revision_errors"):
        reasons.extend(packet["revision_errors"])
    for item in packet["terms"]["deliverables"]:
        if not item["acceptance"]["value"]:
            reasons.append(item["id"] + "尚未约定验收方式")
    return reasons


def build_draft(context, model, version=1):
    """Context is selected-plan data supplied by the caller, never identity proof."""
    c = copy.deepcopy(context)
    for key in ["agreement_id", "need_id", "owner_id", "performer_id"]:
        c[key] = text(c.get(key, ""), 120)
        if not c[key]:
            raise AgreementError("缺少约定、需求或参与者标识")
    if c["owner_id"] == c["performer_id"]:
        raise AgreementError("两种角色不能使用同一参与者标识")
    if type(c.get("need_version")) is not int or c["need_version"] < 1:
        raise AgreementError("缺少有效需求版本")
    if type(version) is not int or version < 1:
        raise AgreementError("无效约定版本")
    source = text(c.get("source_text", ""), 18000)
    tasks = c.get("tasks")
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= 6:
        raise AgreementError("每份约定应有1至6项本人任务")
    ids = []
    total = 0
    for task in tasks:
        task["id"] = text(task.get("id", ""), 80)
        task["text"] = text(task.get("text", ""), 1000)
        if not task["id"] or task["id"] in ids or not task["text"] or not number(task.get("hours")):
            raise AgreementError("任务标识、本人职责或工时无效")
        ids.append(task["id"])
        total += task["hours"]
    budget = c.get("available_hours")
    if not number(budget) or total > budget:
        raise AgreementError("同一合作时段的工时预算未明确或已超出")
    if not isinstance(model, dict):
        model = {}
    generated = model.get("deliverables", [])
    if not isinstance(generated, list):
        generated = []
    deliverables = []
    for task in tasks:
        matches = [x for x in generated if isinstance(x, dict) and x.get("id") == task["id"]]
        raw = matches[0] if len(matches) == 1 else {}
        deliverables.append({"id": task["id"], "text": task["text"], "hours": task["hours"],
                             "acceptance": extract_field(raw.get("acceptance"), source)})
    terms = {"deliverables": deliverables, "total_hours": total,
             "time_window": text(c.get("time_window", ""), 200),
             "due": extract_field(model.get("due"), source, proposal=False),
             "inputs": extract_field(model.get("inputs"), source),
             "support": extract_field(model.get("support"), source, proposal=False),
             "reward": extract_field(model.get("reward"), source, proposal=False),
             "withdrawal": extract_field(model.get("withdrawal"), source),
             "public_contribution": "交付验收后仍由贡献者本人另行授权，默认不公开"}
    if not terms["time_window"]:
        raise AgreementError("必须标明任务与可用工时所属的同一时间段")
    questions = []
    if not terms["due"]["value"]:
        questions.append("希望何时交付？也可以明确约定无固定截止日期。")
    missing = [x["text"] for x in deliverables if not x["acceptance"]["value"]]
    if missing:
        questions.append("这些交付怎么判断完成：" + "、".join(missing))
    packet = {"schema_version": 1, "agreement_id": c["agreement_id"], "version": version,
              "need_id": c["need_id"], "need_version": c["need_version"],
              "owner_id": c["owner_id"], "performer_id": c["performer_id"],
              "terms": terms, "revision_request": "", "context": c,
              "confirmations": {}, "state": "pending_confirmations",
              "events": [], "history": [], "questions": questions[:2], "notes": [],
              "identity_verified": False, "formal_state_update": False,
              "auto_publish": False, "skills_added": []}
    return seal(packet)


def respond(packet, *, role, actor_id, action, expected_version, expected_hash,
            event_id, requested_changes="", note=""):
    """actor_id must be authenticated by a future adapter; here it is a demo input."""
    check(packet)
    p = copy.deepcopy(packet)
    if role not in ["owner", "performer"] or actor_id != p[role + "_id"]:
        raise AgreementError("当前角色与参与者标识不符；这不替代真实鉴权")
    if action not in ["accept", "revise", "decline"]:
        raise AgreementError("无效操作")
    changes = text(requested_changes)
    note = text(note)
    event_id = text(event_id, 160)
    if not event_id:
        raise AgreementError("操作缺少幂等标识")
    request_hash = digest({"role": role, "actor_id": actor_id, "action": action,
                           "version": expected_version, "hash": expected_hash,
                           "changes": changes, "note": note})
    for event in p["events"]:
        if event["id"] == event_id:
            if event["request_hash"] != request_hash:
                raise AgreementError("同一操作标识不能复用到不同选择")
            return p
    if expected_version != p["version"] or expected_hash != p["terms_hash"]:
        raise AgreementError("你看到的约定已过期，请重新查看并确认")
    if p["state"] == "declined":
        raise AgreementError("当前约定已被拒绝，不能继续确认")
    if p["revision_request"]:
        raise AgreementError("修改尚未整理完成，双方均需等待新草稿")
    if action == "revise" and not changes:
        raise AgreementError("请说明需要修改的内容")
    # Nonempty change requests always override an accept click.
    effective = "decline" if action == "decline" else "revise" if changes else action
    if effective == "accept" and blockers(p):
        raise AgreementError("；".join(blockers(p)))
    event = {"id": event_id, "role": role, "actor_id_from_input": actor_id,
             "identity_verified": False, "requested_action": action,
             "effective_action": effective, "version": p["version"],
             "terms_hash": p["terms_hash"], "requested_changes": changes,
             "note": note, "at": now(), "request_hash": request_hash}
    p["events"].append(event)
    if effective == "revise":
        p["history"].append({**material(p), "terms_hash": p["terms_hash"],
                              "confirmations": copy.deepcopy(p["confirmations"]), "state": p["state"]})
        p["version"] += 1
        p["confirmations"] = {}
        p["revision_request"] = changes
        p["state"] = "revision_required"
        return seal(p)
    p["confirmations"][role] = {"choice": effective, "actor_id_from_input": actor_id,
                                "version": p["version"], "terms_hash": p["terms_hash"],
                                "identity_verified": False, "event_id": event_id}
    if effective == "decline":
        p["state"] = "declined"
    else:
        p["state"] = "in_progress_demo" if both_accepted(p) else "pending_confirmations"
    return p


def both_accepted(packet):
    return all(packet["confirmations"].get(role, {}).get("choice") == "accept"
               and packet["confirmations"][role]["version"] == packet["version"]
               and packet["confirmations"][role]["terms_hash"] == packet["terms_hash"]
               for role in ["owner", "performer"])


def redraft(packet, model):
    """One revision keeps its already-incremented version and requires two new choices."""
    check(packet)
    if packet["state"] != "revision_required":
        raise AgreementError("只有修改中的约定可以重新起草")
    context = copy.deepcopy(packet["context"])
    request = packet["revision_request"]
    context["source_text"] += "\n双方待确认的修改意见：" + request
    errors = []
    changes = model.get("task_changes", []) if isinstance(model, dict) else []
    if not isinstance(changes, list):
        changes = []
    seen = set()
    for change in changes:
        if not isinstance(change, dict):
            continue
        task_id = change.get("id")
        tasks = [x for x in context["tasks"] if x["id"] == task_id]
        if len(tasks) != 1 or task_id in seen:
            errors.append("修改引用了未知或重复的任务标识")
            continue
        seen.add(task_id)
        if "hours" in change:
            hours = change["hours"]
            quote = change.get("quote", "")
            numbers = re.findall(r"\d+(?:\.\d+)?", quote) if isinstance(quote, str) else []
            if not number(hours) or not quote or quote not in request or not any(abs(float(n) - hours) < 1e-9 for n in numbers):
                errors.append("工时修改缺少当前修改意见的原文依据")
            else:
                tasks[0]["hours"] = hours
        if "text" in change:
            value = change["text"]
            quote = change.get("quote", "")
            if not isinstance(value, str) or not isinstance(quote, str) or not quote or quote not in request or value not in quote:
                errors.append("职责修改缺少当前修改意见的原文依据")
            else:
                tasks[0]["text"] = text(value, 1000)
    p = build_draft(context, model, version=packet["version"])
    p["notes"] = copy.deepcopy(packet.get("notes", []))
    p["revision_errors"] = errors
    p["history"] = copy.deepcopy(packet["history"])
    p["events"] = copy.deepcopy(packet["events"])
    p["events"].append({"id": "redraft-" + p["terms_hash"], "event": "ai_redraft",
                        "version": p["version"], "terms_hash": p["terms_hash"],
                        "based_on_changes": packet["revision_request"], "at": now(),
                        "identity_verified": False})
    prior = packet["history"][-1]["terms"]
    p["change_summary"] = [key for key in p["terms"] if p["terms"][key] != prior.get(key)]
    return p


def delivery_input(packet, *, current_need_version):
    check(packet)
    if current_need_version != packet["need_version"]:
        raise AgreementError("需求已换版，旧约定不能进入交付")
    if packet["state"] != "in_progress_demo" or not both_accepted(packet) or blockers(packet):
        raise AgreementError("双方尚未确认同一完整版本")
    a = {"id": packet["agreement_id"], "version": packet["version"],
         "current_version": packet["version"], "submission_version": packet["version"],
         "performer_id": packet["performer_id"], "reviewer_id": packet["owner_id"],
         "state": "in_progress", "owner_accepted": True, "performer_accepted": True,
         "deliverables": [{"id": x["id"], "text": x["text"], "acceptance": x["acceptance"]["value"]}
                          for x in packet["terms"]["deliverables"]],
         "agreement_hash": packet["terms_hash"], "identity_verified": False,
         "demo_only": True, "formal_state_update": False}
    return {"agreement_json": canonical(a)}


def render(packet):
    check(packet)
    accepted = packet["state"] == "in_progress_demo"
    suffix = "已获双方确认" if accepted else "尚待双方确认"
    labels = {"source": "原文提供，" + suffix, "proposal": "AI建议，" + suffix, "unknown": "未约定（双方接受此状态）" if accepted else "未约定"}
    lines = ["# 研织｜合作约定" + ("已确认（演示）" if accepted else "草稿"), f"版本 {packet['version']}｜{packet['state']}",
             "只约定本人任务；团队其他成果不计入本人职责。", ""]
    for task in packet["terms"]["deliverables"]:
        field = task["acceptance"]
        lines += [f"- {task['text']}（{task['hours']}小时）",
                  "  验收：" + (field["value"] or "待约定") + "｜" + labels[field["basis"]]]
    lines += ["", "工时所属时段：" + packet["terms"]["time_window"],
              "合计工时：" + str(packet["terms"]["total_hours"])]
    for key, title in [("due", "交付时间"), ("inputs", "提供的输入"), ("support", "接应方式"),
                       ("reward", "回报"), ("withdrawal", "退出方式")]:
        field = packet["terms"][key]
        lines.append(title + "：" + (field["value"] or "未约定") + "｜" + labels[field["basis"]])
    if not packet["terms"]["due"]["value"]:
        lines.append("交付时间尚未约定；接受本版本也表示接受这一未约定状态，系统不会代填日期。")
    if packet.get("revision_diff"):
        lines += ["", "## 本轮条款变更（请核对）"]
        for d in packet["revision_diff"]:
            lines += ["- " + d["label"], "  修改前：" + d["before"], "  修改后：" + d["after"], "  修改依据：" + d["request_quote"]]
    if packet.get("change_summary"):
        lines += ["", "相对旧版本变动的条款：" + "、".join(packet["change_summary"]),
                  "旧版本双方确认已失效，请分别核对完整新版本。"]
    confirmed = [role for role, item in packet["confirmations"].items() if item["choice"] == "accept"]
    lines.append("本版本已确认方：" + ("、".join({"owner":"负责人","performer":"承担者"}.get(role, role) for role in confirmed) or "暂无"))
    if packet["revision_request"]:
        lines += ["", "待处理修改意见：" + packet["revision_request"], "旧确认已失效，需双方重新确认。"]
    if blockers(packet):
        lines += ["", "尚不能进入合作：" + "；".join(blockers(packet))]
    if packet["state"] == "declined":
        lines.append("本轮已拒绝，不产生负面能力评分。")
    lines += ["", "这是角色流程演示，身份未经核验，未写入正式合作库。",
              packet["terms"]["public_contribution"]]
    return "\n".join(lines)

def finish(p):
    state=p['state']
    route='revise' if state=='revision_required' else 'closed' if state=='declined' else 'ready' if state=='in_progress_demo' else 'next'
    if state not in ['declined','revision_required'] and blockers(p):route='blocked'
    a=delivery_input(p,current_need_version=p['need_version'])['agreement_json'] if route=='ready' else ''
    return {'result':render(p),'payload':canonical(p),'route':route,'agreement_json':a}
def invalid(message,raw=''):
    return {'result':'# 研织｜本轮未成立\n'+str(message)+'\n没有代替任何一方接受或写入正式合作。','payload':raw,'route':'closed','agreement_json':''}
def read_model(raw):
    value=str(raw or '').strip()
    if value.startswith('```'):value=re.sub(r'^```(?:json)?\s*|\s*```$','',value)
    return json.loads(value)
FIELD_ALIASES = {
    'due': ['交付','截止','日期','延期','提前','月底','周','号'],
    'inputs': ['输入','数据','文件','材料','提供'],
    'support': ['指导','接应','支持','联系','答疑'],
    'reward': ['报酬','回报','酬劳','工资','元','钱','无偿'],
    'withdrawal': ['退出','终止','取消','不做'],
}
FIELD_LABELS={'acceptance':'验收方式','hours':'工时','text':'本人职责','due':'交付时间','inputs':'提供的输入','support':'接应方式','reward':'回报','withdrawal':'退出方式'}

def apply_requested_patches(packet, model):
    check(packet)
    if packet['state']!='revision_required' or not packet['revision_request']:
        raise AgreementError('当前没有待整理的修改意见')
    if not isinstance(model,dict) or not isinstance(model.get('patches'),list) or not 1<=len(model['patches'])<=12:
        raise AgreementError('AI未提供有效的逐条修改，请保留意见后重新整理')
    p=copy.deepcopy(packet); request=p['revision_request']; seen=set(); diffs=[]
    tasks=p['terms']['deliverables']; context_tasks=p['context']['tasks']
    for patch in model['patches']:
        if not isinstance(patch,dict):raise AgreementError('无效修改项')
        field=patch.get('field'); tid=patch.get('task_id',''); quote=text(patch.get('request_quote',''))
        if field not in FIELD_LABELS or not quote or quote not in request:
            raise AgreementError('修改字段不受支持，或缺少当前修改意见的原文依据')
        key=(tid,field)
        if key in seen:raise AgreementError('同一条款不能重复修改')
        seen.add(key)
        if field in ['acceptance','hours','text']:
            matches=[t for t in tasks if t['id']==tid]
            if len(matches)!=1:raise AgreementError('修改引用了未知任务，不能新增任务')
            task=matches[0]; anchor=text(patch.get('task_anchor',''),1000)
            ordinal=tasks.index(task)+1
            ordinal_alias=['第一项','第二项','第三项','第四项','第五项','第六项'][ordinal-1]
            named=(anchor==tid or anchor==ordinal_alias or (len(anchor)>=2 and anchor in task['text'] and all(anchor not in t['text'] for t in tasks if t['id']!=tid)))
            if not anchor or anchor not in quote or not named:
                raise AgreementError('修改意见未清楚指向该任务，请明确是哪一项；无需填写JSON')
            if field=='acceptance' and not any(w in quote.replace(anchor,'') for w in ['验收','说明','标准','观察','局限','样例','缺失','一致','运行','精简','具体','细化','简单','可用','判断','展示','报告','结论']):
                raise AgreementError('当前意见没有明确要求修改这项任务的验收方式')
            if field=='text' and not any(w in quote for w in ['负责','职责','改做','任务改','改成','改为']):
                raise AgreementError('当前意见没有明确要求改变本人职责')
            label=task['text']+'／'+FIELD_LABELS[field]
        else:
            if tid:raise AgreementError('公共条款不应指定任务')
            if not any(a in quote for a in FIELD_ALIASES[field]):raise AgreementError('修改意见没有提及这个公共条款')
            label=FIELD_LABELS[field]
        value=patch.get('value')
        if field=='hours':
            # Absolute hours only; relative increases/decreases need clarification.
            clauses=[c for c in re.split(r'[；;。！？\n]',quote) if anchor in c]
            hour_scope=clauses[0] if len(clauses)==1 else quote
            def hour_number(raw):
                if re.fullmatch(r'\d+(?:\.\d+)?',raw):return float(raw)
                digits={'零':0,'〇':0,'一':1,'二':2,'两':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}
                total=0;digit=0
                for ch in raw:
                    if ch in digits:digit=digits[ch]
                    elif ch in ['十','百']:total+=(digit or 1)*(10 if ch=='十' else 100);digit=0
                return total+digit
            hour_values=[hour_number(n) for n in re.findall(r'(\d+(?:\.\d+)?|[零〇一二两三四五六七八九十百]+)\s*(?:个)?小时',hour_scope)]
            if not number(value) or len(hour_values)!=1 or abs(hour_values[0]-value)>1e-9 or re.search(r'(?:增加|减少|再加|再减|多加|少做)\s*(?:\d|[一二两三四五六七八九十])',hour_scope):
                raise AgreementError('工时需明确为该任务修改后的总小时数，暂不猜测相对增减')
            before=str(task['hours'])+'小时'; after=str(value)+'小时'; task['hours']=value
            next(t for t in context_tasks if t['id']==tid)['hours']=value
        elif field=='text':
            value=text(value,1000)
            if not value or value not in quote:raise AgreementError('职责变动必须有用户当前原文，不由AI扩展职责')
            before=task['text'];after=value;task['text']=value
            next(t for t in context_tasks if t['id']==tid)['text']=value
        else:
            value=text(value)
            if not value:raise AgreementError('不能把条款静默清空；请明确说明新的约定')
            basis=patch.get('basis')
            if basis=='source' and value in quote:
                replacement={'value':value,'basis':'source','quote':quote}
            elif basis=='proposal' and field in ['acceptance','inputs','withdrawal']:
                replacement={'value':value,'basis':'proposal','quote':''}
            else:raise AgreementError('报酬、时间或支持等事实不能由AI凭空建议')
            previous=task['acceptance'] if field=='acceptance' else p['terms'][field]
            before=previous['value'] or '未约定';after=value
            if field=='acceptance':task['acceptance']=replacement
            else:p['terms'][field]=replacement
        if before!=after:diffs.append({'label':label,'before':before,'after':after,'request_quote':quote})
    total=sum(t['hours'] for t in tasks)
    if total>p['context']['available_hours']:raise AgreementError('修改后超出同一时段可用工时，请先协调分工或预算')
    if not diffs:raise AgreementError('本轮未形成实际条款变动，不能把未处理意见标为完成')
    p['terms']['total_hours']=total
    p['context']['source_text']+='\n本轮待双方重新确认的修改意见：'+request
    p['revision_request']='';p['revision_errors']=[];p['confirmations']={};p['state']='pending_confirmations'
    p['revision_diff']=diffs;p['change_summary']=[d['label'] for d in diffs]
    seal(p)
    p['events'].append({'id':'redraft-'+p['terms_hash'],'event':'ai_patch_redraft','version':p['version'],'terms_hash':p['terms_hash'],'based_on_changes':request,'diff':copy.deepcopy(diffs),'at':now(),'identity_verified':False})
    return p

def main(arg1: str,arg2: str):
    try:return finish(apply_requested_patches(json.loads(arg2),read_model(arg1)))
    except Exception as e:
        r=invalid(e,arg2);r['route']='blocked';r['result']+='\n原条款与修改意见均已保留，没有代替双方确认。';return r
