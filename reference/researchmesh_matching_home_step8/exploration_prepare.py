import json
def main(arg1:str):
    d=json.loads(arg1);requirements={r['id']:r for r in d['need']['requirements']}
    warnings=list(d.get('warnings',[]));groups={}
    for cell in d['matrix']:
        if (cell.get('effective')=='unknown' and cell.get('relation') in ('direct','adjacent')
          and cell.get('personal_contribution') is True and cell.get('student_confirmed') is True
          and cell.get('evidence_support_type') in ('self_reported','provided_excerpt') and cell.get('quote')):
            req=requirements[cell['requirement_id']]
            clue={'requirement_id':req['id'],'task':req['text'],'relation':cell['relation'],
              'evidence_id':cell['evidence_id'],'quote':cell['quote'],
              'why_relevant':cell.get('ai_reason',''),'unresolved':cell['reason'],
              'evidence_tier':cell['evidence_support_type'],'probe':None}
            if req.get('independent_required') and cell.get('independence')!='independent':
                clue['independence_gap']='任务要求独立完成，现有经历尚不能支持；只可讨论既有做法，不承诺独立交付。'
            groups.setdefault(cell['candidate_id'],[]).append(clue)
        cell.pop('ai_discussion_probe',None)
    exploration=[]
    for candidate in d['candidates']:
        clues=groups.get(candidate['id'])
        if clues:
            exploration.append({'candidate_id':candidate['id'],'name':candidate['name'],
              'status':'exploration_only','clues':clues,'pending_conditions':candidate['pending'],
              'can_start_discussion':not bool(candidate['pending']),
              'counts_as_required_coverage':False,'auto_invite':False})
    d.update({'schema_version':'match_exploration_matrix_0.2','exploration_candidates':exploration,
      'warnings':list(dict.fromkeys(warnings)),'auto_contact':False,'auto_accept':False})
    compact=[{'candidate_id':x['candidate_id'],'pending_conditions':x['pending_conditions'],
      'clues':[{k:v for k,v in c.items() if k in ('requirement_id','task','quote','why_relevant','unresolved','independence_gap')} for c in x['clues']]} for x in exploration]
    return {'result':json.dumps(d,ensure_ascii=False),
      'route':'needs_probe' if exploration else 'skip',
      'probe_input':json.dumps({'exploration_candidates':compact},ensure_ascii=False)}
