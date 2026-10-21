import json,hashlib,datetime
def main(arg1:str,arg2:str,arg3:str,arg4:str):
    def dump(x):return json.dumps(x,ensure_ascii=False)
    def finish(p,card,route,evidence=None,revision=''):
        return {'result':card,'payload':dump(p),'route':route,'evidence_json':dump(evidence) if evidence else '', 'revision_input':revision}
    try:
        p=json.loads(arg1);stored=p.pop('draft_hash')
        actual=hashlib.sha256(json.dumps(p,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if stored!=actual:raise ValueError('能力草稿与原快照不一致，请重新读取')
        p['draft_hash']=stored
        if arg2 not in ['confirm_use','revise','save_private']:raise ValueError('无效的本人选择')
        if not isinstance(arg3,str) or len(arg3)>3000:raise ValueError('更正意见应为3000字以内文本')
        correction=arg3.strip()
        if arg2=='revise' and not correction:raise ValueError('请说明要更正的内容；当前未确认或授权匹配')
        state='revision_requested' if correction and arg2!='save_private' else 'private_draft' if arg2=='save_private' else 'confirmed_matching_clues'
        personal=[dict(c) for c in p.get('claims',[]) if c.get('attribution')=='personal']
        if state=='confirmed_matching_clues' and not personal:state='no_personal_claims'
        allowed=state=='confirmed_matching_clues'
        p.update({'schema_version':'capability_profile_0.2','status':state,
          'profile_confirmed_in_demo':allowed,'matching_use_authorized_in_demo':allowed,
          'identity_verified':False,'user_confirmed':False,'skill_certified':False,
          'match_ready':False,'auto_publish':False,'skills_added':[],
          'review_event':{'event':'profile_review_choice','action':arg2,'effective_state':state,
            'correction':correction,'run_id':arg4,'draft_hash':stored,
            'identity_verified':False,'at':datetime.datetime.now(datetime.timezone.utc).isoformat()}})
        evidence=None;revision=''
        if allowed:
            records=[]
            for c in personal:
                records.append({'id':'cap_'+stored[:12]+'_'+c['id'],'text':c['quote'],
                  'personal_contribution':True,'student_confirmed':True,
                  'confirmation_mode':'demo_human_input','identity_verified':False,
                  'task_scope_accepted':False,'support_type':c['support_type'],
                  'independence':c['independence'],'source_claim_id':c['id'],
                  'source_draft_hash':stored,'externally_verified':False})
            evidence={'schema_version':'capability_evidence_0.2','status':'confirmed_clues_in_demo',
              'evidence':records,'matching_use_authorized_in_demo':True,
              'source_draft_hash':stored,'source_workflow_run_id':arg4,
              'identity_verified':False,'skill_certified':False,'match_ready':False}
        elif state=='revision_requested':
            revision=p['source_text']+'\n\n更正（以本段更正为准，未更正内容保留）：'+correction
        labels={'confirmed_matching_clues':'本人确认候选经历，可作为匹配线索（演示）',
          'revision_requested':'已记录更正，等待AI重新整理；本版没有确认或授权匹配',
          'private_draft':'仅保留私有草稿，不授权进入匹配',
          'no_personal_claims':'尚无可确认的本人工作；团队成果和学习兴趣没有转为个人能力'}
        lines=['# 研织｜个人经历核对结果',labels[state],
          '能力草稿快照：'+stored[:12],
          '确认经历自述不等于外部核验、能力认证或承诺能独立承担新任务。']
        if allowed:
            lines+=['','## 本次可用于讨论的本人经历']
            for c in personal:lines += ['- '+c['skill_label']+'：'+c['claim_scope'],'  原文：“'+c['quote']+'”']
            lines+=['','团队成果、归属不明的候选和学习兴趣均未进入这份个人证据包。',
              '进入具体需求后仍需核对任务范围、时间和意愿；系统不会自动公开或联系他人。']
        if correction:lines+=['','更正原文：'+correction]
        if revision:lines+=['下一步：将原描述与这段更正一同交回AI整理，再核对新草稿。']
        return finish(p,'\n'.join(lines),state,evidence,revision)
    except (ValueError,TypeError,KeyError) as e:
        return finish({'schema_version':'capability_profile_0.2','status':'blocked','reason':str(e),
          'matching_use_authorized_in_demo':False,'identity_verified':False,'auto_publish':False},
          '# 研织｜个人经历暂未确认\n'+str(e)+'\n没有生成可用于匹配的证据包。','blocked')
