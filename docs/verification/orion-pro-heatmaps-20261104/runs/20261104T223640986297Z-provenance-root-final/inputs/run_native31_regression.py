"""Run the unchanged native31 E2E; relocate evidence only, never its fixtures."""
import hashlib,json,shutil,sys,types
from pathlib import Path
sys.dont_write_bytecode=True
REPO=Path(__file__).resolve().parents[3]
SOURCE=REPO/'tests/orion_pro_native_contracts_local.py'
ORIGINAL=REPO/'docs/verification/orion-pro-native-contracts-20261104'
OUTPUT=Path(__file__).resolve().parent/'native31-regression'
OUTPUT.mkdir(exist_ok=True)
for name in ['PLAN.md','PROTOCOL.md','FIELD_MATRIX.json']:
    shutil.copy2(ORIGINAL/name,OUTPUT/name)
module=types.ModuleType('unchanged_native31_regression');module.__file__=str(SOURCE)
exec(compile(SOURCE.read_text(),str(SOURCE),'exec'),module.__dict__)
module.DOC=OUTPUT
code=module.main()
(OUTPUT/'redirect.json').write_text(json.dumps({'unchangedTest':str(SOURCE),'testSha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'onlyOverride':'DOC evidence output root','sourceFixturesAndExpectedCountsUnchanged':True},indent=2)+'\n')
raise SystemExit(code)
