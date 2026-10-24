#!/usr/bin/env python3
import json,os,subprocess
import bench
try:
 for label,kwargs in [('baseline',{}),('mtp-d2',{'kind':'draft-mtp','draft':bench.MTP,'depth':2}),('native-cublas',{'engine':'cublas'})]:
  if kwargs:bench.start('verify-'+label,**kwargs)
  else:
   assert bench.call('health')['status']=='ok'
   image=subprocess.check_output(['sudo','docker','inspect','bolt-serve','--format','{{.Config.Image}}'],text=True).strip()
   assert image==bench.IMAGE,image
  env=dict(os.environ,BOLT_MEDIAN_BUDGET='2000',BOLT_PROBE_OUT=str(bench.OUT/(label+'-probes.jsonl')))
  with (bench.OUT/(label+'-probes.log')).open('w') as f:
   subprocess.run(['python3',str(bench.ROOT/'experiments/nemotron-bolt-e4b-20261023/probe-bolt.py')],env=env,check=True,stdout=f,stderr=subprocess.STDOUT)
  label_agent='bolt-four-tricks-'+label
  env=dict(os.environ,PI_PROVIDER='llamacpp-local',TASKS_GLOB='task1-*/ task9-*/')
  with (bench.OUT/(label+'-agentic.log')).open('w') as f:
   subprocess.run(['bash',str(bench.ROOT/'benchmarks/agentic-bench.sh'),label_agent,'180'],env=env,check=True,stdout=f,stderr=subprocess.STDOUT)
  bench.snapshot('verify-'+label)
finally:bench.restore()
