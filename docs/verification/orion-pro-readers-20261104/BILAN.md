# Lecteurs SQL Pro — bilan du lot

Le backend possède quatre lecteurs SQL figés : manifeste, page de matchs, résumé et tirs à la demande. Le flag `STATARENA_PRO_API` reste désactivé par défaut. Aucun lecteur de ce lot n'est activé en production et aucune donnée réelle n'a été publiée dans le nouveau schéma.

La preuve finale [23/23, 56 requêtes HTTP](runs/20261104T203537303447Z-source-profile-native-metres-green/result.json) utilise PostgreSQL 18.6 et le rôle `statarena_runtime` réellement en lecture seule. Elle couvre les anciennes représentations après correction A/B, l'indépendance de C, les curseurs, HEAD/304, les profils sélectionnés à la génération du catalogue, les valeurs natives et les refus d'écriture. Les contre-exemples RED sont conservés ; la revue parent a notamment corrigé les contextes de profils, la chaîne événement vide et l'unité des coordonnées.

| Observation locale finale | Corps JSON | SQL | Lectures lourdes |
|---|---:|---:|---:|
| Manifeste | 2 361 octets | 1 | 0 |
| Page de deux matchs | 1 250 octets | 2 | 0 |
| Résumé | 682 octets | 3 | 0 |
| Tirs demandés explicitement | 665 octets | 3 | 1 |
| HEAD/304 manifeste ou liste | 0 octet | 1 | 0 |
| HEAD/304 résumé ou tirs | 0 octet | 2 | 0 |

Ces mesures portent sur les composants d'un jeu synthétique. Le résumé n'exécute aucune requête de tirs ; celle-ci apparaît seulement à la demande. Le premier essai de l'ancien routeur renvoyait des erreurs faute de projections historiques dans le jeu : il ne constitue donc pas un avant comparable. Aucun pourcentage de gain de latence, p95, économie RDS/S3 ou coût de calcul n'est établi pour ce lot. [Mesures, méthode et commande de reproduction](runs/20261104T203537303447Z-source-profile-native-metres-green/measurements.json).

Reproduction complète, sans accès cloud :

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_readers_local.py --pg-bin /tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin --label review
```

Restent ouverts : import complet et fidèle, publisher réel, autres familles et routes métier, intégration React, parcours desktop/mobile, déploiement et comparaison représentative sur RDS. La représentation v1 projette uniquement les coordonnées `acting_ltr` démontrées en mètres ; les autres repères restent explicitement non projetés avec leurs coordonnées sources typées.

Commit proposé : `feat: serve frozen Pro match summaries and lazy details`.
