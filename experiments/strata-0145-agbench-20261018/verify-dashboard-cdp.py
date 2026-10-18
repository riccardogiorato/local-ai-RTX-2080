"""Use installed Chromium and aiohttp for local-only browser QA, no downloads."""
import asyncio,base64,json,subprocess,tempfile,time,urllib.request
from pathlib import Path
import aiohttp
ROOT=Path(__file__).resolve().parent
async def main():
 with tempfile.TemporaryDirectory(prefix='strata-dashboard-chromium-') as profile:
  proc=subprocess.Popen(['/usr/bin/chromium','--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=9223','--remote-debugging-address=127.0.0.1','--user-data-dir='+profile,'about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   async with aiohttp.ClientSession() as session:
    for _ in range(100):
     try:
      async with session.put('http://127.0.0.1:9223/json/new?about:blank') as r:target=await r.json()
      break
     except Exception:await asyncio.sleep(.1)
    else:raise RuntimeError('Chromium debugging endpoint did not start')
    async with session.ws_connect(target['webSocketDebuggerUrl']) as ws:
     counter=0;errors=[]
     async def call(method,params=None):
      nonlocal counter
      counter+=1;i=counter;await ws.send_json({'id':i,'method':method,'params':params or {}})
      while True:
       msg=await ws.receive_json()
       if msg.get('method')=='Runtime.exceptionThrown':errors.append(msg['params'])
       if msg.get('id')==i:
        assert 'error' not in msg,msg
        return msg.get('result',{})
     async def evaluate(js):
      r=await call('Runtime.evaluate',{'expression':js,'returnByValue':True,'awaitPromise':True});assert 'exceptionDetails' not in r,r
      return r['result'].get('value')
     await call('Page.enable');await call('Runtime.enable')
     await call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
     await call('Page.navigate',{'url':'http://127.0.0.1:8765/benchmarks/index.html'})
     for _ in range(100):
      if await evaluate("document.querySelector('#status')?.textContent==='Benchmark complete'"):break
      await asyncio.sleep(.1)
     checks=await evaluate("""(()=>{let q=s=>document.querySelector(s),rows=()=>document.querySelectorAll('#tasks tr').length;let r={status:q('#status').textContent,stock:q('#stock-pass').textContent,optimized:q('#opt-pass').textContent,wall:q('#wall-change').textContent,prefill:q('#prefill').textContent,rows:rows(),chartRows:document.querySelectorAll('.chart-row').length};q('#failures').click();r.failureFilter=q('#tasks').textContent.includes('No failures');q('#all').click();r.allFilter=rows()===11;return r})()""")
     assert checks['stock']==checks['optimized']=='11 / 11',checks
     assert checks['rows']==checks['chartRows']==11 and checks['failureFilter'] and checks['allFilter'],checks
     assert '25.2%' in checks['wall'].replace(',','.') and '695' in checks['prefill'],checks
     async def screenshot(name):
      size=await evaluate('({width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,viewport:innerWidth})')
      img=await call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':True,'clip':{'x':0,'y':0,'width':size['width'],'height':size['height'],'scale':1}})
      (ROOT/name).write_bytes(base64.b64decode(img['data']));return size
     desktop=await screenshot('dashboard-desktop.png')
     await call('Emulation.setDeviceMetricsOverride',{'width':375,'height':812,'deviceScaleFactor':1,'mobile':False})
     mobile=await screenshot('dashboard-mobile.png');assert mobile['width']<=375,mobile
     assert not errors,errors
     result={'browser':'Installed Chromium through local CDP','fallback_reason':'T3 preview_open failed twice and html_preview remained unavailable during its browser download.','desktop':checks,'desktop_size':desktop,'mobile':mobile,'runtime_errors':errors}
     (ROOT/'dashboard-qa.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
  finally:
   proc.terminate()
   try:proc.wait(timeout=10)
   except subprocess.TimeoutExpired:proc.kill();proc.wait()
asyncio.run(main())
