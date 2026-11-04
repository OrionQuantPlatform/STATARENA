# Bilan chiffré du lot disponibilité — 4 novembre 2026

Le correctif SQL est déployé sur AWS et l’interface courante est rétablie sur
Vercel. Elle utilise temporairement les données Neon déjà enregistrées ; ce lot
ne termine pas la migration métier vers RDS.

| Mesure comparable | Avant | Après | Conclusion |
|---|---:|---:|---|
| SQL dense, même snapshot, 100 matchs et 4 788 participations | 2 605,772 ms | 2 019,623 ms | **−22,49 %**, une paire ordonnée, pas un p95 |
| Requêtes SQL lourdes par GET | 1 | 1 | Nombre inchangé ; agrégation interne regroupée |
| Résultat SQL canonique | 5 821 148 octets | 5 821 148 octets | SHA et valeurs identiques |
| Health/manifeste du domaine public | 503 / 503 | 200 / 200 | Disponibilité rétablie, 6 saisons et 230 partitions |
| Archive 2020/21 via la nouvelle API | 413 malgré une source présente | 200, 238 411 octets gzip | JSON exact de 2 677 442 octets ; plafond générique conservé |
| Stockage récupéré dans RDS/S3 | 0 | 0 | Aucune purge ou économie de stockage annoncée |

Les trois GET réels du nouveau backend AWS ont pris **4 008,62 / 3 575,56 /
3 034,98 ms**, pour les mêmes 100 matchs et 4 788 participations, avec
431 386 octets encodés / 1 973 314 décodés. Hash, ETag et génération identiques.
Tous étaient en `no-store`, avec un MISS CloudFront. HEAD 200 : 379,54 ms ;
304 : 362,14 ms. L’ancien déploiement avait aussi réussi une fois en
5 938,97 ms après un timeout : ces échantillons HTTP non appariés ne permettent
pas de calculer un gain causal ou une fiabilité. Aucun coût monétaire mesuré.

Vercel a construit la source exacte de `main`, `f65036cdb9`, en 23 secondes.
Les **12 parcours navigateur réels** sont passés sur cette URL immuable avant
promotion du même build. Les deux alias vérifiés pointent sur ce build et les
deux contrôles desktop/mobile du domaine canonique passent. La recherche de
logs error/fatal n’a trouvé aucun enregistrement dans sa fenêtre de dix minutes ;
elle ne remplace pas une surveillance continue.

Les contrôles locaux ont rapproché six partitions de Ligue 1, 1 985 fixtures
et les 195 tables de 65 compétitions complémentaires : 264 lectures externes
bornées, 10 463 575 octets et une concurrence maximale de quatre. Ils ne prouvent
pas chaque ligne des 230 partitions ni chaque joueur ou média. Les 404 déjà
présents à la source sont conservés et listés dans RESULTS.md. Le CI du correctif
SQL est passé ; celui du frontend restait en file au dernier relevé.

Preuves, commandes, échecs conservés et limites : [SQL](DENSE_QUERY_RESULTS.md),
[interface](RESULTS.md), [navigateur réel](vercel-browser-20261104T173656163590Z.json),
[alias et HTTP](vercel-production-readback.json), [desktop/mobile](canonical-browser.json).

La refonte Pro est une proposition distincte : 103 tables, 1 791 colonnes,
450 FK, sans tables sœurs d’historique. Aucun gain d’exécution ou de stockage
n’en découle avant le pilote mesuré. Aucun nouveau schéma métier n’a été
appliqué sur RDS et aucune source n’a été supprimée.

Commit suggéré : `docs: record current UI recovery and measured results`.
