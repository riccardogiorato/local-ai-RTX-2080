#!/usr/bin/env python3
"""Replay saved agent turns through the current chat template; execute no tools."""
import json,pathlib,hashlib,time
from bench import OUT,call,record
source=pathlib.Path('/tmp/agentic-run/nemotron-bolt-e4b/task1-js-bugfix/pi-session.jsonl')
msgs=[]; snapshots=[]; usage=[]
for line in source.read_text().splitlines():
 ev=json.loads(line)
 if ev.get('type')!='message_end':continue
 m=ev['message'];role=m['role'];content=m.get('content',[])
 if role=='system':
  msgs.append({'role':'system','content':m.get('content') or '\n\n'.join(str(v) for v in m.get('sections',{}).values())})
 elif role=='user':msgs.append({'role':role,'content':'\n'.join(c.get('text','') for c in content)})
 elif role=='assistant':
  usage.append(m.get('usage',{}))
  a={'role':role,'content':'\n'.join(c.get('text','') for c in content if c.get('type')=='text') or None}
  calls=[{'id':c['id'],'type':'function','function':{'name':c['name'],'arguments':json.dumps(c['arguments'])}} for c in content if c.get('type')=='toolCall']
  if calls:a['tool_calls']=calls
  reasoning='\n'.join(c.get('thinking','') for c in content if c.get('type')=='thinking')
  if reasoning:a['reasoning_content']=reasoning
  msgs.append(a)
 elif role=='toolResult':
  msgs.append({'role':'tool','tool_call_id':m['toolCallId'],'content':'\n'.join(c.get('text','') for c in content)})
  snapshots.append(json.loads(json.dumps(msgs)))
# Tool signatures are reconstructed; histories and tool results come from the real run.
tools=[{'type':'function','function':{'name':n,'description':d,'parameters':{'type':'object','properties':props}}} for n,d,props in [
 ('bash','Execute a bash command',{'command':{'type':'string'}}),('read','Read a file',{'path':{'type':'string'}}),('edit','Edit a file',{'path':{'type':'string'},'edits':{'type':'array','items':{'type':'object'}}}),('write','Write a file',{'path':{'type':'string'},'content':{'type':'string'}})]]
(OUT/'cache-source.json').write_text(json.dumps({'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'original_usage':usage,'snapshots':snapshots,'tools':tools},indent=2))
prompts=[]
for messages in snapshots:
 r=call('apply-template',{'messages':messages,'tools':tools,'chat_template_kwargs':{'enable_thinking':True}})
 prompts.append(r['prompt'])
(OUT/'cache-prompts.json').write_text(json.dumps(prompts))
for run,cache in [(0,False),(0,True),(1,False),(1,True),(2,True),(2,False)]:
 # Reset by explicitly prefilling an unrelated prompt before each sequence.
 call('completion',{'prompt':'Reset replay slot.','n_predict':1,'temperature':0,'cache_prompt':False})
 for i,prompt in enumerate(prompts):
  record('cache-on' if cache else 'cache-off','cache-replay',str(i+1),run,{'prompt':prompt,'n_predict':1,'temperature':0,'seed':42,'cache_prompt':cache,'samplers':['temperature']})
print('historical_usage',json.dumps(usage),flush=True)
