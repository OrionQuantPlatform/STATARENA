"""Source-free PNG/typed-media inputs, specified before the batch implementation."""
from pathlib import Path
import hashlib
import struct
import sys
import zlib

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'docs/verification/orion-pro-entities-20261105'),str(ROOT/'docs/verification/orion-pro-pilot-20261104')]
from entity_fixture import EntityFixture
from fixtures import NOW, hashed


def png(pixel):
    def chunk(kind,value):return struct.pack('>I',len(value))+kind+value+struct.pack('>I',zlib.crc32(kind+value)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00'+bytes(pixel)))+chunk(b'IEND',b'')


class MediaFixture(EntityFixture):
    def link_media(self):
        self.media={}
        folder=self.evidence/'inputs/media';folder.mkdir(parents=True,exist_ok=True)
        for key,pixel in [('A',(255,0,0,255)),('B',(0,0,255,255))]:
            blob=png(pixel);sha=hashlib.sha256(blob).hexdigest();path=folder/(key+'.png');path.write_bytes(blob)
            self.media[key]={'sha256':sha,'key':'raw/media/'+sha+'.png','path':str(path.relative_to(self.evidence)),
                             'bytes':len(blob),'contentType':'image/png','sourceUrl':'https://provenance.fixture.invalid/'+key+'.png'}
        a=self.media['A']
        with self.conn.transaction():
            asset=self._insert('ingest.media_assets',storage_bucket='source-free-no-cloud',storage_key=a['key'],
                content_sha256=a['sha256'],source_url=a['sourceUrl'],content_type='image/png',author='Synthetic E2E fixture',
                license_code='CC0',attribution_url='https://provenance.fixture.invalid/credits',retrieved_at=NOW)
        self.asset_id=asset['id']
        with self._generation('entity_linked_media') as g:
            self.player_profiles[0]=self._replace('football.player_profile_versions',self.player_profiles[0],image_asset_id=asset['id'],
                profile_content_sha256=hashed('entity linked media'),external_profile_version_id='entity-linked-media')
            self.team_profiles[0]=self._replace('football.team_profile_versions',self.team_profiles[0],image_asset_id=asset['id'])
            self.competition=self._replace('football.competitions',self.competition,image_asset_id=asset['id'])
        builds={key:self.build(key,g,g) for key in 'ABCD'}
        self.publish(builds,'entity_linked_media_publication')
        return {'assetId':asset['id'],'media':self.media,'generation':g,'builds':builds,
                'provenance':{'bucket':'source-free-no-cloud','author':'Synthetic E2E fixture','license':'CC0','retrievedAt':str(NOW)}}

    def change_asset(self,key,**extra):
        item=self.media[key]
        values={'storage_key':item['key'],'content_sha256':item['sha256'],'content_type':item['contentType'],'source_url':item['sourceUrl'],**extra}
        self.conn.execute('UPDATE ingest.media_assets SET '+','.join(column+'=%s' for column in values)+' WHERE id=%s',(*values.values(),self.asset_id))
        return {'assetId':self.asset_id,**values}
