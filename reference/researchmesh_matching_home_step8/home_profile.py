"""User-home content projection reference; not an auth, storage or publish service."""
import hashlib,json
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def preview_home(profile_outputs,*,owner_id,settings,contribution_outputs=()):
    p=json.loads(profile_outputs.get('profile_packet') or '{}')
    confirmed=p.get('status')=='confirmed_matching_clues' and p.get('profile_confirmed_in_demo') is True
    experiences=[]
    if confirmed:
        for c in p.get('claims',[]):
            if c.get('attribution')=='personal':
                experiences.append({'id':c['id'],'title':c['skill_label'],'description':c['claim_scope'],
                  'basis':'本人自述已在演示中核对，未经外部核验',
                  'independence':c['independence'],'skill_certified':False})
    contributions=[]
    for out in contribution_outputs:
        d=json.loads(out.get('contribution_packet') or '{}')
        a=d.get('agreement',{})
        if a.get('performer_id')!=owner_id:continue
        # Privately visible owner preview; a Dify draft grant never makes a public entry.
        contributions.append({'id':d.get('contribution_event',{}).get('run_id',''),
          'agreement_id':a.get('id'),'version':a.get('version'),'status':d.get('contribution_status'),
          'summary':[x['scope'] for x in d.get('contribution_claims',[])],
          'public_draft_granted_in_demo':d.get('public_draft_authorized_in_demo') is True,
          'actual_publication':False,'identity_verified':False})
    allowed_settings=('display_name','headline','bio','campus','major','collaboration_intent')
    header={k:settings[k] for k in allowed_settings if isinstance(settings.get(k),str)}
    header.setdefault('display_name','研织成员')
    interests=[{'id':'interest_'+str(i+1),'label':x['label'],'type':'learning_interest'} for i,x in enumerate(p.get('learning_interests',[]))]
    home={'schema_version':'researchmesh_home_0.1','owner_id':owner_id,'view':'owner_preview',
      'header':header,'experiences':experiences,'learning_interests':interests,
      'contributions':contributions,'public_authorized':False,'auto_publish':False,
      'source_profile_hash':p.get('draft_hash'),'identity_verified':False}
    home['preview_hash']=hashlib.sha256(canonical(home).encode()).hexdigest()
    return home
def public_projection(preview,*,publication):
    """publication must be a trusted server record scoped to this exact preview hash.
    No networking/publishing occurs. Caller performs actual authentication and consent.
    """
    material={k:v for k,v in preview.items() if k!='preview_hash'}
    actual_hash=hashlib.sha256(canonical(material).encode()).hexdigest()
    if (preview.get('preview_hash')!=actual_hash or publication.get('status')!='published' or publication.get('owner_id')!=preview.get('owner_id')
      or publication.get('preview_hash')!=preview.get('preview_hash')):
        return {'schema_version':'researchmesh_home_0.1','view':'public','status':'not_published'}
    header={k:v for k,v in preview['header'].items() if k in publication.get('header_fields',[])}
    exp=[x for x in preview['experiences'] if x['id'] in publication.get('experience_ids',[])]
    interests=[x for x in preview['learning_interests'] if x['id'] in publication.get('interest_ids',[])]
    # Contribution publication has its own records; general profile publication is insufficient.
    allowed_contributions=publication.get('separately_published_contributions',{})
    contributions=[{'id':'contribution_'+hashlib.sha256(x['id'].encode()).hexdigest()[:16],
      'version':x['version'],'summary':x['summary'],'source_status':x['status']}
      for x in preview['contributions'] if x['id'] and allowed_contributions.get(x['id'])==hashlib.sha256(canonical(x).encode()).hexdigest()]
    return {'schema_version':'researchmesh_home_0.1','view':'public','status':'published_projection',
      'header':header,'experiences':exp,'learning_interests':interests,'contributions':contributions,
      'identity_verified':False,'skill_certified':False}
