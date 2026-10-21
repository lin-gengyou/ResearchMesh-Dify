"""Demo adapter. Real actor identity/participation must be read by the future backend."""
import json
def candidate_from_confirmed_profile(review_outputs,*,person_id,name,selected_evidence_ids,participation):
    if not isinstance(selected_evidence_ids,list) or not 1<=len(selected_evidence_ids)<=3 or len(set(selected_evidence_ids))!=len(selected_evidence_ids):
        raise ValueError('明确选择1至3条与本次需求有关的经历，不静默截断')
    keys=[k for k in ('matching_evidence','evidence_json') if review_outputs.get(k)]
    if len(keys)!=1:raise ValueError('必须提供唯一的本人确认匹配线索包')
    route=review_outputs.get('profile_route',review_outputs.get('route'))
    if route!='confirmed_matching_clues':raise ValueError('当前本人选择未进入匹配线索状态')
    p=json.loads(review_outputs[keys[0]])
    if p.get('status')!='confirmed_clues_in_demo' or p.get('matching_use_authorized_in_demo') is not True:
        raise ValueError('本人尚未授权作为匹配线索')
    profile=json.loads(review_outputs.get('profile_packet') or review_outputs.get('payload') or '{}')
    if profile.get('draft_hash')!=p.get('source_draft_hash') or profile.get('matching_use_authorized_in_demo') is not True:
        raise ValueError('匹配线索与当前本人确认快照不一致')
    byid={e['id']:e for e in p['evidence']}
    if any(i not in byid for i in selected_evidence_ids):raise ValueError('选择了不属于当前确认快照的经历')
    if not isinstance(person_id,str) or not person_id.strip():raise ValueError('缺少参与者标识')
    evidence=[dict(byid[i]) for i in selected_evidence_ids]
    for e in evidence:e['task_scope_accepted']=False
    return {'id':person_id,'name':name,'visible':True,
      'status':participation.get('status','unknown'),'intent':participation.get('intent','unknown'),
      'hours_per_week':participation.get('hours_per_week'),'available_from':participation.get('available_from'),
      'location':participation.get('location'),'evidence':evidence,
      'identity_verified':False,'demo_only':True,'source_draft_hash':p['source_draft_hash']}
