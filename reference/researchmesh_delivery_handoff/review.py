import json,datetime
def main(arg1: str,arg2: str,arg3: str,arg4: str):
    p=json.loads(arg3);a=p["agreement"];note=str(arg2 or "").strip()[:3000]
    decision={"approve":"accepted","revise":"returned","dispute":"disputed"}.get(arg1,"invalid")
    accepted=decision=="accepted"
    event={"event":"human_review_choice","decision":decision,"note":note,
        "at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"run_id":arg4,
        "agreement_id":a["id"],"agreement_version":a["version"],"snapshot_hash":p["snapshot_hash"],
        "reviewer_id_from_input":a["reviewer_id"],"reviewer_identity_verified":False}
    payload={**p,"review_event":event,"review_decision":decision,"formal_state_update":False,
        "public_authorized":False,"auto_publish":False,"skill_certified":False,"skills_added":[]}
    label={"accepted":"验收者选择通过（流程演示）","returned":"退回补充","disputed":"保留争议","invalid":"操作无效，未推进"}[decision]
    lines=["# 研织｜人工验收记录",label,"约定 "+a["id"]+"｜版本 "+str(a["version"]),
       "说明："+(note or "本次未填写备注。"),"验收选择与AI的提交对应表分开记录；本页不代表身份已核验或真实业务状态已写入。"]
    if accepted:
        lines+=["","## 请贡献者本人核对贡献草稿","仅概括本次约定下的本人工作，不能据此认领团队全部成果或新增技能认证。"]
        for c in p["claims"]:
            lines+=["","- "+c["scope"],"  原文：“"+c["quote"].replace("\n"," ")+"”",
              "  完成方式："+{"independent":"原文自述独立完成","guided":"有指导或教程支持","unknown":"独立程度未说明"}[c["independence"]]]
        if not p["claims"]:lines+=["目前没有可引用的具体个人贡献，请先修改提交说明，不会生成空白公开贡献。"]
        lines+=["","公开与否由本人选择。允许公开也只生成待发布草稿，尚未连接公开主页；有修改请写在下方，将保留为待复核版本。"]
    else:lines+=["","本轮不进入贡献公开确认；退回或争议不会被写成负面能力评分。"]
    return {"route":"accepted" if accepted else "closed","result":"\n".join(lines),"payload":json.dumps(payload,ensure_ascii=False)}

