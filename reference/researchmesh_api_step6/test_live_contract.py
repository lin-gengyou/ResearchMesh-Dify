"""Contract regressions from actual Service API events (tokens redacted)."""
import json,unittest
from pathlib import Path
from dify_event_contract import RunEvents
ROOT=Path(__file__).parent
class LiveContractTests(unittest.TestCase):
 def test_reconnect_replay_replaces_completed_owner_form(self):
  r=RunEvents('researchmesh-api-team-v1')
  for e in json.loads((ROOT/'team_start_events.json').read_text()):r.apply(e)
  self.assertEqual(set(r.pending_forms),{'1792463257417'})
  replay=json.loads((ROOT/'team_owner_accept_events.json').read_text())
  self.assertFalse(any(e['event']=='human_input_form_filled' for e in replay))
  for e in replay:r.apply(e)
  self.assertEqual(set(r.pending_forms),{'1792463915587'})
  self.assertIn('1792463257417',r.resolved_nodes)
 def test_pause_snapshot_alone_reconciles_pending_forms(self):
  r=RunEvents('stable')
  e=json.loads((ROOT/'team_start_events.json').read_text())
  first=next(x for x in e if x['event']=='human_input_required');r.apply(first)
  replay=json.loads((ROOT/'team_owner_accept_events.json').read_text())
  pause=next(x for x in replay if x['event']=='workflow_paused');r.apply(pause)
  self.assertEqual(set(r.pending_forms),{'1792463915587'})
 def test_four_agreement_pauses_and_terminal_outputs(self):
  r=RunEvents('researchmesh-api-team-v1')
  sequence=[('start','1792463257417'),('owner_accept','1792463915587'),('performer_revise','1792478884718'),('owner_v2_accept','1792479365090')]
  for tag,node in sequence:
   for e in json.loads((ROOT/f'team_{tag}_events.json').read_text()):r.apply(e)
   self.assertEqual(set(r.pending_forms),{node})
  for e in json.loads((ROOT/'team_performer_v2_accept_events.json').read_text()):r.apply(e)
  self.assertTrue(r.terminal);self.assertFalse(r.pending_forms)
  self.assertEqual(r.outputs['agreement_v2_route'],'ready')
 def test_delivery_two_roles_remain_separate_during_reconnect(self):
  r=RunEvents('researchmesh-api-delivery-v1')
  for e in json.loads((ROOT/'delivery_start_events.json').read_text()):r.apply(e)
  self.assertEqual(set(r.pending_forms),{'1792415339919'})
  for e in json.loads((ROOT/'delivery_reviewer_approve_events.json').read_text()):r.apply(e)
  self.assertEqual(set(r.pending_forms),{'1792416719562'})
  self.assertEqual(r.pending_forms['1792416719562']['role'],'performer')
 def test_api_agreement_to_delivery_keeps_version_and_consent_boundary(self):
  team=json.loads((ROOT/'team_performer_v2_accept_detail.json').read_text())
  agreement=json.loads(team['outputs']['agreement_v2_packet'])
  delivery=json.loads((ROOT/'delivery_contributor_public_draft_detail.json').read_text())
  p=json.loads(delivery['outputs']['contribution_packet'])
  self.assertEqual(team['outputs']['agreement_v2_route'],'ready')
  self.assertEqual(agreement['confirmations']['owner']['terms_hash'],agreement['confirmations']['performer']['terms_hash'])
  self.assertEqual(p['agreement']['source_workflow_run_id'],team['id'])
  self.assertEqual(p['agreement']['agreement_hash'],agreement['terms_hash'])
  self.assertEqual(p['agreement']['version'],2)
  self.assertEqual(p['review_decision'],'accepted')
  self.assertTrue(p['public_draft_authorized_in_demo'])
  self.assertFalse(p['public_authorized']);self.assertFalse(p['auto_publish'])
  self.assertFalse(p['formal_state_update']);self.assertEqual(p['skills_added'],[])
if __name__=='__main__':unittest.main(verbosity=2)
