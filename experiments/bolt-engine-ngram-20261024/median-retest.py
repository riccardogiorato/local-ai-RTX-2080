import ast,json,pathlib,re,urllib.request
root=pathlib.Path(__file__).resolve().parent
source=(root.parent/'nemotron-bolt-e4b-20261023/probe-bolt.py').read_text()
# Read only the existing task constants; importing would rerun the whole probe suite.
ns={}
for node in ast.parse(source).body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['MEDIAN_BUG','MEDIAN_TASK'] for t in node.targets): exec(compile(ast.Module(body=[node],type_ignores=[]),'<task>','exec'),ns)
for thinking,budget in [(True,1000),(True,2000),(False,1000)]:
 payload={'model':'local-model','messages':[{'role':'user','content':ns['MEDIAN_TASK']}],'temperature':0,'max_tokens':budget,'chat_template_kwargs':{'enable_thinking':thinking}}
 req=urllib.request.Request('http://127.0.0.1:8080/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
 r=json.load(urllib.request.urlopen(req,timeout=300)); msg=r['choices'][0]['message']; txt=msg.get('content') or ''; m=re.search(r'```(?:python)?\s*\n(.*?)```',txt,re.S)
 passed=False; error=None
 try:
  env={}; exec(m.group(1) if m else txt,env); passed=all(env['median'](xs)==v for xs,v in [([3,1,2,4,6,5],3.5),([1,2,3],2),([5],5)])
 except Exception as e: error=str(e)
 row={'probe':'median-retest','thinking':thinking,'budget':budget,'pass':passed,'error':error,'response':r}
 with (root/'median-retests.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 print(json.dumps({k:v for k,v in row.items() if k!='response'} | {'usage':r.get('usage'),'finish_reason':r['choices'][0]['finish_reason'],'content':txt}),flush=True)
