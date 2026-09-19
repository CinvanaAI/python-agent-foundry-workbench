import argparse
import json
import tempfile
from pathlib import Path
from collection_handoff import CollectionHandoff
from package_manager import PackageEditorController
from Operations.assembly.assembly_manager import AssemblyManager
from Operations.task_runner import run_task

parser=argparse.ArgumentParser(description='Create one synthetic package and agent task, then run it locally.')
parser.add_argument('--workspace',type=Path)
args=parser.parse_args()
root=args.workspace.resolve() if args.workspace else Path(tempfile.mkdtemp(prefix='foundry-demo-'))
if root.exists() and any(root.iterdir()):
    raise FileExistsError('Use an empty workspace so this example cannot replace your work.')
root.mkdir(parents=True,exist_ok=True)
handoff=CollectionHandoff(str(root))
handoff.initialize_storage_registry()
handoff.package_post_save_review_enabled=False
source="def normalize_text(value):\n    return ' '.join(value.split())"
PackageEditorController(handoff=handoff).save_from_fields('normalizer','Active',[],[],[{'argument_value_name':'value','argument_question':'Text?'}],[{'return_value_name':'normalized','return_description':'Clean text'}],[],source)
task={'name':'Normalize','task_status':'On Demand','packages':[{'name':'normalizer','package_status':'Active','logic':{'logic_source':source}}],'workflow':{'workflow_source':"from normalizer import normalize_text\n\ndef run_workflow(payload):\n    return {'normalized': normalize_text(payload['value'])}"}}
agent={'name':'DemoAgent','default_returns':[],'groups':[{'name':'Outcasts','tasks':[task]}]}
manager=AssemblyManager(handoff=handoff)
agent_path=manager.save_agent('DemoAgent',agent)
result=run_task(root,'DemoAgent','Normalize',{'value':'  hello   foundry  '},handoff=handoff)
assert result=={'normalized':'hello foundry'}
print(json.dumps({'result':result,'agent_record':agent_path,'workspace':str(root),'next':'Open main.py --workspace with this workspace, choose Agent, and load DemoAgent.'},indent=2))
