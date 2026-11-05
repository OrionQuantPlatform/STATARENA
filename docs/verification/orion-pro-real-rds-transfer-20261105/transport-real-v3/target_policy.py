"""Pure admission of the actual independently observed015 native delta."""
from datetime import datetime
import hashlib,json
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3];PATH=BASE/'TARGET_POLICY.json'
SHA='33b1feda0e47bf24da6c8e0c2d40160485acaac242b8c33572c3e9881a65ee83'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hashed(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def bounded(p):
 p=Path(p);assert p.is_file() and not p.is_symlink() and p.stat().st_size<=8*1024**2,'Bounded regular native metadata required';return json.loads(p.read_text())
def stable(n):
 groups=n['groups'];identity=groups.pop('identity');concurrency=groups.pop('concurrency');assert not concurrency
 for row in groups['relations']:row.pop('bytes',None)
 return groups,identity
def journal_native(journal):
 h=hashlib.sha256()
 for version,sha,clock,commit in journal:
  assert version.isdigit() and len(sha)==64 and ' ' in clock and all(x not in clock for x in [',','"','\\','\n']) and commit.isalnum()
  b=f'({version},{sha},"{clock}",{commit})'.encode();h.update(str(len(b)).encode()+b':'+b+b'\n')
 return h.hexdigest()
def load_target_policy():
 assert digest(PATH)==SHA,'Exact V3 target policy bytes required';m=bounded(PATH)
 for path,expected in m['files'].items():assert digest(ROOT/path)==expected,'Protected P2 authority input differs: '+path
 assert m['kind']=='actual_p2_015_transport_target_policy_v1' and m['policyId']=='metric-membership-guard-m18da43-rds015-v1' and m['productionActivation'] is False and m['fullAcceptance'] is False
 receipt=bounded(ROOT/m['actualAdoptionReceiptPath']);assert receipt['kind']=='actual_isolated015_adoption_v1' and receipt['status']=='applied_and_independently_verified' and receipt['independentPolicy']=='P2' and receipt['connectionsClosed'] is True and receipt['remoteBusinessWrites']==[] and receipt['connections']==2 and receipt['selects']==47
 assert receipt['transition']['ddlStatements']==receipt['transition']['journalInserts']==1
 assert [o['path'] for o in receipt['observations']]==[m['actualBeforeNativePath'],m['actualPrecommitNativePath'],m['actualAfterNativePath']]
 assert all(digest(ROOT/o['path'])==o['sha256'] for o in receipt['observations']) and digest(ROOT/m['actualAdoptionReceiptPath'])==m['actualAdoptionReceiptSha256']
 old_receipt=bounded(ROOT/m['priorAccountedReceiptPath']);assert old_receipt['status']=='verified_rollback_B0_only_with_exact_sequence_gaps' and old_receipt['nativeSha256']==m['beforeNativeSha256']==digest(ROOT/m['priorAccountedNativePath']) and len(old_receipt['sequenceDeltas'])==m['accountedSequenceGaps']==24
 before,_=stable(bounded(ROOT/m['actualBeforeNativePath']));assert hashed(before)==old_receipt['actualStateSha256']==m['beforeStateSha256']=='d237d4d98611829aa4c5ba588629fc943de673eeee1b4640ecef8cd087f9b8b4'
 after,identity=stable(bounded(ROOT/m['actualAfterNativePath']));precommit,_=stable(bounded(ROOT/m['actualPrecommitNativePath']));assert precommit==after;del precommit
 assert hashed(after)==m['actualAfterStateSha256']==receipt['observations'][1]['stateSha256']==receipt['observations'][2]['stateSha256'] and digest(ROOT/m['actualAfterNativePath'])==m['actualAfterNativeSha256']
 assert len(identity)==1 and identity[0]['database']==m['target']['database'] and identity[0]['actor']==identity[0]['session_actor']==m['target']['owner'] and identity[0]['read_only']=='on' and identity[0]['ssl'] is True and identity[0]['started_at']==m['target']['postmasterStartedAt']
 assert set(before)==set(after) and {k for k in before if before[k]!=after[k]}=={'guards','journal'} and before['sequences']==after['sequences'] and len(after['sequences'])==67 and after['nonbootstrap']==[]
 delta=[(a,b) for a,b in zip(before['guards'],after['guards']) if a!=b];assert len(before['guards'])==len(after['guards']) and len(delta)==1
 left,right=delta[0];assert right['name']=='ingest.validate_generation' and right['identity']=='g bigint' and {k:v for k,v in left.items() if k!='definition'}=={k:v for k,v in right.items() if k!='definition'} and hashlib.sha256(right['definition'].encode()).hexdigest()==m['canonicalDefinitionSha256']
 assert after['journal'][:-1]==before['journal'] and [r['version'] for r in after['journal']]==['012','013','014','015'];tail=after['journal'][-1];clock=receipt['transition']['newJournalClock'];assert tail['content_sha256']==m['migration015Sha256'] and tail['applied_at']==clock['appliedAt']==clock['transactionStart'] and datetime.fromisoformat(clock['observedAfterInsert'])>=datetime.fromisoformat(clock['appliedAt'])
 projection=lambda rows:[[r[k] for k in ['version','content_sha256','applied_at','code_commit']] for r in rows]
 old=bounded(ROOT/m['previousP1DescriptorPath']);assert projection(before['journal'])==old['journal'] and journal_native(old['journal'])==old['journalNativeSha256'] and projection(after['journal'])==m['targetJournal'] and journal_native(m['targetJournal'])==m['targetJournalNativeSha256']
 assert m['functionProperties']==old['functionProperties'] and m['bootstrapNativeText']==old['bootstrapNativeText'] and m['nativeCatalogueCounts']==old['nativeCatalogueCounts']
 return m

def validate_target_descriptor(d,m):
 keys={'kind','origin','roles','endpoint','catalogueSha256','nativeCatalogueCounts','functionProperties','journal','journalNativeSha256','bootstrapNativeText','rdsP2StateSha256','rdsP2NativeReceiptSha256','rdsP2AdoptionReceiptSha256'}
 assert isinstance(d,dict) and set(d)==keys and d['kind']==m['targetKind'] and d['origin']==m['targetOrigin'],'Distinct P2/015 descriptor required'
 assert d['roles']=={'owner':'statarena_admin','writer':'statarena_ingest','reader':'statarena_runtime'} and d['endpoint']=={'database':m['target']['database'],'actor':m['target']['actor'],'serverVersion':180006,'postmasterStartedAt':datetime.fromisoformat(m['target']['postmasterStartedAt']).isoformat(),'tls':True},'Exact target P2 actor/engine/TLS/epoch required'
 assert isinstance(d['catalogueSha256'],str) and len(d['catalogueSha256'])==64 and all(c in '0123456789abcdef' for c in d['catalogueSha256']) and d['catalogueSha256']!=m['previousP1CatalogueSha256'],'New P2 catalogue digest required'
 assert d['nativeCatalogueCounts']==m['nativeCatalogueCounts'] and d['functionProperties']==m['functionProperties'] and d['journal']==m['targetJournal'] and d['journalNativeSha256']==m['targetJournalNativeSha256'] and d['bootstrapNativeText']==m['bootstrapNativeText'],'Exact post015 catalogue shape, properties, journal/clocks and B0 required'
 assert d['rdsP2StateSha256']==m['actualAfterStateSha256'] and d['rdsP2NativeReceiptSha256']==m['actualAfterNativeSha256'] and d['rdsP2AdoptionReceiptSha256']==m['actualAdoptionReceiptSha256'],'Actual P2 adoption provenance differs'
