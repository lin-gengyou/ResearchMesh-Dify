"""Reference backend boundary. Call with authenticated current records, not client flags."""
import json
from cross_app_bridge import BridgeError, delivery_from_completed_outputs

def delivery_with_provenance(outputs, *, current, source_run_id):
    adapter=delivery_from_completed_outputs(outputs,current=current,source_run_id=source_run_id)
    key='agreement_v2_packet' if outputs.get('agreement_v2_route') is not None else 'agreement_packet'
    p=json.loads(outputs[key]); context=p.get('context',{})
    provenance=context.get('provenance',{}); planning=context.get('planning_provenance',{})
    expected={
        'need_id':p['need_id'], 'need_version':p['need_version'],
        'source_review_run_id':provenance.get('source_workflow_run_id'),
        'source_draft_sha256':provenance.get('source_draft_sha256'),
        'source_matching_sha256':planning.get('matching_sha256'),
        'planning_sha256':planning.get('planning_sha256'),
        'source_team_sha256':context.get('source_team_sha256'),
        'allocated_hours':p['terms']['total_hours'], 'time_window':p['terms']['time_window']}
    if any(current.get(k)!=v for k,v in expected.items()):
        raise BridgeError('需求、分工或约定来源已改变，请重读当前记录')
    if p['terms']['total_hours']>context['available_hours']:
        raise BridgeError('本人约定超出已确认时段预算')
    adapter['source_context']=expected
    return adapter
