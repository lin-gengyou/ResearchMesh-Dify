"""SSE parsing/state reference, with no credentials or network operations."""
import json
from dataclasses import dataclass,field

class EventContractError(ValueError):pass

def sse_events(lines):
    data=[]
    for raw in lines:
        line=raw.rstrip('\r\n')
        if not line:
            if data:yield json.loads('\n'.join(data));data=[]
        elif line.startswith('data:'):
            data.append(line[5:].lstrip(' '))
    # A truncated frame must not be treated as a completed business event.
    if data:raise EventContractError('事件帧未结束，需要重新连接；不得重启同一业务工作流')

AGREEMENT_ROLES={'1792463257417':'owner','1792463915587':'performer','1792478884718':'owner','1792479365090':'performer'}
DELIVERY_ROLES={'1792415339919':'owner','1792416719562':'performer'}
DEMAND_ROLES={'1792335658268':'need_owner','1792384003831':'need_owner'}
CAPABILITY_ROLES={'1792496533023':'profile_owner'}
FORM_ROLES={**AGREEMENT_ROLES,**DELIVERY_ROLES,**DEMAND_ROLES,**CAPABILITY_ROLES}

@dataclass
class RunEvents:
    dify_user:str
    workflow_run_id:str=''
    status:str='running'
    pending_forms:dict=field(default_factory=dict)
    outputs:dict=field(default_factory=dict)
    resolved_nodes:set=field(default_factory=set)
    terminal:bool=False

    def require_form(self,data):
        node_id=data.get('node_id');token=data.get('form_token')
        if node_id in self.resolved_nodes:return
        if node_id not in FORM_ROLES:raise EventContractError('未知人工节点，需要更新角色映射')
        if not token:raise EventContractError('未取得可用于Service API的Webapp表单令牌')
        old=self.pending_forms.get(node_id)
        if old and old['form_token']!=token:raise EventContractError('同一人工节点出现不同表单，需核对最新运行状态')
        self.pending_forms[node_id]={'form_token':token,'role':FORM_ROLES[node_id]}

    def apply(self,event):
        run_id=event.get('workflow_run_id')
        if run_id:
            if self.workflow_run_id and self.workflow_run_id!=run_id:raise EventContractError('不能将不同运行的事件混合')
            self.workflow_run_id=run_id
        kind=event.get('event');data=event.get('data') or {}
        if self.terminal:return
        if kind=='human_input_required':
            self.require_form(data)
            self.status='waiting_for_human' if self.pending_forms else 'running'
        elif kind in ['human_input_form_filled','human_input_form_timeout']:
            self.pending_forms.pop(data.get('node_id'),None)
            self.resolved_nodes.add(data.get('node_id'))
            self.status='waiting_for_human' if self.pending_forms else 'running'
        elif kind=='node_finished' and data.get('node_id') in FORM_ROLES and data.get('status')=='succeeded':
            node_id=data['node_id']
            self.pending_forms.pop(node_id,None)
            self.resolved_nodes.add(node_id)
        elif kind=='workflow_paused':
            # Reconnected streams replay node events, and may omit filled-form events.
            # A paused state snapshot reconciles the authoritative set of active nodes.
            reasons=data.get('reasons',[])
            paused_nodes=data.get('paused_nodes')
            if isinstance(paused_nodes,list):
                active=set(paused_nodes)
                for node_id in list(self.pending_forms):
                    if node_id not in active:
                        self.pending_forms.pop(node_id,None)
                        self.resolved_nodes.add(node_id)
            for reason in reasons:
                if isinstance(reason,dict) and reason.get('node_id') in FORM_ROLES:self.require_form(reason)
            self.status='waiting_for_human'
        elif kind=='workflow_finished':
            self.status=data.get('status','unknown');self.outputs=data.get('outputs') or {};self.pending_forms={};self.terminal=True
        elif kind=='error':self.status='failed';self.terminal=True

    def submit_payload(self,node_id, *, authenticated_actor_id, owner_id, performer_id, action, inputs, form_definition, role_actor_ids=None):
        form=self.pending_forms.get(node_id)
        if not form:raise EventContractError('该表单不是当前待处理表单')
        role=form['role']
        if role in ('owner','performer'):
            expected=owner_id if role=='owner' else performer_id
            if not owner_id or not performer_id or owner_id==performer_id:raise EventContractError('合作双方角色必须独立明确')
        else:
            expected=(role_actor_ids or {}).get(role)
        if not expected or authenticated_actor_id!=expected:raise EventContractError('当前登录者无权提交这个角色的选择')
        if action not in [a.get('id') for a in form_definition.get('user_actions',[])]:raise EventContractError('操作不在当前表单定义中')
        allowed={x['output_variable_name'] for x in form_definition.get('inputs',[])}
        if not isinstance(inputs,dict) or any(k not in allowed for k in inputs):raise EventContractError('提交了非当前表单字段')
        # Dify transport user stays stable across human roles; actual actor auth is separate.
        return {'user':self.dify_user,'action':action,'inputs':inputs}
