import json
import re

LABELS = {"goal":"项目目标", "existing_team":"已说明的成员能力", "project_stage":"当前进度", "project_duration":"项目整体周期", "problem":"当前困难", "task":"协作职责/任务", "deliverable":"交付物", "acceptance":"验收方式", "deadline":"任务截止/周期", "time_commitment":"明确投入安排", "onboarding_owner":"接应与对接人", "input_materials":"可提供的输入材料", "dependencies":"前置条件", "execution_readiness":"条件可用状态"}

def main(arg1: str, arg2: str, arg3: str = ""):
    arg2 = arg2 if isinstance(arg2, str) else ""
    arg3 = arg3 if isinstance(arg3, str) else ""
    def has_quote(q):
        return q in arg2 or q in arg3
    def error(message):
        p = {"schema_version":"0.6", "status":"validation_error", "owner_confirmed":False, "match_ready":False, "auto_publish":False, "errors":[message]}
        return {"result":"负责人审核稿：" + message + "；未创建需求。", "public_preview":"当前草稿不可展示。", "payload":json.dumps(p, ensure_ascii=False)}
    try:
        raw = arg1.strip()
        if raw.startswith(chr(96) * 3):
            raw = raw.split("\n",1)[1].rsplit(chr(96)*3,1)[0].strip()
        data = json.loads(raw)
        if not isinstance(data,dict) or not isinstance(data.get("fields"),dict):
            return error("模型输出结构异常")
    except Exception:
        return error("模型未返回合法JSON，请重试")
    warnings, facts, suggested, unknowns, clean = [], [], [], [], {}
    conflicts = []
    reported = data.get("unresolved_conflicts", [])
    reported = list(reported) if isinstance(reported, list) else []
    def weekly_mentions(source):
        rows = []
        for clause in re.split(r"[。；;！？!?\n]", source):
            for match in re.finditer(r"每周[^0-9。；;！？!?\n]{0,24}([0-9]+(?:\.[0-9]+)?)\s*(?:小时|钟头|h)", clause, re.I):
                quote = match.group(0)
                kind = "upper" if re.search(r"上限|最多|不超过|至多|不多于", quote) else "lower" if re.search(r"至少|下限|不少于", quote) else "estimate" if re.search(r"预计|大约|约", quote) else "exact"
                correction = bool(re.search(r"更正|改为|改成|调整为|以此为准", clause))
                rows.append({"value":float(match.group(1)),"quote":quote,"kind":kind,"correction":correction})
        return rows
    old_hours, new_hours = weekly_mentions(arg2), weekly_mentions(arg3)
    old_values = {(x["value"], x["kind"]) for x in old_hours}
    new_values = {(x["value"], x["kind"]) for x in new_hours}
    if len(old_values) == 1 and len(new_values) == 1 and not any(x["correction"] for x in new_hours):
        old_value, old_kind = next(iter(old_values))
        new_value, new_kind = next(iter(new_values))
        if old_kind == new_kind and old_value != new_value:
            reported.insert(0, {"field":"time_commitment","original_quote":old_hours[0]["quote"],"supplement_quote":new_hours[0]["quote"]})

    seen_conflicts = set()
    for c in (reported if isinstance(reported, list) else [])[:12]:
        if not isinstance(c, dict): continue
        key = c.get("field", "")
        if key not in LABELS and key != "need_type": continue
        if key in seen_conflicts: continue
        seen_conflicts.add(key)
        oq, sq = c.get("original_quote", ""), c.get("supplement_quote", "")
        checked = isinstance(oq, str) and isinstance(sq, str) and bool(oq.strip()) and bool(sq.strip()) and oq in arg2 and sq in arg3
        label = LABELS.get(key, "合作方式")
        item = {"field":key, "question":"关于" + label + "，原始需求与补充说明不一致，请明确采用哪一种安排。", "evidence_checked":checked, "original_quote":oq if checked else "", "supplement_quote":sq if checked else ""}
        conflicts.append(item)
        warnings.append(label + ("存在未解决的原始/补充冲突，须先确认。" if checked else "被模型标为冲突但引用无法核对，已转未知并要求确认。"))
        if key == "need_type":
            data["need_type"], data["need_type_quote"] = "unclear", ""
        else:
            data["fields"][key] = {"value":"", "status":"unknown", "quote":""}
    for key,label in LABELS.items():
        x = data["fields"].get(key,{})
        if not isinstance(x,dict): x = {}
        v,q,s = x.get("value",""),x.get("quote",""),x.get("status","unknown")
        if not isinstance(v,str) or not isinstance(q,str) or s not in ("explicit","suggested","unknown"):
            v,q,s = "","","unknown"
        if s == "explicit" and (not v.strip() or not q.strip() or not has_quote(q)):
            warnings.append(label+"原文引用未通过检查，已转待确认。")
            v,q,s = "","","unknown"
        if key == "task" and s == "explicit" and not re.search(r"负责|职责|承担|实现|开发|编写|搭建|设计|测试|采集|标注|识别|检测|输出|分析|处理|接入|调试|训练|优化|完成|读取|检查|清洗|汇总|绘制|统计|撰写|访谈|录入", q):
            warnings.append("招募方向尚未说明具体任务动作，不能把专业方向当作职责。")
            v,q,s = "","","unknown"
        if key == "project_duration" and s == "explicit" and not re.search(r"(?:项目|课题|科研|团队).*(?:持续|周期|时长|预计|为期|历时)|(?:持续|周期|时长|预计|为期|历时).*(?:项目|课题|科研)", q):
            v,q,s = "","","unknown"
        if key == "existing_team" and s == "explicit" and re.search(r"调研|选型|采购|购买|立项", q) and not re.search(r"负责|掌握|擅长|熟悉|经验|技能|会使用|会编程|会焊接", q):
            warnings.append("现有资料仅说明调研/选型进度，未证明成员技术能力。")
            v,q,s = "","","unknown"
        if key == "time_commitment" and s == "explicit" and not re.search(r"(?:[0-9一二三四五六七八九十两半]+)\s*(?:小时|钟头|h|天|次)|周[一二三四五六日天].*(?:上午|下午|晚上)", q, re.I):
            warnings.append("投入表述尚不具体，不能用于工时匹配。")
            v,q,s = "","","unknown"
        if s == "explicit" and key in ("time_commitment", "deadline", "project_duration"):
            v = q.strip()
        if s == "unknown": v,q = "",""
        if s == "suggested": q = ""
        clean[key] = {"value":v,"status":s,"quote":q,"source":("both" if s == "explicit" and q in arg2 and q in arg3 else "supplement" if s == "explicit" and q in arg3 else "original" if s == "explicit" else "not_provided"),"verification":("user_statement_only" if s == "explicit" else "ai_suggestion" if s == "suggested" else "not_provided")}
        if s == "explicit": facts.append("- "+label+"："+v+"\n  依据：“"+q+"”")
        elif s == "suggested" and v.strip(): suggested.append("- "+label+"："+v+"（AI建议，待确认）")
        else: unknowns.append(label)
    need_type = data.get("need_type","unclear")
    tq = data.get("need_type_quote","")
    if need_type not in ("short_term","long_term","unclear"): need_type = "unclear"
    if need_type != "unclear" and (not isinstance(tq,str) or not tq.strip() or not has_quote(tq)):
        need_type = "unclear"
        warnings.append("合作类型缺少连续原文支持，不能按项目时长推断。")
    if need_type != "unclear":
        mode_cues = {"short_term":r"短期|按.{0,10}(?:任务|交付)|一次性.{0,6}(?:任务|交付|协作)|(?:任务|交付).{0,6}(?:合作|协作)", "long_term":r"长期|持续.{0,16}(?:成员|职责)|团队成员|成员协作"}
        if not re.search(mode_cues[need_type], tq):
            need_type, tq = "unclear", ""
            warnings.append("原文只说明招募方向，没有足够的合作方式依据，已转待确认。")
    if need_type == "unclear": tq = ""
    gaps, gap_lines = [], []
    src_gaps = data.get("capability_gaps",[])
    for g in (src_gaps if isinstance(src_gaps,list) else [])[:8]:
        if not isinstance(g,dict): continue
        skill = g.get("skill","")
        if not isinstance(skill,str) or not skill.strip(): continue
        assessment = g.get("assessment","unknown")
        quote = g.get("quote","")
        reason = g.get("reason","")
        if not isinstance(quote,str): quote = ""
        if not isinstance(reason,str): reason = ""
        if assessment not in ("explicit_gap","inferred_gap","unknown"): assessment = "unknown"
        if assessment == "explicit_gap" and (not quote.strip() or not has_quote(quote)):
            warnings.append(skill+"的引用未通过检查，不作为已确认需求。")
            assessment,quote,reason = "unknown","","引用无法核对，该判断未采纳。"
        if assessment != "explicit_gap": quote = ""
        gaps.append({"skill":skill,"assessment":assessment,"quote":quote,"reason":reason,"owner_confirmed":False})
        tag = {"explicit_gap":"资料明确提出的需求", "inferred_gap":"AI推测，须确认", "unknown":"未知"}[assessment]
        gap_lines.append("- "+skill+"｜"+tag+"："+reason)
    def strings(key,limit):
        v=data.get(key,[])
        return [x for x in v if isinstance(x,str) and x.strip()][:limit] if isinstance(v,list) else []
    questions,risks = strings("questions",4),strings("risk_flags",8)
    required = ["goal","problem","task","time_commitment"]
    if need_type == "short_term": required += ["deliverable","acceptance","deadline"]
    if need_type == "long_term": required += ["project_duration"]
    missing = [k for k in required if clean[k]["status"] != "explicit"]
    if need_type == "unclear": missing.append("need_type")
    if not questions and missing: questions = ["请补充："+"、".join(LABELS.get(k,"合作模式") for k in missing)]
    status = "needs_clarification" if missing or warnings or risks else "ready_for_owner_review"
    state = "需先补充信息，暂不正式匹配" if status == "needs_clarification" else "可提交负责人审核，确认后再匹配"
    type_label = {"short_term":"按任务交付的短期协作", "long_term":"持续承担职责的成员协作", "unclear":"待负责人确认合作模式"}[need_type]
    payload = {"schema_version":"0.6", "status":status,"need_type":need_type,"need_type_quote":tq,"fields":clean,"unresolved_conflicts":conflicts,"has_supplement":bool(arg3.strip()),"capability_gaps":gaps,"questions":questions,"risk_flags":risks,"validation_warnings":warnings,"missing_for_review":missing,"owner_confirmed":False,"match_ready":False,"auto_publish":False,"evidence_check":"quote_presence_only"}
    sections = ["# 项目负责人审核稿", "用途：由提出需求的负责人补充、修改和确认。此稿未发布，未联系候选人。", "状态："+state, "合作模式："+type_label, "## 资料明确说过的内容", "\n".join(facts) or "暂无足够资料。", "## AI建议（未确认）", "\n".join(suggested) or "暂无额外建议。", "## 待确认的能力需求", "\n".join(gap_lines) or "资料不足，不推断技术能力需求。", "## 尚未提供的字段", "、".join(unknowns) or "字段已填写，仍须负责人确认。", "## 优先补充的问题", "\n".join(str(i+1)+". "+q for i,q in enumerate(questions)) or "请负责人核对草稿。", "## 风险与校验", "\n".join("- "+x for x in risks+warnings) or "原文引用存在性检查通过。", "原文声明不等于真实能力认证。未确认前，结构化数据中的match_ready始终为false。"]
    preview = ["# 协作者展示草稿（仅供负责人预览，未发布）", "合作模式："+type_label]
    for key in ("goal","project_stage","task","deliverable","acceptance","project_duration","deadline","time_commitment"):
        f=clean[key]
        if f["status"] == "explicit": preview.append("- "+LABELS[key]+"："+f["value"])
    visible_skills=[g["skill"] for g in gaps if g["assessment"]=="explicit_gap"]
    if visible_skills: preview.append("- 期望能力："+"、".join(visible_skills))
    if status == "needs_clarification": preview.append("信息尚不完整，需负责人补充后再确认发布。")
    return {"result":"\n\n".join(sections),"public_preview":"\n\n".join(preview),"payload":json.dumps(payload,ensure_ascii=False)}
