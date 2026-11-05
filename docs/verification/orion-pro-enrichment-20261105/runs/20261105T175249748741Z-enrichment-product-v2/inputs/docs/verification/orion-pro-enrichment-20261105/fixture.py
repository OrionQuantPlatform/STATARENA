"""Synthetic typed enrichment observations, specified before the reader."""
from __future__ import annotations
from datetime import date
from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[3]
source=ROOT/'docs/verification/orion-pro-competitions-20261105/fixture.py'
spec=importlib.util.spec_from_file_location('enrichment_competition_base',source)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
NOW=base.NOW
ALIAS='https://upload.wikimedia.org/wikipedia/commons/a/ab/Fixture_portrait.jpg'
CREDIT='https://commons.wikimedia.org/wiki/File:Fixture_portrait.jpg'
HONOUR_URL='https://en.wikipedia.org/w/index.php?title=Fixture_player&oldid=1234567890#Honours'
LINK='0000012345'
REP='summary-v1-shots-v1'

class EnrichmentFixture(base.CompetitionFixture):
    def _begin(self,label,conn=None):
        self.counter+=1
        return (conn or self.conn).execute('SELECT ingest.begin_generation(%s,%s,%s,%s)',(f'enrichment:{label}:{self.counter}','pilot_v1','pilot_priority_v1',NOW)).fetchone()[0]

    def source_doc(self,role,key,contract,url):
        s=self._row('ingest.sources','code=%s',(role,))
        if not s:s=self._insert('ingest.sources',code=role,name={'wikidata':'Wikidata','uefa':'UEFA','wikipedia':'Wikipedia'}[role])
        d=self._insert('ingest.source_datasets',source_id=s['id'],dataset_key=key,contract_version=contract,source_url=url,license_code='fixture-source-license')
        return self._insert('ingest.source_documents',dataset_id=d['id'],source_id=s['id'],retrieved_at=NOW,
            content_sha256=base.hashed(['enrichment-document',key]),request_fingerprint=base.hashed(['enrichment-request',key]),byte_length=17,source_url=url)

    def record(self,doc,locator,external,kind='enrichment_fact_v1'):
        return self._insert('ingest.source_records',source_id=doc['source_id'],document_id=doc['id'],locator_kind='json_pointer',locator=locator,external_key=external,record_kind=kind)

    def _fact(self,doc,locator,external):
        r=self.record(doc,locator,external);return {'source_id':doc['source_id'],'source_record_id':r['id']}

    def media(self,alias=ALIAS,content='a',mime='image/jpeg',author='Fixture Photographer'):
        sha=content*64
        return self._insert('ingest.media_assets',storage_bucket='owned-fixture',storage_key='raw/neon/assets/'+sha+'.jpg',content_sha256=sha,content_type=mime,source_url=alias,
            author=author,license_code='CC BY-SA 4.0',attribution_url=CREDIT,legacy_asset_url=alias,retrieved_at=NOW)

    def bind_docs(self,docs):
        sid=self.conn.execute('SELECT id FROM ingest.dataset_snapshots WHERE generation=%s',(self.g,)).fetchone()[0]
        for doc in docs:self._insert('ingest.dataset_snapshot_documents',snapshot_id=sid,document_id=doc['id'])

    def team_wiki(self,team,qid,name,year,locator):
        e=self._fact(self.docs['wiki'],locator,qid)
        self._insert('football.team_source_ids',team_id=team['id'],external_id=qid,first_seen_at=NOW,**e)
        return self._insert('football.team_profile_versions',team_id=team['id'],observed_at=NOW,display_name=name,country_code_source='FRA',country_id=self.country['id'],country_revision_id=self.country['revision_id'],founded_year=year,team_type='club',profile_context='wikidata_enrichment_v1',variant_key='source:exact',**e)

    def team_uefa(self,team,number,locator):
        e=self._fact(self.docs['uefa'],locator,number)
        return self._insert('football.team_source_ids',team_id=team['id'],external_id=number,first_seen_at=NOW,**e)

    def coach(self,qid,name,*,asset=None,birthday=None):
        e=self._fact(self.docs['wiki'],'/coaches/'+qid,qid)
        c=self._insert('football.coaches',display_name=name,birth_date=birthday,image_asset_id=asset['id'] if asset else None,**e)
        self._insert('football.coach_source_ids',coach_id=c['id'],coach_revision_id=c['revision_id'],external_id=qid,first_seen_at=NOW,**e)
        return c

    def tenure(self,team,coach,label,start,end,role='head_coach'):
        return self._insert('football.team_coach_tenures',team_id=team['id'],coach_id=coach['id'],coach_revision_id=coach['revision_id'],role=role,
            valid_from=start,valid_to=end,date_precision='day',observed_at=NOW,**self._fact(self.docs['wiki'],'/tenures/'+label,label))

    def venue(self,qid,name,cap,lat,lon,year,*,document='wiki'):
        e=self._fact(self.docs[document],'/venues/'+qid,qid)
        v=self._insert('football.venues',name=name,capacity=cap,capacity_as_of=date(2024,2,29) if cap is not None else None,latitude=lat,longitude=lon,opened_year=year,**e)
        self._insert('football.venue_source_ids',venue_id=v['id'],venue_revision_id=v['revision_id'],external_id=qid,first_seen_at=NOW,**e)
        return v

    def prepare_enrichment(self):
        with self._generation('enrichment_typed_raw') as g:
            self.enrichment_gen=g
            self.docs={'wiki':self.source_doc('wikidata','fixture-wiki','orion-enrichment-v1','https://www.wikidata.org/entity/Q101'),
                       'venue':self.source_doc('wikidata','fixture-venue','orion-enrichment-v1','https://www.wikidata.org/wiki/Q301'),
                       'uefa':self.source_doc('uefa','fixture-uefa','orion-enrichment-v1','https://www.uefa.com/'),
                       'honours':self.source_doc('wikipedia','player-honours:p_000001','orion-player-honours-v1',HONOUR_URL),
                       'unbound':self.source_doc('wikipedia','player-honours:p_000002','orion-player-honours-v1','https://en.wikipedia.org/wiki/Unbound_fixture_player'),
                       'invalid':self.source_doc('wikipedia','player-honours:p_000003','orion-player-honours-v1','https://en.wikipedia.org/w/index.php?title=Fixture_player&oldid=1234567890&next=https%3A%2F%2Foutside.invalid#Honours')}
            self.bind_docs([d for k,d in self.docs.items() if k!='unbound'])
            self.photo=self.media();bad=self.media(alias='https://upload.wikimedia.org/wikipedia/commons/a/ab/Bad.jpg',content='b',mime='application/json')
            t0,t1,t2=self.ids['teams'][:3]
            self.country=self._insert('football.countries',name='France',iso2='FR',iso3='FRA',**self._fact(self.docs['wiki'],'/countries/Q142','Q142'))
            self.wiki=self.team_wiki(t0,'Q101','Étoile Fixture',1899,'/teams/Q101')
            self.team_wiki(t1,'Q102','Unknown Tenure Club',1901,'/teams/Q102')
            self.team_wiki(t2,'Q104','Factual Fixture Club',1921,'/teams/Q104')
            self.team_uefa(t0,LINK,'/clubs/'+LINK);self.team_uefa(t1,'12346','/clubs/12346')
            self._insert('football.team_profile_versions',team_id=t0['id'],observed_at=NOW,display_name='UEFA Fixture Club',country_code_source='FRA',team_type='club',profile_context='uefa_enrichment_v1',variant_key='source:exact',**self._fact(self.docs['uefa'],'/clubs/profile/'+LINK,LINK))
            self._insert('football.team_aliases',team_id=t0['id'],alias='Club de l’Étoile',language_code='fr',**self._fact(self.docs['wiki'],'/aliases/Q101','Q101'))
            self.coach_row=self.coach('Q201','Alex Fixture',asset=self.photo,birthday=date(1975,6,1))
            assistant=self.coach('Q202','Assistant Fixture',birthday=date(1980,1,2))
            expired=self.coach('Q203','Expired Fixture',birthday=date(1960,1,1))
            self.coach('Q204','Same Coach',asset=self.photo,birthday=date(1970,1,1))
            self.coach('Q205','Same Coach',birthday=date(1981,1,1))
            self.coach('Q206','Bad Media Coach',asset=bad)
            self.tenure(t0,self.coach_row,'t0-active',date(2026,10,1),date(2026,11,5))
            self.tenure(t0,expired,'t0-expired',date(2026,1,1),date(2026,9,30))
            self.tenure(t0,assistant,'t0-assistant',date(2026,10,1),date(2026,12,31),role='assistant')
            self.tenure(t1,assistant,'t1-unproven',date(2026,10,1),None)
            self.venue_row=self.venue('Q301','Fixture Stadium',0,0.0,0.0,1910,document='venue')
            self.venue('Q302','Partial Fixture Stadium',None,46.4,None,None)
            # These venues have no official team-to-home-venue link.
            player=self.conn.execute('SELECT id FROM football.players ORDER BY id LIMIT 1').fetchone()[0]
            other=self._insert('football.players',display_name='Unbound Player')
            self._insert('ingest.public_aliases',route_kind='player',public_key='p_000002',player_id=other['id'])
            invalid=self._insert('football.players',display_name='Invalid attribution player')
            self._insert('ingest.public_aliases',route_kind='player',public_key='p_000003',player_id=invalid['id'])
            self.record(self.docs['honours'],'/identity','p_000001','honours_identity_v1')
            self.record(self.docs['unbound'],'/identity','p_000002','honours_identity_v1')
            self.record(self.docs['invalid'],'/identity','p_000003','honours_identity_v1')
            self._insert('football.team_profile_versions',team_id=t0['id'],observed_at=NOW,display_name='Étoile Fixture',profile_context='honours_display_v1',variant_key='source:exact',**self._fact(self.docs['honours'],'/teams/1','t_000001'))
            hteam=self._insert('football.honour_definitions',code='fixture-team-title',name='UEFA Champions League',honour_type='team')
            hind=self._insert('football.honour_definitions',code='fixture-person-title',name="Ballon d'Or",honour_type='individual')
            def honour(doc,actor,definition,edi,label,outcome,team=None):
                self._insert('football.player_honours',player_id=actor,honour_id=definition['id'],honour_revision_id=definition['revision_id'],team_id=team,
                    edition_key=edi,season_label=label,outcome=outcome,**self._fact(doc,'/honours/'+edi,edi))
            honour(self.docs['honours'],player,hteam,'team-2023','2023/2024','winner',t0['id'])
            honour(self.docs['honours'],player,hteam,'team-2024','2024/2025','winner',t0['id'])
            honour(self.docs['honours'],player,hteam,'opaque-edition',None,'winner',t0['id'])
            honour(self.docs['honours'],player,hteam,'team-2022','2022/2023','runner_up',t0['id'])
            honour(self.docs['honours'],player,hind,'person-2025','2025','winner')
            honour(self.docs['unbound'],other['id'],hind,'unbound-2025','2025','winner')
            honour(self.docs['invalid'],invalid['id'],hind,'invalid-2025','2025','winner')
        return {'generation':g,'documents':{k:d['id'] for k,d in self.docs.items()},'unbound':self.docs['unbound']['id']}

    def publish_catalogue(self,g):
        build=self.build('A',g,g);self.publish({'A':build},'enrichment_catalogue_published')
        sid=self.conn.execute('SELECT id FROM ingest.dataset_snapshots WHERE generation=%s',(g,)).fetchone()[0]
        self.conn.execute('INSERT INTO analytics.catalog_publication(singleton,catalog_snapshot_id,representation_version,published_at) VALUES(true,%s,%s,%s) ON CONFLICT(singleton) DO UPDATE SET catalog_snapshot_id=excluded.catalog_snapshot_id,representation_version=excluded.representation_version,published_at=excluded.published_at',(sid,REP,NOW))
        return {'build':build,'snapshot':sid,'generation':g}

    def correction(self,mode='capacity'):
        with self._generation('enrichment_'+mode) as g:
            self.bind_docs([d for k,d in self.docs.items() if k!='unbound'])
            if mode=='capacity':self.venue_row=self._replace('football.venues',self.venue_row,capacity=50000,name='Corrected Fixture Stadium')
            elif mode=='ambiguous':
                other=self.ids['teams'][3];self.team_wiki(other,'Q103','Étoile Fixture',1911,'/teams/Q103')
                self.team_uefa(self.ids['teams'][0],'12347','/clubs/12347')
                coach=self.coach('Q207','Second Active Coach')
                self.tenure(self.ids['teams'][1],coach,'t1-second',date(2026,10,2),date(2026,12,31))
            else:raise AssertionError(mode)
        return self.publish_catalogue(g)

    def correct_photo_metadata(self):
        return self.conn.execute('UPDATE ingest.media_assets SET content_sha256=%s,storage_key=%s,author=%s WHERE id=%s RETURNING id',('c'*64,'raw/neon/assets/'+'c'*64+'.jpg','Corrected Fixture Credit',self.photo['id'])).fetchone()[0]

    def add_ambiguous_photo_alias(self):
        return self.media(content='d')['id']

CompetitionFixture=EnrichmentFixture
