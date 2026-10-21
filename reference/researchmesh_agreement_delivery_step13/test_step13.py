import copy,json,unittest
from pathlib import Path
from chain_delivery_bridge import delivery_with_provenance
from cross_app_bridge import BridgeError
import delivery_prepare
P=Path(__file__).parent
def fixture():
    return json.loads((P/'delivery_fixture.json').read_text())
class Checks(unittest.TestCase):
    def test_actual_end_to_end_versions_budget_and_privacy(self):
        out=json.loads((P/'live_agreement_outputs.json').read_text());a=json.loads(out['agreement_v2_packet'])
        result=json.loads((P/'live_delivery_outputs.json').read_text());d=json.loads(result['contribution_packet'])
        self.assertEqual(out['agreement_v2_route'],'ready');self.assertEqual(a['version'],2)
        self.assertEqual(a['need_version'],1);self.assertEqual(a['terms']['total_hours'],4)
        self.assertEqual(a['confirmations']['owner']['terms_hash'],a['confirmations']['performer']['terms_hash'])
        self.assertTrue(a['terms']['support']['value'])
        self.assertEqual(d['agreement']['source_context']['allocated_hours'],4)
        self.assertEqual(d['agreement']['source_context']['need_version'],1)
        self.assertEqual(d['agreement']['agreement_hash'],a['terms_hash'])
        self.assertEqual(d['agreement']['version'],2)
        self.assertFalse(d['public_authorized']);self.assertFalse(d['auto_publish'])
        self.assertFalse(d['skill_certified']);self.assertEqual(d['skills_added'],[])
        self.assertFalse(d['formal_state_update']);self.assertEqual(len(d['contribution_claims']),4)
    def test_lineage_survives_delivery_prepare(self):
        f=fixture();r=delivery_prepare.main(f['agreement_json'],f['submission_text']);self.assertEqual(r['route'],'ready')
        a=json.loads(f['agreement_json']);p=json.loads(r['payload'])
        self.assertEqual(p['agreement']['source_context'],a['source_context'])
        self.assertEqual(p['agreement']['source_context']['allocated_hours'],4)
    def test_stale_agreement_blocks(self):
        f=fixture();a=json.loads(f['agreement_json']);a['current_version']+=1
        self.assertEqual(delivery_prepare.main(json.dumps(a),f['submission_text'])['route'],'blocked')
    def test_bad_source_hash_blocks(self):
        f=fixture();a=json.loads(f['agreement_json']);a['source_context']['planning_sha256']='bad'
        self.assertEqual(delivery_prepare.main(json.dumps(a),f['submission_text'])['route'],'blocked')
    def test_old_need_blocks_bridge(self):
        o=json.loads((P/'live_agreement_outputs.json').read_text());c=json.loads((P/'current_agreement_demo.json').read_text());c['need_version']+=1
        with self.assertRaises(BridgeError):delivery_with_provenance(o,current=c,source_run_id='fictional')
    def test_changed_team_blocks_bridge(self):
        o=json.loads((P/'live_agreement_outputs.json').read_text());c=json.loads((P/'current_agreement_demo.json').read_text());c['source_team_sha256']='0'*64
        with self.assertRaises(BridgeError):delivery_with_provenance(o,current=c,source_run_id='fictional')
    def test_old_format_legacy_unchanged(self):
        f=fixture();a=json.loads(f['agreement_json']);a.pop('source_context')
        self.assertEqual(delivery_prepare.main(json.dumps(a),f['submission_text'])['route'],'ready')
    def test_source_changes_snapshot_hash(self):
        f=fixture();a=json.loads(f['agreement_json']);r=delivery_prepare.main(f['agreement_json'],f['submission_text']);a['source_context']['allocated_hours']=3
        changed=delivery_prepare.main(json.dumps(a),f['submission_text'])
        self.assertNotEqual(json.loads(r['payload'])['snapshot_hash'],json.loads(changed['payload'])['snapshot_hash'])
if __name__=='__main__':unittest.main()
