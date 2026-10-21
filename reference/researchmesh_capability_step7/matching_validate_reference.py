import json,re
def main(arg1: str,arg2: str):
    packet=json.loads(arg2)
    text=str(arg1 or "").strip()
    if text.startswith("```"): text=re.sub(r"^\`\`\`(?:json)?\s*|\s*\`\`\`$","",text)
    warnings=[]
    try:
        data=json.loads(text)
        rows=data.get("assessments",[])
        if not isinstance(rows,list): raise ValueError()
    except Exception:
        rows=[];warnings.append("AI结果格式异常；所有未核对单元格保留未知。")
    allowed={(p["id"],r["id"]) for p in packet["candidates"] for r in packet["need"]["requirements"]}
    groups={}
    for row in rows:
        if not isinstance(row,dict):continue
        key=(row.get("candidate_id"),row.get("requirement_id"))
        if key not in allowed:
            warnings.append("AI返回未知候选或要求ID，已排除。"); continue
        groups.setdefault(key,[]).append(row)
    matrix=[]
    for p in packet["candidates"]:
        evs={e["id"]:e for e in p["evidence"]}
        for r in packet["need"]["requirements"]:
            key=(p["id"],r["id"]); arr=groups.get(key,[])
            cell={"candidate_id":p["id"],"requirement_id":r["id"],"relation":"unknown",
                  "effective":"unknown","evidence_id":"","quote":"","reason":"缺少可核对的逐项判断"}
            if len(arr)!=1:
                if len(arr)>1:cell["reason"]="该单元格重复判断，保留未知"
                matrix.append(cell);continue
            row=arr[0]; rel=row.get("relation")
            if rel not in ["direct","adjacent","unsupported","unknown"]:
                cell["reason"]="判断类型无效";matrix.append(cell);continue
            e=evs.get(row.get("evidence_id"))
            quote=row.get("quote") if isinstance(row.get("quote"),str) else ""
            if not e or len(quote.strip())<4 or quote not in e["text"]:
                cell["reason"]="没有可定位的授权证据片段";matrix.append(cell);continue
            cell.update({"relation":rel,"evidence_id":e["id"],"quote":quote[:1600],
                         "reason":str(row.get("reason") or "")[:360]})
            if rel=="unsupported":
                cell["effective"]="unsupported"
            elif rel in ["direct","adjacent"]:
                if not e["personal_contribution"]:
                    cell["reason"]="仅有团队成果，不能归为本人能力"
                elif e["support_type"]!="provided_excerpt":
                    cell["reason"]="经历可能相关，但只有自述或链接，不计为已确认覆盖"
                elif not e["student_confirmed"] or not e["task_scope_accepted"]:
                    cell["reason"]="本人贡献范围或本次任务证据尚未确认"
                elif r["independent_required"] and e["independence"]!="independent":
                    cell["reason"]="要求独立完成，但材料只支持指导完成或独立程度未知"
                elif rel=="adjacent" and not r["allow_adjacent"]:
                    cell["reason"]="属于相邻经验，该要求未允许替代"
                else: cell["effective"]=rel
            matrix.append(cell)
    result={"schema_version":"match_matrix_0.1","need":packet["need"],
       "candidates":[{"id":p["id"],"name":p["name"],"pending":p["pending"]} for p in packet["candidates"]],
       "matrix":matrix,"excluded":packet["excluded"],"warnings":list(dict.fromkeys(warnings)),
       "source_mode":"supplied_demo_packet","identity_verified":False}
    return {"result":json.dumps(result,ensure_ascii=False)}

