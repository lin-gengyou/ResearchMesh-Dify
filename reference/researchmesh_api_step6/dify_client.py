"""Small server-side Dify Service API client; no UI/session endpoints."""
import json,urllib.request,urllib.error,urllib.parse

class DifyHTTPError(RuntimeError):
    def __init__(self,status,body):
        self.status=status;self.body=body
        super().__init__(f'Dify HTTP {status}')

class DifyClient:
    def __init__(self,key,base='https://api.dify.ai/v1',on_event=None):
        self.key=key.strip();self.base=base.rstrip('/');self.on_event=on_event
    def request(self,method,path,body=None,stream=False):
        data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None
        headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'}
        if stream:headers['Accept']='text/event-stream'
        req=urllib.request.Request(self.base+path,data=data,headers=headers,method=method)
        try:
            response=urllib.request.urlopen(req,timeout=40)
        except urllib.error.HTTPError as e:
            raise DifyHTTPError(e.code,e.read().decode(errors='replace')) from None
        if stream:return response
        with response:return json.load(response)
    def events(self,method,path,body=None):
        # Keep transport errors visible. Never automatically repeat a POST.
        with self.request(method,path,body,stream=True) as response:
            data=[]
            for raw in response:
                line=raw.decode().rstrip('\r\n')
                if not line:
                    if data:
                        event=json.loads('\n'.join(data));data=[]
                        if self.on_event:self.on_event(event)
                        yield event
                        if event.get('event') in ('workflow_paused','workflow_finished','error'):break
                elif line.startswith('data:'):data.append(line[5:].lstrip(' '))
            if data:raise RuntimeError('Incomplete SSE frame: reconnect existing run; do not restart')
    def start(self,inputs,user):
        return list(self.events('POST','/workflows/run',{'inputs':inputs,'user':user,'response_mode':'streaming'}))
    def resume(self,run_id,user):
        query=urllib.parse.urlencode({'user':user,'include_state_snapshot':'true','continue_on_pause':'true'})
        return list(self.events('GET','/workflow/'+urllib.parse.quote(run_id,safe='')+'/events?'+query))
    def form(self,token):return self.request('GET','/form/human_input/'+urllib.parse.quote(token,safe=''))
    def submit(self,token,inputs,action,user):
        return self.request('POST','/form/human_input/'+urllib.parse.quote(token,safe=''),{'inputs':inputs,'action':action,'user':user})
    def detail(self,run_id):return self.request('GET','/workflows/run/'+urllib.parse.quote(run_id,safe=''))

def redact(value):
    if isinstance(value,dict):return {k:('[REDACTED]' if k in ('form_token','api_key','authorization') else redact(v)) for k,v in value.items()}
    if isinstance(value,list):return [redact(v) for v in value]
    return value
