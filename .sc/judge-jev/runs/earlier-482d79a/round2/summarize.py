import json,sys
R1={'obligations':{'2','3','4+'},'joined_by':{'and-list','alternatives','obligation+rationale'}}
R2={'term':{'project term defined nowhere','vague qualifier','undefined acronym'},'check':{'needs a measure','none'}}
d=json.load(open(sys.argv[1]))
for r in d['data']['results']:
    print(r['record']['id'], r['verdict'], 'matched', r['waves'][0].get('matched_statements'))
    for item in r['waves'][0]['reason']:
        s=item['statement']; a={x['id']:(x['choice'],x['confidence']) for x in item['answers']}
        f=[]
        if all(a[k][0] in v for k,v in R1.items()): f.append('rule1')
        if any(a[k][0] in v for k,v in R2.items()): f.append('rule2')
        print('  s%d [%s] %s | %s'%(s['index'],','.join(f) or 'yes', {k:'%s %.2f'%v for k,v in a.items()}, s['text'].replace('\n',' ')))
