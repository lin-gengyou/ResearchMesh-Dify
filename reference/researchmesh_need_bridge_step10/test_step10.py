import copy
import hashlib
import json
import unittest
from pathlib import Path
import normalize, execution, review_record

ROOT = Path(__file__).parent

def fixture():
    p = json.loads(json.loads((ROOT/'trial1_boundary_output.json').read_text())['payload'])
    p['fields']['task'] = dict(value='读取CSV并检查缺失值，按日期汇总温度，绘制温度趋势图', status='explicit', quote='读取CSV并检查缺失值，按日期汇总温度，绘制温度趋势图', verification='user_statement_only')
    p['fields']['execution_readiness'] = dict(value='已就绪', status='explicit', quote='目前可以开始，不依赖采购、真实个人数据或其他未完成任务', verification='user_statement_only')
    p['unresolved_conflicts'] = []
    p['execution_checks'] = dict(ready_for_owner_review=True, readiness='ready')
    return p

class Checks(unittest.TestCase):
    def test_task_actions_retained(self):
        p = fixture()
        brief = (ROOT/'live_input.txt').read_text()
        result = json.loads(normalize.main(json.dumps(p), brief)['payload'])
        self.assertEqual(result['fields']['task']['status'], 'explicit')

    def test_bare_direction_not_task(self):
        p = fixture()
        p['fields']['task'].update(value='数据科学方向', quote='数据科学方向')
        result = json.loads(normalize.main(json.dumps(p), '数据科学方向')['payload'])
        self.assertEqual(result['fields']['task']['status'], 'unknown')

    def test_absent_quote_not_task(self):
        result = json.loads(normalize.main(json.dumps(fixture()), '想做个项目')['payload'])
        self.assertEqual(result['fields']['task']['status'], 'unknown')

    def readiness(self, quote):
        p = fixture()
        p['fields']['execution_readiness']['quote'] = quote
        return json.loads(execution.main(json.dumps(p))['payload'])['execution_checks']

    def test_natural_ready(self):
        self.assertTrue(self.readiness('目前可以开始')['ready_for_owner_review'])

    def test_ready_without_resources_not_enough(self):
        p = fixture()
        p['fields']['dependencies']['quote'] = '依赖CSV文件'
        p['fields']['input_materials']['quote'] = '需要样例CSV'
        self.assertFalse(json.loads(execution.main(json.dumps(p))['payload'])['execution_checks']['ready_for_owner_review'])

    def test_pending_beats_ready(self):
        self.assertEqual(self.readiness('目前可以开始，但文件权限尚未获批')['readiness'], 'pending')

    def test_blocked_beats_ready(self):
        self.assertEqual(self.readiness('目前可以开始，但数据无法提供')['readiness'], 'blocked')

    def test_future_not_ready(self):
        self.assertFalse(self.readiness('预计下周可以开始')['ready_for_owner_review'])

    def review(self, action='approve', note='', packet=None):
        return review_record.main(action, note, json.dumps(packet or fixture(), ensure_ascii=False), 'fictional-run')

    def test_approved_snapshot_hash_and_learning_boundary(self):
        out = self.review()
        r = json.loads(out['review_record']); h = json.loads(out['matching_handoff'])
        expected = hashlib.sha256(json.dumps(r['reviewed_snapshot'], ensure_ascii=False, sort_keys=True, separators=(',',':')).encode()).hexdigest()
        self.assertEqual(r['draft_sha256'], expected)
        self.assertEqual(h['source_draft_sha256'], expected)
        self.assertEqual(h['route'], 'await_backend_confirmation')
        self.assertFalse(h['runnable_matching_input'])
        self.assertFalse(r['owner_confirmed'])
        self.assertEqual(h['reviewed_snapshot']['requirements'][0]['necessity'], 'learnable')
        self.assertEqual(h['reviewed_snapshot']['requirements'][0]['independence'], 'guided')

    def test_revise_never_matching(self):
        h = json.loads(self.review('revise', '任务范围需要缩小')['matching_handoff'])
        self.assertEqual(h['route'], 'not_approved')
        self.assertNotIn('reviewed_snapshot', h)

    def test_missing_required_field_never_approved(self):
        p = fixture(); p['fields']['task']['status'] = 'unknown'
        self.assertEqual(json.loads(self.review(packet=p)['review_record'])['status'], 'review_invalid')

    def test_invalid_action_never_approved(self):
        self.assertEqual(json.loads(self.review('timeout')['matching_handoff'])['route'], 'not_approved')

if __name__ == '__main__':
    unittest.main()
