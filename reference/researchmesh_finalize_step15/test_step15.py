import json,unittest
from pathlib import Path
from dify_event_contract import RunEvents,EventContractError
P=Path(__file__).resolve().parent
def read(name):return json.loads((P/name).read_text())
def state(app,case):
 r=RunEvents('researchmesh-finalize15-'+app)
 for e in read(app+'_'+case+'_events.json'):r.apply(e)
 return r
class PublishedApiTests(unittest.TestCase):
 def test_profile_real_pause_requires_profile_owner(self):
  r=state('capability','confirm');node='1792496533023';self.assertEqual(r.pending_forms[node]['role'],'profile_owner')
  form=read('capability_confirm_form.json')
  kw=dict(owner_id='',performer_id='',action='confirm_use',inputs={'profile_correction':''},form_definition=form,role_actor_ids={'profile_owner':'PROFILE-DEMO'})
  self.assertEqual(r.submit_payload(node,authenticated_actor_id='PROFILE-DEMO',**kw)['user'],r.dify_user)
  with self.assertRaises(EventContractError):r.submit_payload(node,authenticated_actor_id='OTHER',**kw)
 def test_profile_without_trusted_actor_map_cannot_submit(self):
  r=state('capability','confirm')
  with self.assertRaises(EventContractError):r.submit_payload('1792496533023',authenticated_actor_id='PROFILE-DEMO',owner_id='',performer_id='',action='confirm_use',inputs={'profile_correction':''},form_definition=read('capability_confirm_form.json'))
 def test_profile_completion_removes_replayed_form(self):
  r=state('capability','confirm')
  for e in read('capability_confirm_use_events.json'):r.apply(e)
  self.assertTrue(r.terminal);self.assertFalse(r.pending_forms);self.assertEqual(r.outputs['profile_route'],'confirmed_matching_clues')
  es=json.loads(r.outputs['matching_evidence'])['evidence'];self.assertTrue(all(x['support_type']=='self_reported' and not x['task_scope_accepted'] for x in es))
 def test_need_review_has_owner_role_and_current_fields(self):
  r=state('demand','complete');node='1792335658268';self.assertEqual(r.pending_forms[node]['role'],'need_owner');f=read('demand_complete_form.json')
  self.assertEqual([x['output_variable_name'] for x in f['inputs']],['review_note'])
  with self.assertRaises(EventContractError):r.submit_payload(node,authenticated_actor_id='OWNER',owner_id='',performer_id='',action='approve',inputs={'injected_actor':'OWNER'},form_definition=f,role_actor_ids={'need_owner':'OWNER'})
 def test_need_approval_remains_backend_handoff(self):
  r=state('demand','complete')
  for e in read('demand_approve_events.json'):r.apply(e)
  h=json.loads(r.outputs['need_matching_handoff']);self.assertEqual(h['route'],'await_backend_confirmation');self.assertFalse(h['runnable_matching_input']);self.assertFalse(h['identity_verified'])
 def test_vague_direction_role_actions_and_draft(self):
  r=state('demand','vague');node='1792384003831';self.assertEqual(r.pending_forms[node]['role'],'need_owner')
  f=read('demand_vague_form.json');self.assertEqual([x['id'] for x in f['user_actions']],['choose_a','choose_b','revise'])
  for e in read('demand_choose_a_events.json'):r.apply(e)
  self.assertTrue(r.terminal);self.assertIn('exploration_card',r.outputs);self.assertNotIn('need_matching_handoff',r.outputs)
 def test_matching_current_profile_gets_exploration_only(self):
  p=json.loads(read('matching_exploration_outputs.json')['decision_packet']);self.assertTrue(p['exploration_candidates'])
  self.assertTrue(all(x['effective']=='unknown' for x in p['matrix']));self.assertFalse(p['auto_contact']);self.assertFalse(p['auto_accept'])
 def test_unknown_human_node_cannot_default_to_a_role(self):
  with self.assertRaises(EventContractError):RunEvents('demo').apply({'event':'human_input_required','data':{'node_id':'UNKNOWN','form_token':'FAKE-TEST-TOKEN'}})
if __name__=='__main__':unittest.main(verbosity=2)
