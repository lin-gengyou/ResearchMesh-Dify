import json,datetime
def main(arg1: str,arg2: str,arg3: str,arg4: str):
    p=json.loads(arg3);correction=str(arg2 or "").strip()[:3000]
    valid=p.get("review_decision")=="accepted" and bool(p.get("claims"))
    if not valid:state="no_confirmable_contribution"
    elif correction or arg1=="revise":state="contribution_needs_revision"
    elif arg1=="public_draft":state="public_draft_authorized_in_demo"
    elif arg1=="private":state="private_contribution_confirmed_in_demo"
    else:state="invalid_action"
    confirmed=state in ["public_draft_authorized_in_demo","private_contribution_confirmed_in_demo"]
    record={"event":"contributor_choice","state":state,"correction":correction,
        "at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"run_id":arg4,
        "performer_id_from_input":p["agreement"]["performer_id"],"identity_verified":False}
    claims=[{**c,"user_confirmed_in_demo":confirmed,"externally_verified":False} for c in p.get("claims",[])]
    payload={**p,"contribution_event":record,"contribution_status":state,"contribution_claims":claims,
      "public_draft_authorized_in_demo":state=="public_draft_authorized_in_demo",
      "auto_publish":False,"formal_state_update":False,"identity_verified":False,"skill_certified":False,"skills_added":[]}
    labels={"no_confirmable_contribution":"没有可确认的个人贡献，未授权公开","contribution_needs_revision":"贡献表述待修改，未授权公开",
       "public_draft_authorized_in_demo":"本人选择允许生成公开草稿（演示）","private_contribution_confirmed_in_demo":"本人选择仅保留私有（演示）","invalid_action":"操作无效，未授权公开"}
    lines=["# 研织｜交付与贡献记录",labels[state],
       "约定 "+p["agreement"]["id"]+"｜版本 "+str(p["agreement"]["version"]),
       "负责人验收选择："+p["review_decision"]+"；与本人的贡献核对及公开选择分开记录。"]
    for c in claims:lines+=["","贡献候选："+c["scope"],"来源：“"+c["quote"].replace("\n"," ")+"”"]
    if correction:lines+=["","本人修改意见（待复核，不覆盖原文）："+correction]
    if confirmed:lines+=["","本次确认仅涉及上述个人贡献范围，不等于掌握全部相关技能或获得能力认证。"]
    lines+=["","当前是本次运行内的演示记录：未核验两种角色身份，尚未写入正式贡献库或公开主页；没有自动发布、添加技能、发消息或改变合作名额。"]
    return {"result":"\n".join(lines),"payload":json.dumps(payload,ensure_ascii=False)}

