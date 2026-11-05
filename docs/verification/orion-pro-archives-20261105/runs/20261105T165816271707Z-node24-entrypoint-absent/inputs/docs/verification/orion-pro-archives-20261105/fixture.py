"""Synthetic typed archive membership and observations; written before reader."""
from __future__ import annotations
from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[3]
source=ROOT/'docs/verification/orion-pro-competitions-20261105/fixture.py'
spec=importlib.util.spec_from_file_location('archives_competition_base',source)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
NOW,hashed=base.NOW,base.hashed
SEASON='2026/2027'
CONTRACT={'results':'orion-archive-results-v1','goals':'orion-archive-goals-v1','supplemental':'orion-supplemental-v1','point':'orion-archive-match-v1'}

class ArchiveFixture(base.CompetitionFixture):
    def document(self,role,key,label):
        source=self.ids['source'];alias='l_'+str('ABC'.index(key)+1).zfill(6)
        prefix={'results':'archive-results','goals':'archive-goals','supplemental':'supplemental','point':'archive-match'}[role]
        dataset_key=f'{prefix}:{alias}:{SEASON}'
        dataset=self._row('ingest.source_datasets','source_id=%s AND dataset_key=%s',(source,dataset_key))
        if not dataset:dataset=self._insert('ingest.source_datasets',source_id=source,dataset_key=dataset_key,contract_version=CONTRACT[role],source_url='https://fixture.invalid/archives',license_code='fixture-archive-license')
        doc,_=self._record(source,dataset['id'],'archive-'+label)
        return doc

    def record(self,doc,locator,kind,*,ordinal=None,external=None):
        return self._insert('ingest.source_records',source_id=doc['source_id'],document_id=doc['id'],locator_kind='json_pointer',locator=locator,record_kind=kind,ordinal=ordinal,external_key=external)

    def binding(self,docs):
        sid=self.conn.execute('SELECT id FROM ingest.dataset_snapshots WHERE generation=%s',(self.g,)).fetchone()[0]
        for doc in docs:self._insert('ingest.dataset_snapshot_documents',snapshot_id=sid,document_id=doc['id'])

    def observation(self,doc,mid,*,note=None,root=None):
        m=self.match_rows[mid];sides=self.sides[mid]
        record=root or self.record(doc,'/matches/'+mid,'archive_result_v1',external=mid)
        return self._insert('football.match_observation_details',source_record_id=record['id'],match_id=m['id'],match_revision_id=m['revision_id'],resolution_state='resolved',
            source_match_key=mid,source_competition_label='Observed archive competition',source_season_label='2026–27 source',source_home_label=sides['home']['participant_label'],source_away_label=sides['away']['participant_label'],
            source_date_text='8 Nov 2026 (source)' if mid=='m_000002' else (m['match_date'].isoformat() if m['match_date'] else None),
            source_round_label=m['round_label'],source_time_text='20:00 observed' if mid=='m_000002' else None,source_stage_label='Knockout source stage' if mid=='m_000002' else None,
            source_venue_label='Observed venue' if mid=='m_000002' else None,attendance=0 if mid=='m_000002' else None,attendance_text='0 (source)' if mid=='m_000002' else None,
            date_note='Approximate source date' if mid=='m_000002' else None,result_code='not_played' if mid=='m_000003' else None,
            notes=note if note is not None else ('Original observation note' if mid=='m_000002' else None))

    def goals(self,doc,mid,events,variant,*,canonical=False,declared_count=None):
        m=self.match_rows[mid];root=self.record(doc,'/matches/'+mid,'archive_goals_match_v1',external=mid)
        count=len(events) if declared_count is None else declared_count
        cov=self._insert('ingest.match_coverage',match_id=m['id'],match_revision_id=m['revision_id'],source_id=doc['source_id'],source_record_id=root['id'],document_id=doc['id'],feature_code='events',variant_key=variant,is_canonical=canonical,
            coverage_state='available' if count else 'empty_response',collection_state='present' if count else 'empty',observed_row_count=count,checked_at=NOW)
        rows=[]
        for seq,(ordinal,minute,actor,own_goal) in enumerate(events):
            rec=self.record(doc,root['locator']+'/events/'+str(ordinal),'archive_goal_v1',ordinal=ordinal)
            side=self.sides[mid]['home']
            rows.append(self._insert('football.match_events',match_id=m['id'],match_revision_id=m['revision_id'],match_team_revision_id=side['revision_id'],team_id=side['team_id'],
                source_id=doc['source_id'],source_record_id=rec['id'],feature_code='events',variant_key=variant,event_type='goal',event_seq=seq,source_ordinal=ordinal,
                period_code='first_half',period_definition_version='bootstrap_v1',minute=minute,minute_added=1 if minute==45 else None,player_id=actor,is_penalty=False,is_own_goal=own_goal,score_home=1,score_away=0))
        return cov,rows

    def prepare_archive(self):
        self.docs={}
        with self._generation('archives_typed_admitted_inputs') as g:
            self.archive_generation=g
            for role,key in [('results','A'),('goals','A'),('goals','B'),('goals','C'),('supplemental','B'),('point','A')]:
                self.docs[(role,key)]=self.document(role,key,role+'-'+key)
            self.binding(self.docs.values())
            for mid in ('m_000001','m_000002','m_000003'):self.observation(self.docs[('results','A')],mid)
            actor=self.conn.execute('SELECT id FROM football.players ORDER BY id LIMIT 1').fetchone()[0]
            # Physical insertion and source ordering intentionally differ.
            self.goals(self.docs[('goals','A')],'m_000001',[(1,45,actor,False),(0,12,actor,False)],'archive:goals:v1')
            self.goals(self.docs[('goals','A')],'m_000002',[(0,13,None,True)],'archive:goals:v1')
            self.goals(self.docs[('goals','A')],'m_000003',[],'archive:goals:v1')
            self.goals(self.docs[('goals','B')],'m_000004',[(0,20,None,False)],'archive:goals:v1')
            self.goals(self.docs[('goals','B')],'m_000006',[],'archive:goals:v1')
            self.goals(self.docs[('goals','C')],'m_000005',[],'archive:goals:v1')
            for mid in ('m_000004','m_000006'):
                self.observation(self.docs[('supplemental','B')],mid)
                # Observations and coverage roots may coexist under exact locators.
                doc=self.docs[('supplemental','B')];m=self.match_rows[mid]
                rr=self.record(doc,'/goals/'+mid,'archive_goals_match_v1',external=mid)
                self._insert('ingest.match_coverage',match_id=m['id'],match_revision_id=m['revision_id'],source_id=doc['source_id'],source_record_id=rr['id'],document_id=doc['id'],feature_code='events',variant_key='archive:supplemental:v1',is_canonical=False,coverage_state='empty_response',collection_state='empty',observed_row_count=0,checked_at=NOW)
            doc=self.docs[('point','A')];mid='m_000001';m=self.match_rows[mid]
            rr=self.record(doc,'/data','archive_point_match_v1',external=mid)
            self.observation(doc,mid,root=rr)
            self._insert('ingest.match_coverage',match_id=m['id'],match_revision_id=m['revision_id'],source_id=doc['source_id'],source_record_id=rr['id'],document_id=doc['id'],feature_code='match',variant_key='archive:match:v1',is_canonical=True,coverage_state='available',collection_state='present',observed_row_count=1,checked_at=NOW)
            self.goals(doc,mid,[(0,99,actor,False)],'archive:legacy-decoy',canonical=True)
        self.archive_builds={k:self.build(k,g,g) for k in 'ABC'};self.publish(self.archive_builds,'archive_routes_published')
        return {'generation':g,'builds':self.archive_builds,'documentIds':{role+':'+key:d['id'] for (role,key),d in self.docs.items()}}

    def unbound(self):
        with self._generation('unbound_archive_source') as g:
            doc=self.document('results','C','unbound-results-C');self.observation(doc,'m_000005');self.binding([self.docs[('goals','C')]])
        build=self.build('C',g,g);self.publish({'C':build},'archive_unbound_not_admitted')
        return {'generation':g,'build':build,'unboundDocumentId':doc['id']}

    def correction_archive(self,mode='correction'):
        with self._generation('archive_source_'+mode) as g:
            doc=self.document('results','A',mode+'-results-A')
            for mid in ('m_000001','m_000002','m_000003'):
                self.observation(doc,mid,note=('X'*(2*1024**2+1) if mode=='large' else 'Corrected observed note') if mid=='m_000002' else None)
            other=[d for key,d in self.docs.items() if key!=('results','A')]
            if mode=='ambiguous':other.append(self.docs[('results','A')])
            self.binding([doc,*other])
        build=self.build('A',g,g);self.publish({'A':build},'archive_source_'+mode+'_published')
        return {'generation':g,'build':build,'documentId':doc['id']}

    def invalid_native_count(self):
        mid='m_000001';m=self.match_rows[mid];doc=self.docs[('goals','A')]
        record=self._row('ingest.source_records','document_id=%s AND locator=%s',(doc['id'],'/matches/'+mid))
        with self._generation('archive_invalid_native_event_count'):
            self._insert('ingest.match_coverage',match_id=m['id'],match_revision_id=m['revision_id'],source_id=doc['source_id'],source_record_id=record['id'],document_id=doc['id'],feature_code='events',variant_key='archive:invalid-count',is_canonical=False,coverage_state='available',collection_state='present',observed_row_count=2,checked_at=NOW)

# Reuse of the exact qualified owned-setup function needs its fixture export name.
CompetitionFixture=ArchiveFixture
