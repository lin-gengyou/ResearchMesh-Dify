import json,re,hashlib
def main(arg1: str, arg2: str):
    raw = str(arg2 or "")
    def s(x,n=300):
        return str(x or "").strip()[:n]
    def safe(x):
        return s(x,1200).replace("|","／").replace("\n"," ")
    warnings=[]
    try:
        text=str(arg1 or "").strip()
        if text.startswith("```"):
            text=re.sub(r"^\`\`\`(?:json)?\s*|\s*\`\`\`$","",text)
        data=json.loads(text)
        if not isinstance(data,dict): raise ValueError()
    except Exception:
        data={}
        warnings.append("AI结果格式异常，本轮没有生成可使用的能力声明。可保留原描述重试。")
    claims=[]
    items=data.get("claims",[])
    for c in (items if isinstance(items,list) else [])[:6]:
        if not isinstance(c,dict): continue
        quote=s(c.get("quote"),1200)
        label=s(c.get("skill_label"),80)
        scope=s(c.get("claim_scope"),400)
        if not quote or quote not in raw or not label or not scope:
            warnings.append("有一项候选缺少可定位原文，已排除。")
            continue
        who=c.get("attribution")
        if who not in ["personal","team","unknown"]: who="unknown"
        indep=c.get("independence")
        iq=s(c.get("independence_quote"),600)
        if indep not in ["independent","guided"] or not iq or iq not in raw: indep="unknown"; iq=""
        if indep=="independent" and not re.search("独立|自己完成|独自|自行完成|独力",iq):
            indep="unknown"; iq=""
        if indep=="guided" and not re.search("教程|指导|带着|带领|跟着|照着",iq):
            indep="unknown"; iq=""
        if who!="personal": indep="unknown"; iq=""
        typ=c.get("support_type")
        if typ not in ["self_reported","provided_excerpt","link_only"]: typ="self_reported"
        unc=c.get("uncertainties",[])
        unc=[s(x,180) for x in unc[:3] if s(x)] if isinstance(unc,list) else []
        claims.append({"id":"claim_"+str(len(claims)+1),"skill_label":label,"claim_scope":scope,
           "quote":quote,"source_span":{"start":raw.find(quote),"end":raw.find(quote)+len(quote)},
           "attribution":who,"independence":indep,"independence_quote":iq,
           "support_type":typ,"uncertainties":unc,"user_confirmed":False,"externally_verified":False})
    interests=[]
    arr=data.get("learning_interests",[])
    for i in (arr if isinstance(arr,list) else [])[:4]:
        if isinstance(i,dict) and s(i.get("quote"),600) and s(i.get("quote"),600) in raw and s(i.get("label"),80):
            interests.append({"label":s(i["label"],80),"quote":s(i["quote"],600)})
    qs=data.get("questions",[])
    qs=[s(q,220) for q in qs if isinstance(q,str) and s(q)] [:2] if isinstance(qs,list) else []
    payload={"schema_version":"capability_draft_0.1","status":"draft","source_text":raw,
       "claims":claims,"learning_interests":interests,"questions":qs,"warnings":warnings,
       "user_confirmed":False,"identity_verified":False,"skill_certified":False,
       "match_ready":False,"auto_publish":False}
    payload["source_span_unit"]="unicode_codepoint"
    payload["draft_hash"]=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    lines=["# 研织｜个人能力草稿","AI已替你整理一版，可直接更正；以下是候选陈述，不是能力认证。"]
    who_labels={"personal":"本人工作（待本人确认）","team":"团队成果（不能归为本人能力）","unknown":"本人贡献待确认"}
    ind_labels={"independent":"原文自述独立完成","guided":"跟随教程或指导完成","unknown":"独立程度未说明"}
    for c in claims:
        lines += ["","### "+safe(c["skill_label"]),safe(c["claim_scope"]),
           "归属："+who_labels[c["attribution"]]+"；"+ind_labels[c["independence"]]+"。",
           "原文：“"+safe(c["quote"])+"”",
           "材料："+{"self_reported":"经历自述，未外部核验","provided_excerpt":"用户提供的片段，真实性和贡献范围未核验","link_only":"仅有链接，本流程未读取链接内容"}[c["support_type"]]]
        if c["uncertainties"]: lines.append("待核对："+"；".join(safe(x) for x in c["uncertainties"]))
    if not claims: lines+=["","目前还不能形成具体能力声明。可以先说一次你参与过的小事，不必写完整简历。"]
    if interests: lines+=["","### 想学习的方向（不计入现有能力）"]+[safe(x["label"])+"；原文：“"+safe(x["quote"])+"”" for x in interests]
    if qs: lines+=["","### 最多补充两点（知道多少写多少）"]+[str(i+1)+". "+safe(q) for i,q in enumerate(qs)]
    if warnings: lines+=["","校验提示："+"；".join(dict.fromkeys(warnings))]
    lines+=["","可在原描述后写“更正：……”重新运行。当前草稿未确认、未公开；如进入本人核对环节，可选择更正、仅存私有或授权作为匹配线索。"]
    return {"result":"\n".join(lines),"payload":json.dumps(payload,ensure_ascii=False),"route":"review" if claims or interests else "draft_only"}

