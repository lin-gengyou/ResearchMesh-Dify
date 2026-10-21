import json
def main(arg1: str,arg2: str=""):
    d=json.loads(arg1)
    rs=d["need"]["requirements"]; byid={r["id"]:r for r in rs}
    rows=[]; label={"direct":"材料直接支持","adjacent":"相邻经验（已允许适应）","unsupported":"材料明确不支持","unknown":"证据或条件待确认"}
    def safe(x):return str(x or "").replace("\n"," ").replace("|","／")[:1600]
    for p in d["candidates"]:
        cells=[c for c in d["matrix"] if c["candidate_id"]==p["id"]]
        gaps=[byid[c["requirement_id"]]["text"] for c in cells if byid[c["requirement_id"]]["must"] and c["effective"] not in ["direct","adjacent"]]
        counts={k:sum(c["effective"]==k for c in cells) for k in label}
        state="需补足必需项" if gaps else ("合作条件待确认" if p["pending"] else "可优先进行有限讨论")
        rows.append({**p,"cells":cells,"must_gaps":gaps,"counts":counts,"status":state})
    rows.sort(key=lambda p:(bool(p["pending"]),len(p["must_gaps"]),-p["counts"]["direct"],p["counts"]["adjacent"],p["id"]))
    lines=["# 研织｜供需匹配解释（数据包演示）",
       "需求："+safe(d["need"].get("title") or d["need"].get("id")),
       "这是单人任务候选比较，不把多人能力直接拼成已成立团队。确认标记来自本次输入，尚无真实人员库和身份核验。",
       "排序先考虑合作条件是否待确认、必需项缺口，再比较直接证据覆盖与适应成本；不输出成功概率。"]
    exploration=d.get("exploration_candidates",[])
    if exploration:
        lines += ["", "## 可探索的经历线索", "以下经历与任务可能相关，但尚未满足已核对材料或任务范围条件。可先讨论做法，不代表能直接承担。"]
        for candidate in exploration:
            lines += ["", "### "+safe(candidate["name"])]
            for clue in candidate["clues"]:
                lines += ["相关任务："+safe(clue["task"]),"AI关联理由："+safe(clue["why_relevant"]),"原文依据：“"+safe(clue["quote"])+"”", "仍待核对："+safe(clue["unresolved"])]
                if clue.get("independence_gap"):lines += [safe(clue["independence_gap"])]
                probe=clue.get("probe")
                if probe:
                    lines += ["可选讨论草稿（约"+str(probe["minutes"])+"分钟）："+safe(probe["goal"])]
                    lines += [str(i+1)+". "+safe(step) for i,step in enumerate(probe["steps"])]
                    lines += ["核对点："+safe(probe["success_check"]),"仅使用模拟或脱敏样例；可拒绝或停止，不计项目交付、评分或能力认证。"]
            if candidate["pending_conditions"]:lines += ["开始讨论前先确认："+"；".join(safe(x) for x in candidate["pending_conditions"])]
        lines += ["", "## 已核对材料与任务缺口"]
    for n,p in enumerate(rows,1):
        ct=p["counts"]
        lines+=["","## "+str(n)+". "+safe(p["name"])+"｜"+p["status"],
            "直接支持 "+str(ct["direct"])+" 项；相邻经验 "+str(ct["adjacent"])+" 项；未知 "+str(ct["unknown"])+" 项；明确不支持 "+str(ct["unsupported"])+" 项。"]
        for c in p["cells"]:
            r=byid[c["requirement_id"]]
            lines+=["","**"+("必需" if r["must"] else "可选")+"："+safe(r["text"])+"**",
               "判断："+label[c["effective"]]+"。"+safe(c["reason"])]
            if c["quote"]:lines+=["依据 ["+safe(c["evidence_id"])+"]：“"+safe(c["quote"])+"”"]
        if p["pending"]:lines+=["待确认条件："+"；".join(safe(x) for x in p["pending"])]
        if p["must_gaps"]:lines+=["未覆盖的必需项："+"；".join(safe(x) for x in p["must_gaps"]),"下一步：先核对相关个人工作或用有限试任务补充判断，不直接确认能承担。"]
        elif p["pending"]:lines+=["下一步：先确认上述时间或意愿，再由双方决定是否进行有限讨论。"]
        else:lines+=["下一步：双方复核任务范围、材料和时间，再决定是否试协作。"]
    if d["excluded"]:
        lines+=["","## 本轮未进入AI评估"]
        lines += [safe(p["name"])+"："+ "；".join(safe(x) for x in p["reasons"]) for p in d["excluded"]]
    if d["warnings"]:lines+=["","校验提示："+"；".join(safe(x) for x in d["warnings"])]
    lines+=["","证据支持只针对本次任务，不代表能力认证。没有自动联系、邀请、预留名额或形成合作；需求或证据改变后须重新评估。"]
    payload={**d,"ranked_candidates":rows,"recommendation_status":"discussion_draft","has_exploration_clues":bool(exploration),"auto_contact":False,"auto_accept":False,"skill_certified":False}
    return {"result":"\n".join(lines),"payload":json.dumps(payload,ensure_ascii=False)}

