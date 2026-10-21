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
