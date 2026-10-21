import unittest,json,copy,hashlib
from pathlib import Path
from match_validate import main as validate
from match_preflight import main as preflight
from exploration_prepare import main as prepare
from probe_validate import main as add_probe
from match_render import main as render
from home_profile import preview_home,public_projection,canonical
ROOT=Path(__file__).parent
PROBE={'mode':'synthetic_discussion','minutes':15,'goal':'用模拟CSV讨论空值处理思路','steps':['用三行虚构数据说明缺失值位置','口头解释一种处理办法'],'success_check':'能说明处理选择与局限，而非提交真实项目代码'}
class MatchTests(unittest.TestCase):
 def test_preflight_enumerates_exact_matrix_slots(self):
  f=json.loads((ROOT/'live_test_fixture.json').read_text());out=preflight(json.dumps(f['need']),json.dumps(f['people']))
  p=json.loads(out['payload']);self.assertEqual(p['expected_assessment_count'],6)
  self.assertEqual([(x['candidate_id'],x['requirement_id']) for x in p['assessment_slots']],[('A','R1'),('A','R2'),('B','R1'),('B','R2'),('D','R1'),('D','R2')])
 def test_omitted_cells_are_explicitly_reported(self):
  d=json.loads(validate({'assessments':[]},json.dumps(self.packet()))['result']);self.assertTrue(d['warnings']);self.assertEqual(d['matrix'][0]['effective'],'unknown')
 def packet(self,support='self_reported',personal=True,confirmed=True,independence='guided'):
  e={'id':'E1','text':'我跟教程使用Python处理CSV空值。','personal_contribution':personal,'student_confirmed':confirmed,'task_scope_accepted':support=='provided_excerpt','support_type':support,'independence':independence}
  return {'need':{'id':'N','title':'模拟需求','requirements':[{'id':'R1','text':'独立处理CSV空值','must':True,'allow_adjacent':False,'independent_required':True}]},'candidates':[{'id':'P','name':'虚构参与者','pending':[],'evidence':[e]}],'excluded':[]}
 def run_case(self,p=None,probe=PROBE,relation='direct'):
  p=p or self.packet();m={'assessments':[{'candidate_id':'P','requirement_id':'R1','relation':relation,'evidence_id':'E1','quote':p['candidates'][0]['evidence'][0]['text'],'reason':'原文有处理CSV空值的本人经历','action_checks':[{'action':'处理CSV空值','status':'supported','quote':'处理CSV空值'}],'discussion_probe':probe}]}
  base=prepare(validate(json.dumps(m),json.dumps(p))['result'])['result']
  rows=[dict(probe,candidate_id='P',requirement_id='R1')] if isinstance(probe,dict) else []
  return json.loads(add_probe(json.dumps({'probes':rows}),base)['result'])
 def test_self_report_gets_optional_probe_without_required_coverage(self):
  d=self.run_case();self.assertEqual(d['matrix'][0]['effective'],'unknown');x=d['exploration_candidates'][0]
  self.assertFalse(x['counts_as_required_coverage']);self.assertEqual(x['clues'][0]['probe']['minutes'],15);self.assertIn('independence_gap',x['clues'][0])
  text=render(json.dumps(d))['result'];self.assertIn('可探索的经历线索',text);self.assertIn('未覆盖的必需项',text)
 def test_team_interest_link_or_unconfirmed_never_get_probe(self):
  for p,relation in [(self.packet(personal=False),'direct'),(self.packet(confirmed=False),'direct'),(self.packet(support='link_only'),'direct'),(self.packet(),'unknown')]:
   self.assertFalse(self.run_case(p=p,relation=relation)['exploration_candidates'])
 def test_supported_material_keeps_original_hard_coverage(self):
  d=self.run_case(p=self.packet(support='provided_excerpt',independence='independent'))
  self.assertEqual(d['matrix'][0]['effective'],'direct');self.assertFalse(d['exploration_candidates'])
 def prepared(self,p=None):
  p=p or self.packet();m={'assessments':[{'candidate_id':'P','requirement_id':'R1','relation':'direct','evidence_id':'E1','quote':p['candidates'][0]['evidence'][0]['text'],'reason':'本人处理经历','action_checks':[{'action':'处理CSV空值','status':'supported','quote':'处理CSV空值'}]}]}
  return prepare(validate(json.dumps(m),json.dumps(p))['result'])
 def test_second_ai_only_sees_exploration_candidates(self):
  p=self.packet();a=copy.deepcopy(p['candidates'][0]);a['id']='A';a['evidence'][0].update(support_type='provided_excerpt',independence='independent',task_scope_accepted=True);p['candidates'].append(a)
  rows=[{'candidate_id':c['id'],'requirement_id':'R1','relation':'direct','evidence_id':'E1','quote':c['evidence'][0]['text'],'action_checks':[{'action':'处理CSV空值','status':'supported','quote':'处理CSV空值'}]} for c in p['candidates']]
  q=prepare(validate(json.dumps({'assessments':rows}),json.dumps(p))['result']);inp=json.loads(q['probe_input'])
  self.assertEqual(q['route'],'needs_probe');self.assertEqual([x['candidate_id'] for x in inp['exploration_candidates']],['P'])
 def test_no_exploration_routes_around_second_ai(self):
  q=self.prepared(self.packet(support='provided_excerpt',independence='independent'));self.assertEqual(q['route'],'skip');self.assertEqual(json.loads(q['probe_input'])['exploration_candidates'],[])
 def test_non_exploration_candidate_or_task_is_rejected(self):
  for cid,rid in [('A','R1'),('P','FAKE')]:
   out=json.loads(add_probe(json.dumps({'probes':[dict(PROBE,candidate_id=cid,requirement_id=rid)]}),self.prepared()['result'])['result'])
   self.assertIsNone(out['exploration_candidates'][0]['clues'][0]['probe']);self.assertTrue(out['warnings'])
 def test_duplicate_probe_is_rejected_without_changing_coverage(self):
  r=dict(PROBE,candidate_id='P',requirement_id='R1');out=json.loads(add_probe(json.dumps({'probes':[r,r]}),self.prepared()['result'])['result'])
  self.assertIsNone(out['exploration_candidates'][0]['clues'][0]['probe']);self.assertEqual(out['matrix'][0]['effective'],'unknown')
 def test_bad_probe_keeps_clue_but_no_actionable_draft(self):
  for probe in [dict(PROBE,minutes=90),dict(PROBE,minutes=True),dict(PROBE,steps=[]),dict(PROBE,mode='real_delivery')]:
   d=self.run_case(probe=probe);self.assertIsNone(d['exploration_candidates'][0]['clues'][0]['probe']);self.assertTrue(d['warnings'])
 def test_missing_action_blocks_even_confirmed_material_and_adjacent_allowed(self):
  p=self.packet(support='provided_excerpt',independence='independent');p['need']['requirements'][0]['allow_adjacent']=True
  m={'assessments':[{'candidate_id':'P','requirement_id':'R1','relation':'direct','evidence_id':'E1','quote':p['candidates'][0]['evidence'][0]['text'],'action_checks':[{'action':'解释数据趋势','status':'missing','quote':''}]}]}
  c=json.loads(validate(json.dumps(m),json.dumps(p))['result'])['matrix'][0]
  self.assertEqual(c['effective'],'unknown');self.assertEqual(c['relation'],'adjacent');self.assertIn('解释数据趋势',c['reason'])
 def test_fabricated_or_missing_action_quotes_cannot_support_coverage(self):
  p=self.packet(support='provided_excerpt',independence='independent')
  for checks in [None,[],[{'action':'解释数据趋势','status':'supported','quote':'这里没有这段原文'}]]:
   m={'assessments':[{'candidate_id':'P','requirement_id':'R1','relation':'direct','evidence_id':'E1','quote':p['candidates'][0]['evidence'][0]['text'],'action_checks':checks}]}
   c=json.loads(validate(json.dumps(m),json.dumps(p))['result'])['matrix'][0];self.assertEqual(c['effective'],'unknown')
 def test_same_quote_cannot_multiply_into_two_different_core_actions(self):
  p=self.packet(support='provided_excerpt',independence='independent');p['need']['requirements'][0]['allow_adjacent']=True
  row={'candidate_id':'P','requirement_id':'R1','relation':'direct','evidence_id':'E1','quote':p['candidates'][0]['evidence'][0]['text'],'reason':'AI错误声称两项都有支持','action_checks':[{'action':a,'status':'supported','quote':'处理CSV空值'} for a in ['处理空值','解释趋势']]}
  c=json.loads(validate({'assessments':[row]},json.dumps(p))['result'])['matrix'][0]
  self.assertEqual(c['effective'],'unknown');self.assertIn('重复引用',c['reason']);self.assertNotIn('两项都有支持',c['ai_reason'])
 def test_bad_ai_ids_fail_to_unknown_instead_of_crashing(self):
  m={'assessments':[{'candidate_id':{},'requirement_id':'R1'}]}
  out=json.loads(validate(json.dumps(m),json.dumps(self.packet()))['result']);self.assertEqual(out['matrix'][0]['effective'],'unknown')
 def test_pending_conditions_prevent_immediate_discussion(self):
  p=self.packet();p['candidates'][0]['pending']=['本人意愿待确认']
  self.assertFalse(self.run_case(p=p)['exploration_candidates'][0]['can_start_discussion'])
 def test_excess_probes_are_not_silently_selected(self):
  p=self.packet();r=p['need']['requirements'][0];p['need']['requirements']=[dict(r,id='R'+str(i)) for i in range(1,5)]
  rows=[{'candidate_id':'P','requirement_id':req['id'],'relation':'direct','evidence_id':'E1','quote':p['candidates'][0]['evidence'][0]['text'],'discussion_probe':PROBE} for req in p['need']['requirements']]
  base=prepare(validate(json.dumps({'assessments':rows}),json.dumps(p))['result'])['result']
  probes=[dict(PROBE,candidate_id='P',requirement_id=r['requirement_id']) for r in rows]
  d=json.loads(add_probe(json.dumps({'probes':probes}),base)['result'])
  self.assertEqual(len(d['exploration_candidates'][0]['clues']),4);self.assertTrue(all(c['probe'] is None for c in d['exploration_candidates'][0]['clues']));self.assertTrue(d['warnings'])

