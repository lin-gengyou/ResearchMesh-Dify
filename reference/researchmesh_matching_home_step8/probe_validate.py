import json,re
def main(arg1:str,arg2:str):
    d=json.loads(arg2);warnings=list(d.get('warnings',[]))
    allowed={(x['candidate_id'],c['requirement_id']):c for x in d.get('exploration_candidates',[]) for c in x['clues']}
    for c in allowed.values():c['probe']=None
    try:
        text=str(arg1 or '').strip()
        if text.startswith('```'):text=re.sub(r'^```(?:json)?\s*|\s*```$','',text)
        model=json.loads(text);rows=model.get('probes',[])
        if not isinstance(rows,list) or len(rows)>3:raise ValueError('讨论建议应为最多3条的列表')
    except (ValueError,TypeError,AttributeError):rows=[];warnings.append('AI讨论建议格式异常，保留经历线索，不生成可执行草稿。')
    groups={}
    for r in rows:
        if not isinstance(r,dict) or not isinstance(r.get('candidate_id'),str) or not isinstance(r.get('requirement_id'),str):
            warnings.append('讨论建议引用格式不符，已排除。');continue
        key=(r['candidate_id'],r['requirement_id'])
        if key not in allowed:warnings.append('讨论建议引用了非探索候选或任务，已排除。');continue
        groups.setdefault(key,[]).append(r)
    def bounded(x,n):return isinstance(x,str) and bool(x.strip()) and len(x)<=n
    for key,values in groups.items():
        if len(values)!=1:warnings.append('同一探索任务返回重复建议，未展示。');continue
        raw=values[0]
        if (raw.get('mode')!='synthetic_discussion' or type(raw.get('minutes')) is not int
          or not 10<=raw['minutes']<=30 or not bounded(raw.get('goal'),180)
          or not bounded(raw.get('success_check'),220) or not isinstance(raw.get('steps'),list)
          or not 1<=len(raw['steps'])<=3 or not all(bounded(s,180) for s in raw['steps'])):
            warnings.append('一条讨论建议格式或时长不符，未展示。');continue
        allowed[key]['probe']={k:raw[k] for k in ('mode','minutes','goal','steps','success_check')}
        allowed[key]['probe'].update({'is_assignment':False,'ai_generated':True,'user_confirmed':False,
          'real_project_delivery':False,'adds_skill_certification':False,
          'constraints':['仅使用模拟或脱敏样例','参与自愿，可拒绝或停止','不自动计入项目交付、评分或能力认证']})
    d['warnings']=list(dict.fromkeys(warnings))
    return {'result':json.dumps(d,ensure_ascii=False)}
