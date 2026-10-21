FIELD_ALIASES = {
    'due': ['交付','截止','日期','延期','提前','月底','周','号'],
    'inputs': ['输入','数据','文件','材料','提供'],
    'support': ['指导','接应','支持','联系','答疑'],
    'reward': ['报酬','回报','酬劳','工资','元','钱','无偿'],
    'withdrawal': ['退出','终止','取消','不做'],
}
FIELD_LABELS={'acceptance':'验收方式','hours':'工时','text':'本人职责','due':'交付时间','inputs':'提供的输入','support':'接应方式','reward':'回报','withdrawal':'退出方式'}

def apply_requested_patches(packet, model):
    check(packet)
    if packet['state']!='revision_required' or not packet['revision_request']:
        raise AgreementError('当前没有待整理的修改意见')
    if not isinstance(model,dict) or not isinstance(model.get('patches'),list) or not 1<=len(model['patches'])<=12:
        raise AgreementError('AI未提供有效的逐条修改，请保留意见后重新整理')
    p=copy.deepcopy(packet); request=p['revision_request']; seen=set(); diffs=[]
    tasks=p['terms']['deliverables']; context_tasks=p['context']['tasks']
    for patch in model['patches']:
        if not isinstance(patch,dict):raise AgreementError('无效修改项')
        field=patch.get('field'); tid=patch.get('task_id',''); quote=text(patch.get('request_quote',''))
        if field not in FIELD_LABELS or not quote or quote not in request:
            raise AgreementError('修改字段不受支持，或缺少当前修改意见的原文依据')
        key=(tid,field)
        if key in seen:raise AgreementError('同一条款不能重复修改')
        seen.add(key)
        if field in ['acceptance','hours','text']:
            matches=[t for t in tasks if t['id']==tid]
            if len(matches)!=1:raise AgreementError('修改引用了未知任务，不能新增任务')
            task=matches[0]; anchor=text(patch.get('task_anchor',''),1000)
            ordinal=tasks.index(task)+1
            ordinal_alias=['第一项','第二项','第三项','第四项','第五项','第六项'][ordinal-1]
            named=(anchor==tid or anchor==ordinal_alias or (len(anchor)>=2 and anchor in task['text'] and all(anchor not in t['text'] for t in tasks if t['id']!=tid)))
            if not anchor or anchor not in quote or not named:
                raise AgreementError('修改意见未清楚指向该任务，请明确是哪一项；无需填写JSON')
            if field=='acceptance' and not any(w in quote.replace(anchor,'') for w in ['验收','说明','标准','观察','局限','样例','缺失','一致','运行','精简','具体','细化','简单','可用','判断','展示','报告','结论']):
                raise AgreementError('当前意见没有明确要求修改这项任务的验收方式')
            if field=='text' and not any(w in quote for w in ['负责','职责','改做','任务改','改成','改为']):
                raise AgreementError('当前意见没有明确要求改变本人职责')
            label=task['text']+'／'+FIELD_LABELS[field]
        else:
            if tid:raise AgreementError('公共条款不应指定任务')
            if not any(a in quote for a in FIELD_ALIASES[field]):raise AgreementError('修改意见没有提及这个公共条款')
            label=FIELD_LABELS[field]
        value=patch.get('value')
        if field=='hours':
            # Absolute hours only; relative increases/decreases need clarification.
            clauses=[c for c in re.split(r'[；;。！？\n]',quote) if anchor in c]
            hour_scope=clauses[0] if len(clauses)==1 else quote
            def hour_number(raw):
                if re.fullmatch(r'\d+(?:\.\d+)?',raw):return float(raw)
                digits={'零':0,'〇':0,'一':1,'二':2,'两':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}
                total=0;digit=0
                for ch in raw:
                    if ch in digits:digit=digits[ch]
                    elif ch in ['十','百']:total+=(digit or 1)*(10 if ch=='十' else 100);digit=0
                return total+digit
            hour_values=[hour_number(n) for n in re.findall(r'(\d+(?:\.\d+)?|[零〇一二两三四五六七八九十百]+)\s*(?:个)?小时',hour_scope)]
            if not number(value) or len(hour_values)!=1 or abs(hour_values[0]-value)>1e-9 or re.search(r'(?:增加|减少|再加|再减|多加|少做)\s*(?:\d|[一二两三四五六七八九十])',hour_scope):
                raise AgreementError('工时需明确为该任务修改后的总小时数，暂不猜测相对增减')
            before=str(task['hours'])+'小时'; after=str(value)+'小时'; task['hours']=value
            next(t for t in context_tasks if t['id']==tid)['hours']=value
        elif field=='text':
            value=text(value,1000)
            if not value or value not in quote:raise AgreementError('职责变动必须有用户当前原文，不由AI扩展职责')
            before=task['text'];after=value;task['text']=value
            next(t for t in context_tasks if t['id']==tid)['text']=value
        else:
            value=text(value)
            if not value:raise AgreementError('不能把条款静默清空；请明确说明新的约定')
            basis=patch.get('basis')
            if basis=='source' and value in quote:
                replacement={'value':value,'basis':'source','quote':quote}
            elif basis=='proposal' and field in ['acceptance','inputs','withdrawal']:
                replacement={'value':value,'basis':'proposal','quote':''}
            else:raise AgreementError('报酬、时间或支持等事实不能由AI凭空建议')
            previous=task['acceptance'] if field=='acceptance' else p['terms'][field]
            before=previous['value'] or '未约定';after=value
            if field=='acceptance':task['acceptance']=replacement
            else:p['terms'][field]=replacement
        if before!=after:diffs.append({'label':label,'before':before,'after':after,'request_quote':quote})
    total=sum(t['hours'] for t in tasks)
    if total>p['context']['available_hours']:raise AgreementError('修改后超出同一时段可用工时，请先协调分工或预算')
    if not diffs:raise AgreementError('本轮未形成实际条款变动，不能把未处理意见标为完成')
    p['terms']['total_hours']=total
    p['context']['source_text']+='\n本轮待双方重新确认的修改意见：'+request
    p['revision_request']='';p['revision_errors']=[];p['confirmations']={};p['state']='pending_confirmations'
    p['revision_diff']=diffs;p['change_summary']=[d['label'] for d in diffs]
    seal(p)
    p['events'].append({'id':'redraft-'+p['terms_hash'],'event':'ai_patch_redraft','version':p['version'],'terms_hash':p['terms_hash'],'based_on_changes':request,'diff':copy.deepcopy(diffs),'at':now(),'identity_verified':False})
    return p

def main(arg1: str,arg2: str):
    try:return finish(apply_requested_patches(json.loads(arg2),read_model(arg1)))
    except Exception as e:
        r=invalid(e,arg2);r['route']='blocked';r['result']+='\n原条款与修改意见均已保留，没有代替双方确认。';return r
