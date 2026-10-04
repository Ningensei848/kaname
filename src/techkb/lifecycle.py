"""Preserve all unrelated rules; manage Delete/age on explicit raw source prefixes."""


def lifecycle_plan(bucket, sources):
    configured = [s for s in sources if s.raw_retention_days is not None]
    prefixes = {'raw/'+s.id+'/' for s in configured}
    rules = list(bucket.lifecycle_rules)
    kept=[]
    for rule in rules:
        condition=rule.get('condition',{})
        matches=condition.get('matchesPrefix',[])
        # Replace only rules whose complete scope and condition are ours.
        if (rule.get('action')=={'type':'Delete'} and set(condition)=={'age','matchesPrefix'} and
                len(matches)==1 and matches[0] in prefixes):
            continue
        kept.append(rule)
    added=[{'action':{'type':'Delete'},'condition':{'age':s.raw_retention_days,'matchesPrefix':['raw/'+s.id+'/']}}
           for s in sorted(configured,key=lambda s:s.id)]
    return kept+added


def configure_lifecycle(store,sources,apply=False):
    bucket=store.bucket
    # GCSStore.get_bucket captured current metageneration and access controls.
    original=list(bucket.lifecycle_rules)
    target=lifecycle_plan(bucket,sources)
    changed=original!=target
    if apply and changed:
        if bucket.metageneration is None:
            raise ValueError('bucket metageneration missing')
        bucket.lifecycle_rules=target
        bucket.patch(if_metageneration_match=int(bucket.metageneration))
    return dict(status='success',applied=bool(apply and changed),changed=changed,rules=target)
