"""Recheck latest actual DeepSeek profile against current matching code, no model call."""
import copy, importlib.util, json
from pathlib import Path
B=Path(__file__).resolve().parent.parent
def load(name, relative):
    spec=importlib.util.spec_from_file_location(name,B/relative)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
adapter=load('closing_adapter','researchmesh_capability_step7/candidate_adapter.py')
pre=load('closing_pre','researchmesh_need_matching_step11/match_preflight.py')
validate=load('closing_validate','researchmesh_matching_home_step8/match_validate.py')
explore=load('closing_explore','researchmesh_matching_home_step8/exploration_prepare.py')
profile=json.loads((B/'researchmesh_deepseek_migration_step9/capability_flash_result.json').read_text())
clues=json.loads(profile['matching_evidence'])['evidence']
fixture=json.loads((B/'researchmesh_need_matching_step11/live_fixture.json').read_text())
def candidate(outputs=profile):
    return adapter.candidate_from_confirmed_profile(outputs,person_id='CAP-DEMO-14',name='虚构经历参与者',selected_evidence_ids=[clues[0]['id'],clues[1]['id']],participation={'status':'available','intent':'interested','hours_per_week':4,'available_from':'2026-11-01','location':'线上'})
c=candidate();o=pre.main(fixture['need_json'],json.dumps([c],ensure_ascii=False));assert o['route']=='ready'
assert all(e['support_type']=='self_reported' and e['task_scope_accepted'] is False for e in c['evidence'])
assert c['evidence'][0]['independence']=='guided'
packet=json.loads(o['payload']);rows=[]
for i,req in enumerate(packet['need']['requirements']):
    e=c['evidence'][min(i,1)]
    rows.append({'candidate_id':c['id'],'requirement_id':req['id'],'relation':'direct','evidence_id':e['id'],'quote':e['text'],'reason':'合成模型判断，仅测试保守校验','action_checks':[{'action':req['text'],'status':'supported','quote':e['text']}]})
matrix=json.loads(validate.main(json.dumps({'assessments':rows},ensure_ascii=False),o['payload'])['result'])
assert all(x['effective']=='unknown' for x in matrix['matrix'])
discussion=explore.main(json.dumps(matrix,ensure_ascii=False));ep=json.loads(discussion['result'])
assert discussion['route']=='needs_probe'
assert ep['exploration_candidates'] and all(x['counts_as_required_coverage'] is False and x['auto_invite'] is False for x in ep['exploration_candidates'])
negative=[]
for change in ('private','revision','snapshot'):
    p=copy.deepcopy(profile)
    if change in ('private','revision'):p['profile_route']={'private':'private_draft','revision':'revision_requested'}[change]
    else:
        q=json.loads(p['profile_packet']);q['draft_hash']='0'*64;p['profile_packet']=json.dumps(q)
    try:candidate(p)
    except ValueError:negative.append(change)
    else:raise AssertionError(change)
assert len(negative)==3
summary={'status':'passed','source':'actual stage9 DeepSeek capability End output; current stage11 preflight and stage8 validators','new_model_calls':0,'checks':['current profile accepted by matching preflight','self report retained','guided retained','all hard coverage unknown','exploration route available','no automatic invitation','private rejected','revision rejected','snapshot mismatch rejected'],'scope':'local contract recheck; synthetic assessment rows are not AI output; backend must independently authenticate actor and bind exact current authorized profile snapshot'}
(Path(__file__).parent/'capability_link_result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False,indent=2))
