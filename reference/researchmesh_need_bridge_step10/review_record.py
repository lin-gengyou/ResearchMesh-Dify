import json
import hashlib
from datetime import datetime, timezone

LABELS = {"goal":"项目目标","problem":"当前困难","task":"协作职责","deliverable":"交付物/首次里程碑","acceptance":"验收方式","deadline":"截止/首次检查时间","time_commitment":"投入安排","project_duration":"项目整体周期", "onboarding_owner":"接应与对接人", "input_materials":"可提供的输入材料", "dependencies":"前置条件", "execution_readiness":"条件可用状态"}

def requirement_lines(p):
    rows = []
    if p.get("requirements_policy",{}).get("value")=="no_prerequisite": rows.append("- 前置技能：原文明示无前置技能要求")
    for r in p.get("requirements",[]):
        rows.append("- "+r["skill"]+"｜"+{"must_have":"必须已具备","learnable":"允许边做边学","unknown":"必须性待确认"}.get(r.get("necessity"),"待确认")+"；"+{"independent":"需独立完成","guided":"可在指导下完成","unknown":"独立程度待确认"}.get(r.get("independence"),"待确认"))
    s = p.get("learning_support",{})
    label = {"available":"团队声明可提供","unavailable":"团队声明无法提供","unknown":"尚未说明"}.get(s.get("availability"),"尚未说明")
    rows.append("- 学习/指导支持："+label+("；"+s.get("description","") if s.get("description") else ""))
    return rows

def _record_review(arg1: str, arg2: str, arg3: str, arg4: str):
    action = arg1 if isinstance(arg1, str) else ""
    note = arg2.strip() if isinstance(arg2, str) else ""
    now = datetime.now(timezone.utc).isoformat()
    record = {"schema_version":"0.6", "workflow_run_id":arg4, "action_id":action, "review_note":note, "reviewed_at":now, "human_review_confirmed":False, "owner_confirmed":False, "reviewer_identity_verified":False, "match_ready":False, "auto_publish":False}
    def reject(message):
        record["status"] = "review_invalid"
        return {"result":"# 研织 ResearchMesh｜审核未通过检查\n\n" + message + "\n\n本次未确认草稿，未发布、未匹配。", "review_record":json.dumps(record,ensure_ascii=False)}
    try:
        p = json.loads(arg3)
        if not isinstance(p, dict) or not isinstance(p.get("fields"), dict): raise ValueError()
    except Exception:
        return reject("本次待审核资料不可读取，请重新发起需求澄清。")
    if action not in ("approve", "revise"):
        return reject("未收到有效的人工选择，不能替代你确认。")
    if len(note) > 4000:
        return reject("审核备注超过4000字，请精简后重新审核。")
    f = p["fields"]
    required = ["goal","problem","task","deliverable","acceptance","deadline","time_commitment"]
    if p.get("need_type") == "long_term": required.append("project_duration")
    ready = p.get("need_type") in ("short_term","long_term") and not p.get("unresolved_conflicts") and all(isinstance(f.get(k),dict) and f[k].get("status")=="explicit" and isinstance(f[k].get("value"),str) and bool(f[k]["value"].strip()) for k in required)
    checks = p.get("execution_checks", {})
    ready = ready and isinstance(checks,dict) and checks.get("ready_for_owner_review") is True and checks.get("readiness")=="ready"
    ready = ready and all(isinstance(f.get(k),dict) and f[k].get("status")=="explicit" and bool(f[k].get("value")) for k in ["onboarding_owner","input_materials","dependencies","execution_readiness"])
    req_checks = p.get("requirements_checks", {})
    ready = ready and isinstance(req_checks,dict) and req_checks.get("ready_for_owner_review") is True
    if not ready:
        return reject("关键资料仍有缺项或冲突，应先返回需求澄清，不能直接确认。")
    snapshot = {"need_type":p["need_type"],"fields":f,"capability_gaps":p.get("capability_gaps",[]),"execution_checks":checks,"requirements":p.get("requirements",[]),"requirements_policy":p.get("requirements_policy",{}),"learning_support":p.get("learning_support",{}),"requirements_checks":req_checks}
    record["draft_sha256"] = hashlib.sha256(json.dumps(snapshot,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")).hexdigest()
    record["reviewed_snapshot"] = snapshot
    if action == "approve":
        record["status"] = "human_confirmed_in_demo"
        record["human_review_confirmed"] = True
        title, state = "本次草稿已人工确认", "你已在审核表单中确认这一版草稿。该确认只对应本次内容。"
    elif note:
        record["status"] = "revision_requested"
        title, state = "草稿已退回修改", "尚未确认。请按审核意见修改原始需求或补充说明，然后重新运行并审核；旧意见不会自动改写事实字段。"
    else:
        record["status"] = "revision_note_required"
        title, state = "已选择退回，待补修改意见", "尚未确认。没有填写具体修改意见，请补充需要修改的字段及原因后重新发起审核。"
    mode = "按任务交付的短期协作" if p["need_type"]=="short_term" else "持续承担职责的成员协作"
    body = ["# 研织 ResearchMesh｜"+title, state, "合作方式："+mode, "## 本次审核的内容"]
    body += ["- "+label+"："+f[k]["value"] for k,label in LABELS.items() if isinstance(f.get(k),dict) and f[k].get("status")=="explicit"]
    body += ["## 能力要求与支持边界", "\n".join(requirement_lines(p))]
    body += ["## 审核备注", "\n".join("> "+line for line in note.splitlines()) if note else "未填写备注。", "当前为人工审核流程演示，尚未核验负责人身份；不会发布招募、进行匹配或联系候选人。"]
    return {"result":"\n\n".join(body), "review_record":json.dumps(record,ensure_ascii=False)}

def main(arg1: str, arg2: str, arg3: str, arg4: str):
    output = _record_review(arg1, arg2, arg3, arg4)
    record = json.loads(output["review_record"])
    approved = record.get("status") == "human_confirmed_in_demo" and record.get("human_review_confirmed") is True
    packet = {
        "schema_version": "need_matching_handoff_0.1",
        "route": "await_backend_confirmation" if approved else "not_approved",
        "source_workflow_run_id": record.get("workflow_run_id", ""),
        "source_draft_sha256": record.get("draft_sha256", ""),
        "review_status": record.get("status"),
        "review_note": record.get("review_note", ""),
        "identity_verified": False,
        "runnable_matching_input": False,
        "auto_publish": False,
        "auto_contact": False,
    }
    if approved:
        snapshot = record["reviewed_snapshot"]
        packet["reviewed_snapshot"] = snapshot
        packet["pending_backend_fields"] = [
            "authenticated_owner_id", "need_id", "current_need_version",
            "confirmed_start_date", "confirmed_expires_date",
            "confirmed_hours_per_week", "confirmed_location",
            "confirmed_task_requirements"
        ]
        packet["normalization_rules"] = {
            "time": "每周投入与项目总工时分开；不以4小时/周替代总预算。",
            "requirements": "任务职责与前置技能分开；learnable和no_prerequisite不能升级为必须已具备。",
            "confirmation": "AI根据原文预填，负责人核对；未知项保留未知，不要求用户手写JSON。",
            "authority": "后端绑定本次运行、内容指纹和当前需求版本；Dify演示确认不等于身份认证。"
        }
    output["matching_handoff"] = json.dumps(packet, ensure_ascii=False)
    return output
