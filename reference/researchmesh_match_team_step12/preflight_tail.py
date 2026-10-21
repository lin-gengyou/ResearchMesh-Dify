def main(arg1: str,arg2: str):
    def blocked(message):
        packet={'schema_version':'team_demo_0.1','route':'blocked','reason':str(message),'excluded':[]}
        return {'route':'blocked','result':'# 研织｜组队前暂需核对\n'+str(message)+'\n没有创建团队、联系人员或接受约定。','payload':json.dumps(packet,ensure_ascii=False),'excluded':'[]'}
    try:
        envelope=json.loads(arg1)
        if not isinstance(envelope,dict) or envelope.get('module')!='team_from_match':
            return _filter(arg1,arg2)
        people=json.loads(arg2)
        if envelope['current'].get('matching_candidates_sha256')!=digest(people):
            raise BridgeError('候选资料与本次匹配时保存的快照不同，应重新匹配')
        source=envelope['decision_packet']
        if source.get('recommendation_status')!='discussion_draft':raise BridgeError('不是完整匹配结果')
        need=team_from_match(envelope,people)
        checked=_filter(json.dumps(need,ensure_ascii=False),arg2)
        if checked['route']!='ready':return checked
        packet=json.loads(checked['payload'])
        keys={(p['id'],r['id']) for p in packet['candidates'] for r in need['requirements']}
        source_cells=source.get('matrix',[])
        matrix=[]
        for key in sorted(keys):
            found=[c for c in source_cells if (c.get('candidate_id'),c.get('requirement_id'))==key]
            if len(found)!=1:raise BridgeError('上游匹配矩阵有缺项或重复，不能拼出可行分工')
            cell=copy.deepcopy(found[0])
            if cell.get('effective') in ('direct','adjacent'):
                person=next(p for p in packet['candidates'] if p['id']==key[0])
                evidence=[e for e in person['evidence'] if e['id']==cell.get('evidence_id')]
                if len(evidence)!=1:raise BridgeError('匹配引用的证据已缺失')
                e=evidence[0]; checks=cell.get('task_action_checks',[])
                if (not cell.get('quote') or cell['quote'] not in e['text'] or e['support_type']!='provided_excerpt'
                    or not e['personal_contribution'] or not e['student_confirmed'] or not e['task_scope_accepted']
                    or cell.get('task_actions_complete') is not True or not checks
                    or any(c.get('status')!='supported' or not c.get('quote') or c['quote'] not in e['text'] for c in checks)):
                    raise BridgeError('逐动作证据未通过复核，不能升为任务覆盖')
            matrix.append(cell)
        packet.update({'schema_version':'team_matrix_0.2','matrix':matrix,'warnings':source.get('warnings',[]),
            'source_mode':'reused_matching_matrix','identity_verified':False})
        solved=_solve(json.dumps(packet,ensure_ascii=False))
        return {'route':'matched_plan','payload':solved['payload'],'result':solved['result'],'excluded':checked['excluded']}
    except Exception as e:
        return blocked(e)
