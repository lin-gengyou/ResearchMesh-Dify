import json
def main(arg1:str,arg2:str):
    p=json.loads(arg1)
    p.update({'schema_version':'capability_profile_0.2','status':'human_confirmation_timeout',
      'matching_use_authorized_in_demo':False,'profile_confirmed_in_demo':False,
      'identity_verified':False,'auto_publish':False,'match_ready':False,
      'review_event':{'event':'profile_confirmation_timeout','run_id':arg2}})
    return {'result':'# 研织｜本人核对尚未完成\n本轮确认已超时；原草稿保留，未授权匹配、未公开、未认证技能。',
      'payload':json.dumps(p,ensure_ascii=False)}
