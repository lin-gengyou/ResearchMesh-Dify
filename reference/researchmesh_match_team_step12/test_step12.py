import copy,json,unittest
from pathlib import Path
from review_bridge import digest,BridgeError
from team_bridge import agreement_from_team
import team_preflight
import team_preflight_original
from team_bridge import team_from_match
P=Path(__file__).parent

def fixture():
    f=json.loads((P/'live_fixture.json').read_text())
    return json.loads(f['need_json']),json.loads(f['candidates_json'])

def execute(e,p):return team_preflight.main(json.dumps(e,ensure_ascii=False),json.dumps(p,ensure_ascii=False))

def reseal_planning(e):
    h=digest(e['planning_confirmation']['planning'])
    e['planning_confirmation']['planning_sha256']=h;e['current']['planning_sha256']=h

class Tests(unittest.TestCase):
    def test_legacy_exclusion_details_preserved(self):
        e,p=fixture();n=team_from_match(e,p);p[0]['hours_per_week']=0
        old=team_preflight_original.main(json.dumps(n),json.dumps(p))
        new=team_preflight.main(json.dumps(n),json.dumps(p))
        self.assertEqual(new,old)

    def test_three_tasks_one_person_four_hours(self):
        e,p=fixture();r=execute(e,p);self.assertEqual(r['route'],'matched_plan')
        d=json.loads(r['payload']);self.assertEqual(d['status'],'proposed')
        self.assertEqual(len(d['plans']),1);self.assertEqual(sum(a['hours'] for a in d['plans'][0]['assignments']),4)
        self.assertEqual(d['need']['need_version'],1)

    def test_changed_need_blocks(self):
        e,p=fixture();e['current']['need_version']=2;self.assertEqual(execute(e,p)['route'],'blocked')

    def test_changed_candidate_packet_requires_new_match(self):
        e,p=fixture();p[0]['evidence'][0]['text']+='新增自述'
        self.assertEqual(execute(e,p)['route'],'blocked')

    def test_changed_planning_blocks(self):
        e,p=fixture();e['planning_confirmation']['planning']['task_hours'][0]['hours']=2
        self.assertEqual(execute(e,p)['route'],'blocked')

    def test_over_week_budget_blocks(self):
        e,p=fixture();e['planning_confirmation']['planning']['task_hours'][0]['hours']=2;reseal_planning(e)
        self.assertEqual(execute(e,p)['route'],'blocked')

    def test_old_match_hash_blocks(self):
        e,p=fixture();e['current']['latest_matching_sha256']='old'
        self.assertEqual(execute(e,p)['route'],'blocked')

    def test_partial_ai_coverage_not_elevated(self):
        e,p=fixture();c=e['decision_packet']['matrix'][0];c['task_actions_complete']=False
        h=digest(e['decision_packet']);e['current']['latest_matching_sha256']=h;e['planning_confirmation']['matching_sha256']=h
        self.assertEqual(execute(e,p)['route'],'blocked')

    def test_unknown_cell_not_elevated(self):
        e,p=fixture();e['decision_packet']['matrix'][0]['effective']='unknown'
        h=digest(e['decision_packet']);e['current']['latest_matching_sha256']=h;e['planning_confirmation']['matching_sha256']=h
        r=execute(e,p);d=json.loads(r['payload'])
        self.assertEqual(d['status'],'no_feasible_assignment');self.assertFalse(d['plans'])

    def test_task_ids_not_dropped(self):
        e,p=fixture();e['planning_confirmation']['planning']['task_hours'].pop();reseal_planning(e)
        self.assertEqual(execute(e,p)['route'],'blocked')

    def test_agreement_keeps_single_week_and_budget(self):
        e,p=fixture();d=json.loads(execute(e,p)['payload']);cur={**e['current'],'latest_team_sha256':digest(d)}
        out=agreement_from_team(d,current=cur,plan_index=0,performer_id=p[0]['id'],agreement_id='ENG-DEMO-12')
        c=out['context'];self.assertEqual(c['available_hours'],4)
        self.assertEqual(c['need_version'],1);self.assertIn('2026-11-08',c['time_window'])
        self.assertNotIn('2026-11-15',c['source_text']);self.assertEqual(sum(t['hours'] for t in c['tasks']),4)

    def test_agreement_rejects_stale_need(self):
        e,p=fixture();d=json.loads(execute(e,p)['payload']);cur={**e['current'],'latest_team_sha256':digest(d),'need_version':2}
        with self.assertRaises(BridgeError):agreement_from_team(d,current=cur,plan_index=0,performer_id=p[0]['id'],agreement_id='ENG-DEMO-12')

    def test_agreement_rejects_changed_team(self):
        e,p=fixture();d=json.loads(execute(e,p)['payload']);cur={**e['current'],'latest_team_sha256':digest(d)};d['plans'][0]['assignments'][0]['hours']=6
        with self.assertRaises(BridgeError):agreement_from_team(d,current=cur,plan_index=0,performer_id=p[0]['id'],agreement_id='ENG-DEMO-12')

if __name__=='__main__':unittest.main()
