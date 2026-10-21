from pathlib import Path
import subprocess,sys
root=Path(__file__).resolve().parents[1]/"reference"
suites=[("researchmesh_capability_step7","test_capability"),("researchmesh_matching_home_step8","test_step8"),("researchmesh_need_bridge_step10","test_step10"),("researchmesh_need_matching_step11","test_step11"),("researchmesh_match_team_step12","test_step12"),("researchmesh_agreement_delivery_step13","test_step13"),("researchmesh_api_step6","test_live_contract"),("researchmesh_finalize_step15","test_step15")]
for folder,module in suites:
    result=subprocess.run([sys.executable,"-m","unittest","-v",module],cwd=root/folder)
    if result.returncode:raise SystemExit(result.returncode)
subprocess.run([sys.executable,str(root/"researchmesh_closing_step14/check_capability_link.py")],check=True)
print("All 96 regression tests and 9 capability-link assertions passed.")
