import json,re
def main(arg1: str,arg2: str):
    p=json.loads(arg2);s=p["submission"];a=p["agreement"];warnings=[]
    text=str(arg1 or "").strip()
    if text.startswith("```"):text=re.sub(r"^\`\`\`(?:json)?\s*|\s*\`\`\`$","",text)
    try:
        data=json.loads(text)
        if not isinstance(data,dict):raise ValueError()
    except Exception:data={};warnings.append("AI输出格式异常，所有交付项保留待人工核对。")
    def arr(x):return x if isinstance(x,list) else []
    def safe(x,n=1000):return str(x or "").strip().replace("\n"," ").replace("|","／")[:n]
    groups={}
    for x in arr(data.get("criteria")):
        if isinstance(x,dict) and isinstance(x.get("id"),str):groups.setdefault(x["id"],[]).append(x)
    criteria=[]
    for item in a["deliverables"]:
        xs=groups.get(item["id"],[]);state="unclear";quote="";note="没有可核对的AI对应项。"
        if len(xs)==1:
            x=xs[0];q=x.get("quote") if isinstance(x.get("quote"),str) else ""
            st=x.get("status")
            if st in ["described","partial"] and q and q in s:
                state=st;quote=q;note=safe(x.get("note"),350)
            elif st in ["missing","unclear"]:
                state=st;note=safe(x.get("note"),350)
            else:note="AI引用无法定位或格式无效，保留待核对。"
        elif len(xs)>1:note="AI重复对应同一交付项，保留待核对。"
        criteria.append({**item,"status":state,"quote":quote,"note":note})
    claims=[]
    for x in arr(data.get("contributions"))[:5]:
        if not isinstance(x,dict):continue
        q=x.get("quote") if isinstance(x.get("quote"),str) else ""
        if x.get("person_id")!=a["performer_id"] or not q or q not in s or not safe(x.get("scope"),400):
            warnings.append("有一项贡献候选缺少本人ID或连续原文，已排除。");continue
        scope=safe(x["scope"],400);ind=x.get("independence");iq=x.get("independence_quote")
        if ind not in ["independent","guided"] or not isinstance(iq,str) or not iq or iq not in q:ind="unknown";iq=""
        if ind=="independent" and not re.search("独立|独自|自行完成|自己完成",iq):ind="unknown";iq=""
        if ind=="guided" and not re.search("教程|指导|带着|跟着|照着",iq):ind="unknown";iq=""
        if ind!="independent":scope=re.sub("独立|独自|自行完成|自己完成","",scope)
        claims.append({"person_id":a["performer_id"],"scope":scope,"quote":q,"independence":ind,"independence_quote":iq,"user_confirmed":False})
    questions=[safe(x,200) for x in arr(data.get("questions")) if isinstance(x,str) and x.strip()][:2]
    payload={**p,"criteria":criteria,"claims":claims,"questions":questions,"warnings":list(dict.fromkeys(warnings))}
    labels={"described":"提交说明中已描述，尚未核验实物","partial":"仅描述了部分内容","missing":"提交说明未覆盖","unclear":"待人工核对"}
    lines=["# 研织｜交付验收辅助卡","约定 "+safe(a["id"])+"｜版本 "+str(a["version"]),
       "AI只把提交说明对应到约定，未读取外部链接或检测文件、设备、性能。以下不是验收结论。"]
    for c in criteria:
        lines+=["","**"+safe(c["text"])+"**","约定验收标准："+safe(c["acceptance"]),"对应状态："+labels[c["status"]]+"。"+c["note"]]
        if c["quote"]:lines+=["提交原文：“"+safe(c["quote"])+"”"]
    if claims:lines+=["","### 个人贡献候选（尚待本人核对）"]+[safe(c["scope"])+"；原文：“"+safe(c["quote"])+"”" for c in claims]
    if questions:lines+=["","### 建议核对"]+questions
    if warnings:lines+=["","校验提示："+"；".join(payload["warnings"])]
    lines+=["","请由验收者作出通过、退回或保留争议的决定。通过仅记录本次人工选择，不会自动公开贡献、认证技能或代表真实身份核验。"]
    return {"result":"\n".join(lines),"payload":json.dumps(payload,ensure_ascii=False)}

