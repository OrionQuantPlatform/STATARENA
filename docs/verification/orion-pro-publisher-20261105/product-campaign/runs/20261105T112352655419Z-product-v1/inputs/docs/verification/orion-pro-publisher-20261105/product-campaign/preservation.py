"""Read-only verification of predecessor artifacts; never edits their bytes."""
import hashlib
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent
PARENT=BASE.parent
MANIFESTS={
    PARENT/'THIRD_PRECODE_CHECKSUMS.json':'7f0be897e84b6bc244e037dffc9de7012ddbbbfeae36cdee13b8802eb0205f47',
    PARENT/'static-schema-review/STATIC_CHECKSUMS.json':'20fd48fc3da68e03a40ca3f1d210f1946979aa04724a35deb05eb0f18ffbaa63',
}

def preserved():
    result=[]
    for manifest,want in MANIFESTS.items():
        assert hashlib.sha256(manifest.read_bytes()).hexdigest()==want,'Preserved manifest changed'
        entries=json.loads(manifest.read_text())['sha256']
        bad=[name for name,digest in entries.items() if hashlib.sha256((manifest.parent/name).read_bytes()).hexdigest()!=digest]
        assert not bad,'Preserved artifact changed: '+str(bad)
        result.append({'manifest':str(manifest.relative_to(PARENT)),'sha256':want,'entries':len(entries),'unchanged':True})
    return result