class HomeTests(unittest.TestCase):
 def setUp(self):
  self.profile=json.loads((ROOT/'home_profile_fixture.json').read_text())
  self.delivery=json.loads((ROOT/'home_contribution_fixture.json').read_text())
  self.preview=preview_home(self.profile,owner_id='P-DEMO',settings={'display_name':'虚构学生甲','bio':'希望从数据整理开始参与协作','contact':'PRIVATE-CONTACT'},contribution_outputs=[self.delivery])
 def publication(self,**fields):return dict(status='published',owner_id='P-DEMO',preview_hash=self.preview['preview_hash'],header_fields=['display_name'],experience_ids=['claim_1'],interest_ids=[],**fields)
 def test_matching_consent_does_not_publish_home(self):
  self.assertEqual(public_projection(self.preview,publication={})['status'],'not_published');self.assertFalse(self.preview['public_authorized'])
 def test_public_projection_has_only_selected_sanitized_content(self):
  p=public_projection(self.preview,publication=self.publication());self.assertEqual(len(p['experiences']),1);s=canonical(p)
  for forbidden in ['PRIVATE-CONTACT','source_text','requested_changes','workflow_run_id','questions','原文：']:self.assertNotIn(forbidden,s)
  self.assertFalse(p['contributions']);self.assertNotIn('bio',p['header']);self.assertFalse(p['skill_certified'])
 def test_changed_preview_or_wrong_owner_cannot_reuse_consent(self):
  q=copy.deepcopy(self.preview);q['header']['display_name']='CHANGED'
  self.assertEqual(public_projection(q,publication=self.publication())['status'],'not_published')
  grant=self.publication();grant['owner_id']='OTHER';self.assertEqual(public_projection(self.preview,publication=grant)['status'],'not_published')
 def test_contribution_requires_separate_content_bound_publication(self):
  c=self.preview['contributions'][0]
  grant=self.publication(separately_published_contributions={c['id']:hashlib.sha256(canonical(c).encode()).hexdigest()})
  projected=public_projection(self.preview,publication=grant)
  self.assertEqual(len(projected['contributions']),1)
  self.assertNotIn(c['id'],canonical(projected));self.assertNotIn('agreement_id',canonical(projected))
  grant['separately_published_contributions'][c['id']]='stale';self.assertFalse(public_projection(self.preview,publication=grant)['contributions'])
 def test_other_person_contribution_is_not_on_owners_home(self):
  p=preview_home(self.profile,owner_id='OTHER',settings={},contribution_outputs=[self.delivery]);self.assertFalse(p['contributions'])
 def test_revoked_home_has_no_public_content(self):
  grant=self.publication();grant['status']='revoked';out=public_projection(self.preview,publication=grant)
  self.assertEqual(out['status'],'not_published');self.assertNotIn('experiences',out)
if __name__=='__main__':unittest.main(verbosity=2)
