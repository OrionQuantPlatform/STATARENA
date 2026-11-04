# Prototype local abandonné après correction utilisateur

Ces sources sont conservées uniquement comme preuves des essais E2E déjà exécutés. Elles ne font plus partie du pilote actif et ne doivent pas être appliquées au RDS. Aucune migration distante n’a été exécutée. Le dernier essai local est terminal et son PostgreSQL propriétaire a été arrêté.

Pour inspecter les essais, lire les répertoires `before`, `first-implementation`, `after-bootstrap-order` et `after-fixture-contract`, leur `result.json`, leurs logs et les sources archivées ci-dessous. L’état du schéma de référence de ces essais est celui du commit `780a113da3`. Leur protocole exact est conservé dans `PROTOCOL.original.md` ; `../PROTOCOL.md` décrit désormais uniquement le statut supersédé et les portes du prochain pilote.

Reproduction historique uniquement dans un dossier temporaire isolé : extraire ce commit avec `git archive`, superposer `source/` et le reçu `approval-initial.json` à son ancien emplacement `docs/verification/orion-schema-pilot-20261104/approval.json`, puis lancer `PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_schema_postgres.py`. Le moteur local utilisé était `/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin/postgres`18.6. Ces vérifications n’ont pas atteint l’acceptation complète et ne prouvent pas une migration AWS.

Commit suggéré : `docs: remove separate history tables from the Orion plan`.
