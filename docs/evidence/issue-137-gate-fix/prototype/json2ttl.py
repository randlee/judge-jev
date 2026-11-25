import json,sys,re
src,kind=sys.argv[1],sys.argv[2]; d=json.load(open(src)); tid=d["id"]
def slug(s): return re.sub(r"-+","-",re.sub(r"[^a-z0-9]+","-",s.lower())).strip("-") or "x"
def lit(s): return json.dumps(s,ensure_ascii=False)
def opt(q,c): return f"o:{kind}.{q}:{slug(c)}"
out=['@prefix jj: <urn:judge-jev:ontology#> .','@prefix t:  <urn:judge-jev:tree:> .','@prefix q:  <urn:judge-jev:question:> .','@prefix o:  <urn:judge-jev:option:> .','',
f'# The shipped {kind.upper()} quality tree (the same content as {tid}.json):','# the questions are resources with IRIs, so another tree or wave may ask them.','',
f't:{tid} a jj:Tree ;',f'    jj:id {lit(tid)} ;',f'    jj:kind {lit(d["kind"])} ;',f'    jj:version {d["version"]} ;',f'    jj:approved {"true" if d.get("approved") else "false"} ;']
if d.get("note"): out.append(f'    jj:note {lit(d["note"])} ;')
out.append(f'    jj:start t:{tid}:{d["start"]} ;'); out.append('    jj:node '+' , '.join(f"t:{tid}:{n}" for n in d["nodes"])+' .'); out.append('')
questions={}
def conds(m):
    return ' ,\n        '.join(f'[ a jj:Condition ; jj:question q:{kind}.{q} ;\n          jj:choice '+' , '.join(opt(q,c) for c in ([v] if isinstance(v,str) else v))+' ]' for q,v in m.items())
for nid,n in d["nodes"].items():
    iri=f"t:{tid}:{nid}"
    if "questions" not in n:
        out+= [f'{iri} a jj:Leaf ;',f'    jj:id {lit(nid)} ;',f'    jj:verdict {lit(n["verdict"])} .','']; continue
    for q,v in n["questions"].items(): questions.setdefault(q,v)
    rules=n.get("next") or n["verdict_rules"]
    L=[f'{iri} a jj:Wave ;',f'    jj:id {lit(nid)} ;']
    if n.get("per"): L+= [f'    jj:per {lit(n["per"])} ;',f'    jj:statements {lit(n["statements"])} ;']+[f'    jj:modal {lit(m)} ;' for m in n.get("modals",[])]
    if n.get("only_matched"): L.append('    jj:onlyMatched true ;')
    L.append('    jj:asks '+' , '.join(f"q:{kind}.{q}" for q in n["questions"])+' ;')
    L.append('    jj:rule '+' , '.join(f"{iri}:rule-{i}" for i in range(1,len(rules)+1))+' .'); out+=L+['']
    for i,r in enumerate(rules,1):
        R=[f'{iri}:rule-{i} a jj:{"BranchRule" if "next" in n else "VerdictRule"} ;',f'    jj:rank {i} ;']
        if "next" in n:
            R.append(f'    jj:goto t:{tid}:{r["goto"]}'+(' ;' if r.get("when") else ' .'))
            if r.get("when"): R.append('    jj:whenAll\n        '+conds(r["when"])+' .')
        else:
            parts=[f'    jj:verdict {lit(r["verdict"])}']
            if r.get("all"): parts.append('    jj:whenAll\n        '+conds(r["all"]))
            if r.get("any"): parts.append('    jj:whenAny\n        '+conds(r["any"]))
            R.append(' ;\n'.join(parts)+' .')
        out+=R+['']
rank=0
for q,v in questions.items():
    rank+=1; os_=list(v["criteria"])
    out+= [f'q:{kind}.{q} a jj:Question ;',f'    jj:id {lit(q)} ;',f'    jj:rank {rank} ;',f'    jj:instructions {lit(v["instructions"])} ;','    jj:option '+' , '.join(opt(q,c) for c in os_)+' .','']
    for j,c in enumerate(os_,1):
        out+= [f'{opt(q,c)} a jj:Option ; jj:rank {j} ;',f'    jj:label {lit(c)} ;',f'    jj:criterion {lit(v["criteria"][c])} .']
    out.append('')
print("\n".join(out).rstrip()+"\n",end="")
