"""D23, written before loosening only the over-constrained scalar pointer."""
from __future__ import annotations

import hashlib


def D23(c):
    """A different source document/order reuses exact scalars; foreign side refuses."""
    old=c.fx._row('ingest.match_coverage',"feature_code='stats' AND recorded_to_gen IS NULL")
    assert old and old['contract_version']=='match-native-v1'
    refs=c.ingest.execute('SELECT home_metric_revision_id,away_metric_revision_id FROM football.match_team_stat_items WHERE recorded_from_gen=%s ORDER BY source_record_id',(old['recorded_from_gen'],)).fetchall()
    assert len(refs)==2 and len(set(refs))==2
    count=c.runtime.execute('SELECT count(*) FROM football.team_match_metric_values').fetchone()[0]
    source=old['source_id'];dataset=c.ingest.execute('SELECT id FROM ingest.source_datasets WHERE source_id=%s ORDER BY id LIMIT 1',(source,)).fetchone()[0]

    def correction(foreign=False):
        g=c.fx._begin('owned_layout_foreign_side' if foreign else 'owned_layout_reordered_reuse')
        previous=c.fx.g;c.fx.g=g
        try:
            doc,_=c.fx._record(source,dataset,f'native107-layout-reuse-{g}')
            root=c.fx.record('layout_root',doc,'/data',external='m_000001')
            assert doc['id']!=old['document_id']
            profiles={}
            for i,side in enumerate(('home','away')):
                record=c.fx.record(side+'_layout_record',doc,'/data/'+side+'_team',external='t_'+str(i+1).zfill(6))
                profiles[side]=c.fx.profile(side+'_layout_profile',record,c.fx.ids['teams'][i])['id']
            c.ingest.execute("UPDATE ingest.match_coverage SET recorded_to_gen=%s WHERE match_id=%s AND source_id=%s AND feature_code='stats' AND variant_key=%s AND recorded_from_gen=%s",(g,old['match_id'],source,old['variant_key'],old['recorded_from_gen']))
            args={k:v for k,v in old.items() if k not in ['recorded_to_gen','recorded_from_gen']}
            args.update(document_id=doc['id'],source_record_id=root['id'],source_home_team_profile_version_id=profiles['home'],source_away_team_profile_version_id=profiles['away'])
            cov=c.fx.put('ingest.match_coverage','layout_coverage',**args)
            key={k:cov[k] for k in ('match_id','source_id','feature_code','variant_key','recorded_from_gen')}
            for i in range(2):
                period=c.fx.record('layout_period'+str(i),doc,'/data/periods/'+str(i),i)
                c.fx.put('football.match_team_stat_periods','layout_period_row'+str(i),**key,source_record_id=period['id'],
                    source_period_label='first_half',source_period_label_state='value',groups_state='empty' if i else 'present',groups_count=0 if i else 1)
                if i:continue
                group=c.fx.record('layout_group',doc,period['locator']+'/groups/0',0)
                c.fx.put('football.match_team_stat_groups','layout_group_row',**key,source_record_id=group['id'],period_source_record_id=period['id'],
                    group_name='Corrected synthetic layout',group_name_state='value',items_state='present',items_count=2)
                for ordinal,(home,away) in enumerate(reversed(refs)):
                    item=c.fx.record('layout_item'+str(ordinal),doc,group['locator']+'/items/'+str(ordinal),ordinal)
                    c.fx.put('football.match_team_stat_items','layout_item_row'+str(ordinal),**key,source_record_id=item['id'],group_source_record_id=group['id'],
                        raw_key='repeated',raw_key_state='value',title='',title_state='value',format_type=None,format_type_state='null',
                        home_metric_revision_id=away if foreign and ordinal==0 else home,away_metric_revision_id=away)
            c.ingest.execute('SELECT ingest.seal_generation(%s,%s)',(g,hashlib.sha256(f'owned-layout-reuse:{g}'.encode()).hexdigest()))
            c.ingest.execute('SET CONSTRAINTS ALL IMMEDIATE')
            return g,doc['id']
        finally:c.fx.g=previous

    refused=c.expect_sqlstate('layout_reuse_wrong_side',lambda:correction(True),{'23514'},'native107: stats scalar side',c.ingest)
    with c.ingest.transaction():g,document=correction()
    after=c.runtime.execute('SELECT i.home_metric_revision_id,i.away_metric_revision_id FROM football.match_team_stat_items i JOIN ingest.source_records r ON r.id=i.source_record_id WHERE i.recorded_from_gen=%s ORDER BY r.ordinal',(g,)).fetchall()
    assert after==list(reversed(refs))
    assert c.runtime.execute('SELECT count(*) FROM football.team_match_metric_values').fetchone()[0]==count
    assert c.runtime.execute('SELECT count(*) FROM football.team_match_metric_values WHERE recorded_from_gen=%s',(g,)).fetchone()==(0,)
    retained=c.runtime.execute('SELECT count(*) FROM football.match_team_stat_items WHERE recorded_from_gen=%s',(old['recorded_from_gen'],)).fetchone()[0]
    assert retained==2
    return {'previousDocument':old['document_id'],'newDocument':document,'generation':g,'reversedPhysicalRefs':after,
            'scalarRowsBeforeAfter':[count,count],'newScalars':0,'retainedOldLayoutItems':retained,'wrongSideRefusal':refused}
