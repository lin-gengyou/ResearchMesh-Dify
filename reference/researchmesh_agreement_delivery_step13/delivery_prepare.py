import json,hashlib,datetime,re
def main(arg1: str,arg2: str):
    def stop(msg):return {"route":"blocked","payload":"{}","result":"# 研织｜本轮交付暂未进入验收\n"+msg+"\n未生成验收结论或公开贡献。"}
    try:
        a=json.loads(arg1);s=str(arg2 or "").strip()
        if not isinstance(a,dict) or not s:return stop("需要约定数据包和本次提交说明。")
        for k in ["id","performer_id","reviewer_id"]:
            if not isinstance(a.get(k),str) or not a[k].strip():return stop("约定缺少ID、提交者或验收者。")
        if a["performer_id"]==a["reviewer_id"]:return stop("提交者与验收者应区分，不能用本人自述代替对方验收。")
        for k in ["version","current_version","submission_version"]:
            if not isinstance(a.get(k),int) or isinstance(a[k],bool) or a[k]<1:return stop("约定和提交需带正整数版本。")
        if not a["version"]==a["current_version"]==a["submission_version"]:return stop("提交对应的约定版本已不一致，请先重新确认约定。")
        if a.get("state")!="in_progress":return stop("约定尚未进行中或已关闭，不能重复生成本轮验收。")
        if a.get("owner_accepted") is not True or a.get("performer_accepted") is not True:return stop("输入中缺少双方对同一版本的接受记录。")
        ds=a.get("deliverables")
        if not isinstance(ds,list) or not 1<=len(ds)<=6:return stop("约定需有1至6项交付物及验收标准。")
        ids=set();clean=[]
        for x in ds:
            if not isinstance(x,dict) or not isinstance(x.get("id"),str) or not x["id"] or x["id"] in ids:return stop("交付项ID缺失或重复。")
            if not isinstance(x.get("text"),str) or not x["text"].strip() or not isinstance(x.get("acceptance"),str) or not x["acceptance"].strip():return stop("交付项需要原约定中的内容和验收标准。")
            ids.add(x["id"]);clean.append({"id":x["id"],"text":x["text"][:600],"acceptance":x["acceptance"][:600]})
        agreement={k:a[k] for k in ["id","version","current_version","submission_version","performer_id","reviewer_id","state","owner_accepted","performer_accepted"]}
        agreement["deliverables"]=clean
        lineage=a.get('source_context')
        if lineage is not None:
            if not isinstance(lineage,dict):return stop('来源上下文应为对象。')
            needed=['need_id','source_review_run_id','time_window']
            if any(not isinstance(lineage.get(k),str) or not lineage[k].strip() or len(lineage[k])>240 for k in needed):return stop('需求来源或时段信息缺失。')
            if type(lineage.get('need_version')) is not int or lineage['need_version']<1:return stop('需求来源版本无效。')
            for k in ['source_draft_sha256','source_matching_sha256','planning_sha256','source_team_sha256']:
                if not isinstance(lineage.get(k),str) or not re.fullmatch(r'[a-f0-9]{64}',lineage[k]):return stop('来源内容指纹无效。')
            hours=lineage.get('allocated_hours')
            if not isinstance(hours,(int,float)) or isinstance(hours,bool) or not 0<hours<=168:return stop('来源阶段工时无效。')
            agreement['source_context']={k:lineage[k] for k in needed+['need_version','source_draft_sha256','source_matching_sha256','planning_sha256','source_team_sha256','allocated_hours']}
        source_hash=a.get("agreement_hash","")
        if source_hash and (not isinstance(source_hash,str) or not re.fullmatch(r"[a-f0-9]{64}",source_hash)):
            return stop("来源约定摘要格式无效，请重新读取已确认版本。")
        if source_hash:agreement["agreement_hash"]=source_hash
        if isinstance(a.get("source_workflow_run_id"),str):agreement["source_workflow_run_id"]=a["source_workflow_run_id"]
        canonical=json.dumps({"agreement":agreement,"submission":s},ensure_ascii=False,sort_keys=True)
        packet={"schema_version":"delivery_0.1","agreement":agreement,"submission":s,
           "snapshot_hash":hashlib.sha256(canonical.encode()).hexdigest(),
           "submitted_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "identity_verified":False,"storage_connected":False,"agreement_hash_verified":False}
        return {"route":"ready","payload":json.dumps(packet,ensure_ascii=False),"result":""}
    except Exception:
        return stop("数据格式异常；不会默认推进到验收。")
