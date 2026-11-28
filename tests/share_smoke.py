import json,urllib.request,uuid
from unique_interface import Interface
tag=uuid.uuid4().hex[:8]
demo=Interface(lambda name:f"{tag} hello {name}",title="Unique sharing verification")
app=demo.launch(share=True,block=False,open_browser=False)
try:
 for u in [app.local_url,app.share_url]:
  client=urllib.request.build_opener(urllib.request.ProxyHandler({})) if u==app.local_url else urllib.request.build_opener()
  req=urllib.request.Request(u+"/api/predict",data=b'{"inputs":["Ada"]}',headers={"Content-Type":"application/json","Origin":u})
  with client.open(req,timeout=18) as r: data=json.load(r)
  assert data["outputs"]==[tag+" hello Ada"] and data["duration_ms"]>=0
  print("Verified callback and timing:",u,flush=True)
finally:app.close()
