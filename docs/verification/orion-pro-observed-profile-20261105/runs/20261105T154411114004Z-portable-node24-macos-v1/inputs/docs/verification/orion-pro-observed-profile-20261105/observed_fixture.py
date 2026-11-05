"""Retained physical-profile workflow authored before the corrective reader edit."""
from pathlib import Path
import hashlib
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'docs/verification/orion-pro-appearances-20261105'))
from appearance_fixture import AppearanceFixture,png
from fixtures import NOW,hashed


class ObservedProfileFixture(AppearanceFixture):
    def replace_observed_profile(self):
        old=self.observed_profiles[0]
        media=self.media['B']
        self.new_asset=self._insert('ingest.media_assets',storage_bucket='source-free-no-cloud',
            storage_key=media['key'],content_sha256=media['sha256'],content_type='image/png',
            source_url='https://provenance.fixture.invalid/replacement.png',author='Synthetic captured-profile E2E',
            license_code='CC0',retrieved_at=NOW)
        with self._generation('captured_profile_replacement') as g:
            replacement=self._replace('football.player_profile_versions',old,
                display_name='CURRENT renamed profile must not leak',external_profile_version_id='current_replacement_profile_01',
                profile_content_sha256=hashed('captured-profile replacement B'),image_asset_id=self.new_asset['id'])
            self.replacement_generation=g
        old_data_build=self.build('E',self.appearance_g,g)
        self.publish({'E':old_data_build},'captured_profile_oldDG_newCG')
        new_data_build=self.build('E',g,g)
        self.publish({'E':new_data_build},'captured_profile_newDG_newCG')
        self.profile_replacement={'old':old,'replacement':replacement,'generation':g,
            'oldDataBuild':old_data_build,'newDataBuild':new_data_build}
        return self.profile_replacement

    def membership_proof(self):
        old=self.observed_profiles[0];g=self.replacement_generation
        profiles=self.conn.execute('''SELECT id,player_id,profile_context,display_name,external_profile_version_id,
            image_asset_id,recorded_from_gen,recorded_to_gen,is_canonical,is_deleted
            FROM football.player_profile_versions WHERE player_id=%s AND profile_context=%s ORDER BY id''',
            (old['player_id'],old['profile_context'])).fetchall()
        selected=self.conn.execute('''SELECT count(*),count(DISTINCT profile_version_id),min(profile_version_id),max(profile_version_id)
            FROM football.match_players WHERE player_id=%s AND is_canonical AND NOT is_deleted
            AND ingest.selected_at(%s,recorded_from_gen,recorded_to_gen)''',(old['player_id'],g)).fetchone()
        current=self.conn.execute('''SELECT id FROM football.player_profile_versions WHERE player_id=%s AND profile_context=%s
            AND is_canonical AND NOT is_deleted AND ingest.selected_at(%s,recorded_from_gen,recorded_to_gen)''',
            (old['player_id'],old['profile_context'],g)).fetchall()
        sealed=self.conn.execute('SELECT generation,status FROM ingest.dataset_snapshots WHERE generation=%s',(g,)).fetchall()
        triggers=self.conn.execute('''SELECT c.relname,t.tgname,t.tgenabled FROM pg_trigger t
            JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='football' AND c.relname IN ('match_players','player_profile_versions')
            AND t.tgname='pro_typed_guard' ORDER BY c.relname''').fetchall()
        assert len(profiles)==2 and profiles[0][0]==old['id'] and profiles[0][7]==g
        assert profiles[0][3:6]==(old['display_name'],old['external_profile_version_id'],old['image_asset_id'])
        assert selected==(6,1,old['id'],old['id'])
        assert current==[(self.profile_replacement['replacement']['id'],)] and sealed==[(g,'sealed')]
        assert len(triggers)==2 and all(row[2]=='O' for row in triggers)
        return {'profiles':profiles,'selectedParticipants':selected,'selectedCurrentProfile':current,
            'sealedGeneration':sealed,'enabledTypedTriggers':triggers,
            'constraintPolicy':'Native constraints/triggers unchanged; no replica-role/disable/override'}

    def change_unused_replacement_media(self):
        blob=png((128,0,128,255));digest=hashlib.sha256(blob).hexdigest()
        key='raw/media/'+digest+'.png'
        (self.evidence/'inputs/media/C.png').write_bytes(blob)
        self.conn.execute('UPDATE ingest.media_assets SET storage_key=%s,content_sha256=%s WHERE id=%s',
            (key,digest,self.new_asset['id']))
        return {'assetId':self.new_asset['id'],'key':key,'sha256':digest,'bytes':len(blob),'input':'inputs/media/C.png'}
