"""Reference boundary validator. `current` must come from the future app backend.

This module does not authenticate actors, persist state, or call Dify.
"""
import json
from agreement_contract import check,both_accepted,blockers,delivery_input

class BridgeError(ValueError):pass

def delivery_from_completed_outputs(outputs, *, current, source_run_id):
    if not isinstance(outputs,dict) or not isinstance(current,dict):raise BridgeError('缺少工作流输出或权威当前状态')
    branches=[('agreement_route','agreement_packet','agreement_json'),('agreement_v2_route','agreement_v2_packet','agreement_v2_json')]
    active=[b for b in branches if outputs.get(b[0]) is not None]
    if len(active)!=1:raise BridgeError('必须只有一个实际约定结果分支')
    route,packet_key,adapter_key=active[0]
    if outputs[route]!='ready' or not outputs.get(adapter_key):raise BridgeError('当前约定结果不允许进入交付')
    if not isinstance(source_run_id,str) or not source_run_id.strip():raise BridgeError('缺少来源运行标识')
    try:
        p=json.loads(outputs[packet_key]);provided=json.loads(outputs[adapter_key]);check(p)
        if p['state']!='in_progress_demo' or not both_accepted(p) or blockers(p):raise BridgeError('双方没有确认同一完整版本')
        expected={'agreement_id':p['agreement_id'],'need_version':p['need_version'],'agreement_version':p['version'],'terms_hash':p['terms_hash'],'owner_id':p['owner_id'],'performer_id':p['performer_id']}
        if current.get('active') is not True or any(current.get(k)!=v for k,v in expected.items()):raise BridgeError('约定已换版、关闭或参与者不符，请重新读取当前状态')
        adapter=json.loads(delivery_input(p,current_need_version=current['need_version'])['agreement_json'])
        if provided!=adapter:raise BridgeError('交付适配包与已确认约定不一致')
        adapter['source_workflow_run_id']=source_run_id
        return adapter
    except BridgeError:raise
    except (KeyError,ValueError,TypeError) as e:raise BridgeError('约定结果包不完整或摘要不一致') from e
