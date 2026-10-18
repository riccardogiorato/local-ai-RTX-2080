#!/usr/bin/env python3
"""Build distinct-file coding-session requests using Strata's existing agent replay."""
import json,sys
from pathlib import Path
root=Path(__file__).resolve().parent
src=root.parents[1].parent/'strata-0145'
sys.path[:0]=[str(src),str(src/'tools')]
import agent_turns_bench as atb
turns=dict(atb.turns())
for label,tag in [('code-25k','expert-cache.3'),('code-100k','server-option.4')]:
 body={'model':'local-model','messages':turns[tag],'tools':atb.TOOLS,'max_tokens':128,'temperature':0,'seed':1234,'reasoning_effort':'none'}
 (root/f'body-{label}.json').write_text(json.dumps(body)+'\n')
 print(label,tag,len(json.dumps(body)),'bytes; actual tokens recorded by engine')
