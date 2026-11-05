# Compétitions, coupes et classements — qualification locale V3

Les huit formes sont implémentées dans `dashboard/backend/services/orion-pro-competitions.js` (`c680e9dd1fc5549d2a5470d0bb90d255d51c19d7c3632d97e64da00c3a0b47c2`). Le module sert les DTO de standings, archives de coupes, Nations, index, tableaux, snapshots et journées à partir du modèle103, des publications READY et de leurs DG/CG. Les huit routes ne sont pas câblées par ce lot : le mode d’essai appelle le module sur un vrai serveur HTTP Node24, puis l’app réelle pour les contrôles V1. ROOT possède le câblage et la régression de l’app entière.

La campagne locale `runs/20261105T163938561629Z-competitions-product-v3/result.json` (`6f90f56fbf7d0fd9e7de929605c3592e03e9fe59b4bb1140c84ffe69a4f05e4c`) passe les26 scénarios en5.064s : 843 requêtes SQL réservées et exactement843 observées dans le journal PostgreSQL (651 propriétaire,187 API,4 initialisation,1 refus runtime),96 requêtes HTTP. Le runtime ordinaire était TLS, lecture seule, avec8s SQL,1s verrou et5s idle. Les huit calibrations de réseau externe sont bloquées, puis zéro tentative externe opérationnelle. Aucun appel source, AWS, Neon ou RDS.

| GET sur le fixture | Octets | SQL |
| --- | ---: | ---: |
| standings | 971 | 3 |
| open-cups | 800 | 3 |
| openligadb | 1182 | 3 |
| nations-results | 499 | 3 |
| cup-index | 698 | 2 |
| cup-table | 361 | 3 |
| cup-snapshot native | 1570 | 3 |
| matchdays | 173 | 3 |

Les HEAD et304 des huit routes positives ont chacun deux requêtes de métadonnées et aucun corps. Les réponses d’erreur sont sans cache, y compris la cohorte standings ambiguë et un alias match disparu sous `If-None-Match:*`. Le résultat conserve55×200,13×503,12×304,10×400,3×404,1×405,1×501 hors périmètre et1×413. Ces mesures concernent un petit fixture local ; elles ne sont pas des mesures de production ni une comparaison de débit avec les anciennes projections.

Les fonctions consommateurs inchangées reçoivent les vrais corps HTTP. Elles retrouvent deux manches, un total1–1 et des tirs au but4–3 dans l’orientation du premier match, deux tours natifs, deux groupes de journées, une cohorte Nations B et trois lignes résultats/calendrier. Les points observés3.125 puis7.875 et la sanction−0.125 restent décimaux, les rangs ex æquo et NULL/0 restent distincts. La correction visible au nouveau build ne change ni le corps ni l’ETag de l’ancien jeton ou de la cohorte indépendante. Les quatre V1 à jeton retenu restent identiques octet pour octet. L’oracle SQL indépendant avant/après lecture compare les94 tables et67 séquences,233 lignes physiques ; les deux fichiers sont byte exact (`aeb8879c9dcb9b33022d6fb0733589c9e866180e55229dd10806fcf307bfbec5`). L’INSERT runtime a réellement échoué25006.

Le RED Node24 d’entrée absente (`c8536c58…`) précède le produit. V1 (`a2a30bf4…`) échoue avant initdb parce que `-I` masque le chemin du helper ; zéro SQL/HTTP. V2 (`1a3d25db…`) installe le fixture B0, exécute la vérification d’identité TLS puis s’arrête au bind Node24 : le littéral127.0.0.1 passe par `dns.lookup`; 31 SQL,0 HTTP. Les deux corrections ne touchent que le harness. La V3 autorise le littéral exact via DNS natif, conserve les huit refus externes et passe sa calibration sans PG avant la reprise. Les releases, journaux et copies d’entrée antérieurs sont conservés. Le résultat V3 confirme API/pool/propriétaire fermés, PostgreSQL arrêté, racine retirée. Pic mesuré71 213 056 octets de disque PG,7 817 749 octets de preuve pendant les cas ; preuve finale8 632 397 octets.

Le cas413 exerce le garde d’une étiquette trop volumineuse. Le stress réel d’une édition de10001 matchs dépasse l’allocation physique du fixture et reste non vérifié. Le modèle103 conserve les labels de tours, mais ne porte pas le `has_playoff` source séparément : la valeur publique de ce lot repose uniquement sur le type d’étape déclaré, et reste omise si inconnu. Les saisons du core historique sont Ligue1, sans snapshots de classement, groupes ou coupes ; cette qualification ne prouve pas leur alimentation réelle. `DEPENDENCIES.json` donne les19 relations et leur portée au publisher partagé. Ce lot ne revendique ni import réel, ni réconciliation des sources, ni disponibilité des coupes sur RDS, ni déploiement.

Commit suggéré : `feat: serve eight competition and cup routes from published typed SQL`.
