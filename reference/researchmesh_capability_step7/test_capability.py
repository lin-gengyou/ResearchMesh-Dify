import unittest,json,copy,importlib.util
from pathlib import Path
from draft_validate import main as draft
from review_record import main as review
from timeout_record import main as timeout
from candidate_adapter import candidate_from_confirmed_profile
SOURCE='我独立用Python清洗CSV。我们团队做了机械臂。以后想学ROS2。'
MODEL={'claims':[{'skill_label':'CSV清洗','claim_scope':'用Python清洗CSV','quote':'我独立用Python清洗CSV。','attribution':'personal','independence':'independent','independence_quote':'我独立用Python清洗CSV。','support_type':'self_reported'}, {'skill_label':'机械臂','claim_scope':'团队做机械臂','quote':'我们团队做了机械臂。','attribution':'team','support_type':'self_reported'}],'learning_interests':[{'label':'ROS2','quote':'以后想学ROS2。'}]}
class CapabilityTests(unittest.TestCase):
 def setUp(self):self.d=draft(json.dumps(MODEL,ensure_ascii=False),SOURCE)
 def test_confirm_keeps_only_personal_self_report_without_certification(self):
  r=review(self.d['payload'],'confirm_use','','DEMO');p=json.loads(r['payload']);e=json.loads(r['evidence_json'])['evidence']
  self.assertEqual(r['route'],'confirmed_matching_clues');self.assertEqual(len(e),1)
  self.assertEqual(e[0]['text'],'我独立用Python清洗CSV。');self.assertEqual(e[0]['support_type'],'self_reported')
  self.assertTrue(e[0]['student_confirmed']);self.assertFalse(e[0]['task_scope_accepted']);self.assertFalse(p['identity_verified']);self.assertFalse(p['match_ready'])
 def test_correction_overrides_confirm_and_revokes_matching(self):
  r=review(self.d['payload'],'confirm_use','Python是跟教程做的','DEMO')
  self.assertEqual(r['route'],'revision_requested');self.assertEqual(r['evidence_json'],'');self.assertIn(SOURCE,r['revision_input']);self.assertIn('跟教程',r['revision_input'])
 def test_private_never_emits_matching_evidence(self):
  r=review(self.d['payload'],'save_private','','DEMO');self.assertEqual(r['route'],'private_draft');self.assertFalse(r['evidence_json'])
 def test_tamper_and_empty_revision_fail_closed(self):
  p=json.loads(self.d['payload']);p['claims'][0]['attribution']='team'
  for raw,action in [(json.dumps(p),'confirm_use'),(self.d['payload'],'revise')]:
   r=review(raw,action,'','DEMO');self.assertEqual(r['route'],'blocked');self.assertFalse(r['evidence_json'])
 def test_team_and_interest_only_cannot_be_personal_claim(self):
  m=copy.deepcopy(MODEL);m['claims']=m['claims'][1:];r=draft(json.dumps(m,ensure_ascii=False),SOURCE)
  r=review(r['payload'],'confirm_use','','DEMO');self.assertEqual(r['route'],'no_personal_claims');self.assertFalse(r['evidence_json'])
 def test_bad_model_is_draft_only_and_timeout_grants_nothing(self):
  self.assertEqual(draft('not JSON',SOURCE)['route'],'draft_only')
  p=json.loads(timeout(self.d['payload'],'DEMO')['payload']);self.assertEqual(p['status'],'human_confirmation_timeout');self.assertFalse(p['matching_use_authorized_in_demo'])
 def test_adapter_keeps_self_report_out_of_hard_coverage(self):
  r=review(self.d['payload'],'confirm_use','','DEMO');e=json.loads(r['evidence_json'])['evidence']
  c=candidate_from_confirmed_profile(r,person_id='P-DEMO',name='虚构参与者',selected_evidence_ids=[e[0]['id']],participation={'status':'available','intent':'interested','hours_per_week':4,'available_from':'2026-10-20','location':'线上'})
  spec=importlib.util.spec_from_file_location('match_validate',Path(__file__).with_name('matching_validate_reference.py'));mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  packet={'need':{'requirements':[{'id':'R1','must':True,'allow_adjacent':False,'independent_required':False}]},'candidates':[dict(c,pending=[])],'excluded':[]}
  ai={'assessments':[{'candidate_id':'P-DEMO','requirement_id':'R1','relation':'direct','evidence_id':e[0]['id'],'quote':e[0]['text'],'reason':'经历相关'}]}
  out=json.loads(mod.main(json.dumps(ai),json.dumps(packet))['result']);self.assertEqual(out['matrix'][0]['relation'],'direct');self.assertEqual(out['matrix'][0]['effective'],'unknown')
 def test_selection_must_belong_to_current_snapshot(self):
  r=review(self.d['payload'],'confirm_use','','DEMO')
  for selected in [[],['OLD'],['X']*4]:
   with self.assertRaises(ValueError):candidate_from_confirmed_profile(r,person_id='P',name='P',selected_evidence_ids=selected,participation={})
 def test_real_dify_end_output_enters_adapter(self):
  r=json.loads(Path(__file__).with_name('live_confirm_outputs.json').read_text())
  ids=[e['id'] for e in json.loads(r['matching_evidence'])['evidence']][:2]
  c=candidate_from_confirmed_profile(r,person_id='P-DEMO',name='虚构参与者',selected_evidence_ids=ids,participation={})
  self.assertEqual(len(c['evidence']),2);self.assertTrue(all(e['support_type']=='self_reported' and not e['task_scope_accepted'] for e in c['evidence']))
 def test_real_correction_output_cannot_enter_adapter(self):
  r=json.loads(Path(__file__).with_name('live_correction_outputs.json').read_text())
  with self.assertRaises(ValueError):candidate_from_confirmed_profile(r,person_id='P',name='P',selected_evidence_ids=['OLD'],participation={})
 def test_real_revised_private_output_keeps_guided_experience_and_no_matching(self):
  r=json.loads(Path(__file__).with_name('live_private_outputs.json').read_text());p=json.loads(r['profile_packet'])
  self.assertEqual(r['profile_route'],'private_draft');self.assertFalse(r['matching_evidence']);self.assertFalse(p['matching_use_authorized_in_demo'])
  self.assertEqual([c['independence'] for c in p['claims'][:2]],['guided','guided'])
  self.assertTrue(any(c['attribution']=='personal' and '汇报' in c['claim_scope'] for c in p['claims']))
  self.assertFalse(any('ROS2' in c['skill_label'] for c in p['claims']))
if __name__=='__main__':unittest.main(verbosity=2)
