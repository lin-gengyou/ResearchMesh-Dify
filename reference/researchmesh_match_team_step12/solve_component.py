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

