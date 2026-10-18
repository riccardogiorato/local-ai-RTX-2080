#!/usr/bin/env python3
import hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parent
dst=Path('/home/riccardogiorato/models/flashnext-gsq-rco-nvme')
name='Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf'
p=dst/name
while not p.exists():time.sleep(2)
print(time.ctime(),'Verifying SSD main shard',flush=True)
h=hashlib.sha256();start=time.monotonic()
with p.open('rb') as f:
 while b:=f.read(8*1024*1024):h.update(b)
expected='69820c02ec7d0b45ef2ebb19d6620299db749fe2aded7f39f93c6b88b199b720'
assert h.hexdigest()==expected,(h.hexdigest(),expected)
row=dict(file=str(p),sha256=h.hexdigest(),matches_local_manifest=True,seconds=time.monotonic()-start)
(root/'ssd-verify-main.json').write_text(json.dumps(row,indent=2)+'\n');print(row,flush=True)
assert json.loads((root/'ssd-verify-ple.json').read_text())['sha256']=='316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113'
alias=Path('/home/riccardogiorato/models/flashnext-gsq-rco')
assert alias.is_symlink()
original=os.readlink(alias)
assert original=='/mnt/archive/local-models/flashnext-gsq-rco',original
shutil.copy2(Path(original)/'sha.txt',dst/'sha.txt')
tmp=alias.with_name(alias.name+'.ssd-switch')
assert not tmp.exists() and not tmp.is_symlink()
os.symlink(dst.name,tmp);os.replace(tmp,alias)
assets=[alias/name,alias/'Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf',Path('/home/riccardogiorato/Desktop/github/strata-port/packs/q2_0-gsq/dense.bin'),Path('/home/riccardogiorato/Desktop/github/strata-port/mtp/rt/experts.bin'),Path('/home/riccardogiorato/Desktop/github/strata-port/mtp/rt/dense.bin'),Path('/home/riccardogiorato/Desktop/github/strata-port/mtp/rt/draft_vocab.bin'),Path('/home/riccardogiorato/Desktop/github/strata-port/packs/q2_0-gsq/tokenizer/vocab.json'),Path('/home/riccardogiorato/Desktop/github/strata-0145/data/expert-profile.bin')]
assetrows=[]
for asset in assets:
 mount=subprocess.check_output(['findmnt','-T',str(asset),'-n','-o','SOURCE,FSTYPE,TARGET'],text=True).strip()
 assert '/mnt/archive' not in mount,(asset,mount)
 assetrows.append(dict(path=str(asset),resolved=str(asset.resolve()),bytes=asset.stat().st_size,mount=mount))
(root/'ssd-migration.json').write_text(json.dumps({'alias':str(alias),'old_target':original,'new_target':str(alias.resolve()),'hdd_backup_retained':True,'assets':assetrows},indent=2)+'\n')
print(time.ctime(),'SSD alias switched; all required assets checked',flush=True)
with (root/'full-runner.log').open('w') as log:
 subprocess.run([sys.executable,'-u',str(root/'run-full.py')],stdout=log,stderr=subprocess.STDOUT,check=True)
print('FULL BENCHMARK DONE',flush=True)
