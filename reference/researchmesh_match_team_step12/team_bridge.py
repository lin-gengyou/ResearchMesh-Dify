"""Bridge for fictional regression and future authenticated backend use.
Current records and confirmations are not authenticated by Dify itself.
"""
import copy
import datetime
import math
from review_bridge import BridgeError, digest, check_current_match

def positive(x):
    return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and 0 < x <= 168

def team_from_match(envelope, people):
    packet=envelope.get('decision_packet'); current=envelope.get('current')
    need=check_current_match(packet,current)
    if current.get('latest_matching_sha256') != digest(packet):
        raise BridgeError('匹配结果不是后端当前保存的那一次')
    confirm=envelope.get('planning_confirmation',{})
    planning=confirm.get('planning')
    if not isinstance(planning,dict) or confirm.get('accepted') is not True or confirm.get('actor_id') != need['owner_id']:
        raise BridgeError('指定周的任务工时尚未由负责人核对')
    if confirm.get('need_version') != need['need_version'] or confirm.get('matching_sha256') != digest(packet) or confirm.get('planning_sha256') != digest(planning):
        raise BridgeError('周计划已改变或采用了旧匹配，请重新核对')
    if current.get('planning_sha256') != digest(planning):
        raise BridgeError('周计划不是后端当前保存的确认记录')
    try:
        start=datetime.date.fromisoformat(planning['week_start'])
        if start.isoformat() != planning['week_start'] or start.weekday()!=0 or start<datetime.date.fromisoformat(need['start_date']):raise ValueError()
    except (KeyError,TypeError,ValueError):
        raise BridgeError('请确认不早于需求开始日的周一日期')
    if type(planning.get('max_people')) is not int or not 1<=planning['max_people']<=3:
        raise BridgeError('本版分配人数为1至3人')
    hours=planning.get('task_hours'); reqs=need['requirements']
    if not isinstance(hours,list) or len(hours)!=len(reqs) or any(not isinstance(r,dict) for r in hours):
        raise BridgeError('周计划必须逐项保留当前任务及工时')
    ids=[r.get('id') for r in hours]
    if len(set(ids))!=len(ids) or set(ids)!={r['id'] for r in reqs} or any(not positive(r.get('hours')) for r in hours):
        raise BridgeError('周任务标识重复、遗漏或工时无效')
    budget=planning.get('weekly_task_budget')
    if not positive(budget) or sum(r['hours'] for r in hours)>budget+1e-9:
        raise BridgeError('本周任务超过明确确认的本周任务预算')
    candidates=packet.get('candidates',[])
    allowed={p['id'] for p in candidates}
    if not isinstance(people,list) or not people or any(not isinstance(p,dict) or p.get('id') not in allowed for p in people):
        raise BridgeError('候选包包含未在本次匹配中评估的人')
    if len({p['id'] for p in people})!=len(people):raise BridgeError('候选标识重复')
    existing=planning.get('existing_member_ids',[])
    if not isinstance(existing,list) or len(set(existing))!=len(existing) or any(pid not in {p['id'] for p in people} for pid in existing):
        raise BridgeError('已有成员必须有本次授权候选记录')
    hourmap={r['id']:r['hours'] for r in hours}
    result=copy.deepcopy(need)
    result.update({'period':'one_week','start_date':start.isoformat(),'week_start':start.isoformat(),
        'week_end':(start+datetime.timedelta(days=6)).isoformat(),
        'weekly_task_budget':budget,'max_people':planning['max_people'],'existing_member_ids':existing,
        'source_matching_need':copy.deepcopy(need),
        'planning_provenance':{'matching_sha256':digest(packet),'planning_sha256':digest(planning),
            'need_version':need['need_version'],'mode':'matched_week_plan_demo'},
        'requirements':[{**copy.deepcopy(r),'hours':hourmap[r['id']]} for r in reqs]})
    return result

def agreement_from_team(packet, *, current, plan_index, performer_id, agreement_id):
    """Build one person's one-week draft; never accept it or multiply weekly hours."""
    if not isinstance(packet,dict) or packet.get('status')!='proposed':
        raise BridgeError('组队尚无可供复核的方案')
    need=packet.get('need',{}); provenance=need.get('planning_provenance',{})
    check_current_match({'need':need.get('source_matching_need')},current)
    if provenance.get('planning_sha256')!=current.get('planning_sha256') or provenance.get('matching_sha256')!=current.get('latest_matching_sha256'):
        raise BridgeError('组队所据周计划或匹配已改变')
    if current.get('latest_team_sha256')!=digest(packet):raise BridgeError('组队方案不是后端当前保存的那一版')
    plans=packet.get('plans',[])
    if type(plan_index) is not int or not 0<=plan_index<len(plans):raise BridgeError('方案索引无效')
    plan=plans[plan_index]
    if plan.get('pending_count')!=0 or performer_id not in plan.get('member_ids',[]):
        raise BridgeError('参与者条件未齐备或不在当前方案中')
    if not isinstance(agreement_id,str) or not agreement_id.strip():raise BridgeError('缺少约定标识')
    if performer_id==need.get('owner_id'):raise BridgeError('负责人和承担者需区分')
    byid={r['id']:r for r in need['requirements']}
    mine=[a for a in plan['assignments'] if a['person_id']==performer_id]
    persons=[p for p in packet['candidates'] if p['id']==performer_id]
    if len(persons)!=1 or not mine:raise BridgeError('缺少本人的任务或可用工时')
    available=persons[0]['hours_per_week']
    budget=sum(a['hours'] for a in mine)
    if not positive(available) or not positive(budget) or budget>available+1e-9:
        raise BridgeError('本人同一周累计工时超出可用工时')
    snapshot=current.get('reviewed_snapshot',{})
    if digest(snapshot)!=need.get('provenance',{}).get('source_draft_sha256'):
        raise BridgeError('缺少与需求审核指纹对应的原始快照')
    source='\n'.join(f.get('quote','') for k,f in snapshot.get('fields',{}).items() if k in ('goal','problem','task','acceptance','onboarding_owner','input_materials','dependencies','execution_readiness') and isinstance(f,dict) and f.get('status')=='explicit')
    support=snapshot.get('learning_support',{}).get('quote','')
    context={'agreement_id':agreement_id,'need_id':need['id'],'need_version':need['need_version'],
        'owner_id':need['owner_id'],'performer_id':performer_id,'available_hours':budget,
        'time_window':need['week_start']+'至'+need['week_end']+'（仅这一周的任务预算，非全项目总工时）',
        'tasks':[{'id':a['task_id'],'text':byid[a['task_id']]['text'],'hours':a['hours']} for a in mine],
        'source_text':source+'\n'+support+'\n本次确认的阶段工作时段为'+need['week_start']+'至'+need['week_end']+'，不是全项目最终截止日期。',
        'provenance':copy.deepcopy(need['provenance']),
        'planning_provenance':copy.deepcopy(provenance),'source_team_sha256':digest(packet)}
    return {'module':'agreement','context':context}
