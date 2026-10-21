import json
import re

KEYS = ["onboarding_owner", "input_materials", "dependencies", "execution_readiness"]

def main(arg1: str):
    try:
        p = json.loads(arg1)
        if not isinstance(p, dict) or not isinstance(p.get("fields"), dict): raise ValueError()
    except Exception:
        return {"payload":json.dumps({"status":"validation_error"},ensure_ascii=False)}
    if p.get("status") == "validation_error": return {"payload":json.dumps(p,ensure_ascii=False)}
    fields = p["fields"]
    def known(k):
        f = fields.get(k,{})
        return isinstance(f,dict) and f.get("status")=="explicit" and isinstance(f.get("value"),str) and bool(f["value"].strip()) and isinstance(f.get("quote"),str) and bool(f["quote"].strip()) and f.get("verification")=="user_statement_only"
    missing = [k for k in KEYS if not known(k)]
    reasons = []
    if known("onboarding_owner") and not re.search(r"接应|对接|答疑|入门支持|带领.{0,8}上手|帮助.{0,8}上手", fields["onboarding_owner"]["quote"]):
        missing.append("onboarding_owner")
        fields["onboarding_owner"] = {"value":"","status":"unknown","quote":"","source":"not_provided","verification":"not_provided"}
        reasons.append("尚未明确谁承担接应和对接，验收人不能自动代替接应人。")
    readiness = "unknown"
    if known("execution_readiness"):
        value = fields["execution_readiness"]["value"]
        quotes = "；".join(fields[k]["quote"] for k in ["input_materials","dependencies","execution_readiness"] if known(k))
        if re.search(r"不可用|无法提供|不能提供|无法获得|无法取得", quotes):
            readiness = "blocked"
        elif re.search(r"尚未|还未|未就绪|未到位|未落实|未获|未借到|待落实|待授权|待审批|待申请|申请中|审批中|等待|预计.{0,12}(?:借到|获得|取得|拿到)", quotes):
            readiness = "pending"
        elif value == "已就绪" and (re.search(r"已就绪|已经就绪|均已.{0,8}(?:可用|到位|落实|准备好)|全部.{0,8}(?:可用|到位|落实|准备好)", fields["execution_readiness"]["quote"]) or (re.search(r"(?:目前|现在|当前)(?:已)?(?:可以|可|能够)开始", fields["execution_readiness"]["quote"]) and re.search(r"(?:都|均|全部)(?:已经|已)?准备好", quotes))):
            readiness = "ready"
        elif value == "待落实": readiness = "pending"
        elif value == "不可用": readiness = "blocked"
        if readiness != "ready" and "execution_readiness" not in missing: missing.append("execution_readiness")
        if readiness != "ready" and value == "已就绪":
            fields["execution_readiness"] = {"value":"","status":"unknown","quote":"","source":"not_provided","verification":"not_provided"}
            reasons.append("模型的已就绪判断缺少充分原文依据，未作为事实采用。")
    if readiness == "pending": reasons.append("执行条件仍待落实，不能把预计可获得当作已可用。")
    elif readiness == "blocked": reasons.append("资料明确存在不可用的执行条件，应先调整输入或依赖安排。")
    elif readiness == "unknown": reasons.append("尚未明确执行条件是否已经就绪。")
    p["execution_checks"] = {"check_version":"0.1", "missing_fields":list(dict.fromkeys(missing)), "readiness":readiness, "blocking_reasons":reasons, "ready_for_owner_review":not missing and readiness=="ready", "verification":"user_statement_only"}
    return {"payload":json.dumps(p,ensure_ascii=False)}
