# Qualification Linux du mode SQL seul

Le [run GitHub41955410288](https://github.com/OrionQuantPlatform/STATARENA/actions/runs/41955410288), sur le commit1b0b71f5cd14329c4c28c86058bf78ef8025311e, réussit ses trois jobs. Le nouveau scénario CLI/SSM local passe **10/10** sous Linux. Les14suites Pro préexistantes conservent **203contrôles réussis**,0échec et4contrôles réels volontairement non exécutés dans cette CI.

[Résumé et métadonnées](ci/run-41955410288.json), [log du job incluant les dix cas](ci/verify-job-127009027024.log.json), [log Pro](ci/pro-job-127009027063.log.json). Les logs sont ceux décodés par GitHub, conservés intégralement en chaînes JSON. Les métadonnées des trois archives sont relevées ; elles n'ont pas été téléchargées pour cette lecture.

La fixture SSM est locale au runner : aucun credential AWS réel, OIDC, transfert métier ou collecte programmée n'est exercé par ces dix cas. Cette validation confirme la portabilité du chemin CLI et des refus ; elle ne qualifie pas la connectivité RDS d'un collecteur en production. Le [bilan local](BILAN.md) reste l'état historique avant push.

Commit suggéré : `test: retain passing Linux worker and policy CI evidence`.
