import copy
import json
from pathlib import Path
import unittest
from review_bridge import BridgeError, digest, prepare_review_need, task_proposal, check_current_match
import match_preflight

ROOT = Path(__file__).parent

def fixture():
    x = json.loads((ROOT/'live_fixture.json').read_text())
    return json.loads(x['need_json']), json.loads(x['candidates_json'])

def reseal(e):
    n=e['confirmation']['normalized_need']; h=digest(n)
    e['confirmation']['normalized_sha256']=h; e['current']['normalized_sha256']=h

class Checks(unittest.TestCase):
    def prepare(self,e):
        return prepare_review_need(e['handoff'],e['confirmation'],e['current'])

    def test_valid_need_retains_source_and_learning(self):
        e,p=fixture(); n=self.prepare(e)
        self.assertEqual(len(n['requirements']),3)
        self.assertEqual(n['need_version'],1)
        self.assertEqual(n['skill_requirements'][0]['necessity'],'learnable')
        self.assertTrue(all(not r['independent_required'] for r in n['requirements']))
        self.assertEqual(n['learning_support']['availability'],'available')

    def test_stale_version_blocked_before_ai(self):
        e,p=fixture();e['current']['need_version']=2
        r=match_preflight.main(json.dumps(e),json.dumps(p))
        self.assertEqual(r['route'],'blocked')
        self.assertIn('换版',r['result'])

    def test_revised_demand_blocked(self):
        e,p=fixture();e['handoff']['route']='not_approved'
        with self.assertRaises(BridgeError):self.prepare(e)

    def test_changed_snapshot_blocked(self):
        e,p=fixture();e['handoff']['reviewed_snapshot']['fields']['task']['value']='新增硬件开发'
        with self.assertRaises(BridgeError):self.prepare(e)

    def test_role_mismatch_blocked(self):
        e,p=fixture();e['confirmation']['actor_id']='someone-else'
        with self.assertRaises(BridgeError):self.prepare(e)

    def test_deleted_task_blocked_even_if_normalization_reconfirmed(self):
        e,p=fixture();e['confirmation']['normalized_need']['requirements'].pop();reseal(e)
        with self.assertRaises(BridgeError):self.prepare(e)

    def test_added_task_blocked_even_if_normalization_reconfirmed(self):
        e,p=fixture();r=e['confirmation']['normalized_need']['requirements'][0]
        r['text']=r['source_quote']='开发硬件控制器';reseal(e)
        with self.assertRaises(BridgeError):self.prepare(e)

    def test_duplicate_task_blocked(self):
        e,p=fixture();e['confirmation']['normalized_need']['requirements'][1]=copy.deepcopy(e['confirmation']['normalized_need']['requirements'][0]);reseal(e)
        with self.assertRaises(BridgeError):self.prepare(e)

    def test_guided_not_escalated_to_independent(self):
        e,p=fixture();e['confirmation']['normalized_need']['requirements'][0]['independent_required']=True;reseal(e)
        with self.assertRaises(BridgeError):self.prepare(e)

    def test_expiry_not_invented(self):
        e,p=fixture();e['confirmation']['normalized_need']['expires_date']=None;reseal(e)
        with self.assertRaises(BridgeError):self.prepare(e)

    def test_total_hours_cannot_replace_weekly_hours(self):
        e,p=fixture();e['confirmation']['normalized_need']['hours_per_week']=8;reseal(e)
        with self.assertRaisesRegex(BridgeError,'总计工时'):self.prepare(e)

    def test_expired_recruitment_blocked(self):
        e,p=fixture();e['confirmation']['normalized_need']['expires_date']='2000-01-01';reseal(e)
        with self.assertRaises(BridgeError):self.prepare(e)

    def test_pipeline_keeps_versions(self):
        e,p=fixture();r=match_preflight.main(json.dumps(e),json.dumps(p))
        self.assertEqual(r['route'],'ready')
        packet=json.loads(r['payload'])
        self.assertEqual(packet['need']['owner_id'],e['current']['owner_id'])
        self.assertEqual(packet['need']['provenance']['source_draft_sha256'],e['handoff']['source_draft_sha256'])
        self.assertEqual(check_current_match(packet,e['current'])['need_version'],1)

    def test_old_match_blocked_before_team(self):
        e,p=fixture();r=match_preflight.main(json.dumps(e),json.dumps(p));packet=json.loads(r['payload'])
        e['current']['need_version']=2
        with self.assertRaises(BridgeError):check_current_match(packet,e['current'])

    def test_closed_match_blocked_before_team(self):
        e,p=fixture();packet={'need':self.prepare(e)};e['current']['active']=False
        with self.assertRaises(BridgeError):check_current_match(packet,e['current'])

    def test_modified_match_task_blocked_before_team(self):
        e,p=fixture();packet={'need':self.prepare(e)};packet['need']['requirements'][0]['text']='改成硬件开发'
        with self.assertRaises(BridgeError):check_current_match(packet,e['current'])

    def test_legacy_demo_still_runs_but_cannot_enter_bridge(self):
        e,p=fixture();n=self.prepare(e)
        legacy={k:v for k,v in n.items() if k not in ('provenance','owner_id','need_version')}
        r=match_preflight.main(json.dumps(legacy),json.dumps(p))
        self.assertEqual(r['route'],'ready')
        with self.assertRaises(BridgeError):check_current_match(json.loads(r['payload']),e['current'])

if __name__=='__main__':unittest.main()
