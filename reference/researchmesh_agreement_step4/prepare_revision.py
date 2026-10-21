import json
def main(arg1: str):
    p=json.loads(arg1);req=p['revision_request'];tasks=p['terms']['deliverables']
    compact=[]
    for t in tasks:
        fragments=set()
        for i in range(len(t['text'])):
            for j in range(i+2,len(t['text'])+1):
                a=t['text'][i:j]
                if a in req and all(a not in other['text'] for other in tasks if other['id']!=t['id']):fragments.add(a)
        anchors=[a for a in fragments if not any(a!=z and a in z for z in fragments)]
        if t['id'] in req:anchors.append(t['id'])
        ordinal=['第一项','第二项','第三项','第四项','第五项','第六项'][tasks.index(t)]
        if ordinal in req:anchors.append(ordinal)
        compact.append({'id':t['id'],'text':t['text'],'hours':t['hours'],'old_acceptance':t['acceptance'],'valid_request_anchors':sorted(anchors)})
    x={'CURRENT_USER_REVISION_REQUEST':req,'TASKS':compact,'OTHER_CURRENT_TERMS':{k:v for k,v in p['terms'].items() if k!='deliverables'},'available_hours':p['context']['available_hours'],'instruction':'只处理CURRENT_USER_REVISION_REQUEST。任务锚点只能选valid_request_anchors之一。request_quote逐字来自CURRENT_USER_REVISION_REQUEST；新条款必须落实其中的数字、范围或条件。不要输出未要求修改的字段，也不要复制旧条款当作新条款。'}
    return {'result':json.dumps(x,ensure_ascii=False,separators=(',',':'))}
