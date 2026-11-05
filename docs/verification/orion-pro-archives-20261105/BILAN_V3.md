# Archives et données complémentaires — qualification locale V3

Le module `dashboard/backend/services/orion-pro-archives.js` (`cc48e560a8f0d7bd1180c98fa885652ad2a2ce0b1fafb5046e6a4b66d9777973`) couvre les quatre formes prévues. Il choisit les documents de provenance explicitement liés au snapshot de données du build READY, puis les observations et familles typées exactes. Il ne lit aucun corps source, projection historique, fournisseur ou Neon. Sans cohorte admise, le résultat reste indisponible ; une liste vide exige une couverture observée. Le contrat `archives-typed-v1` ne prétend pas reproduire les champs lexicaux qui n’existent pas en 103.

La campagne `runs/20261105T171344065087Z-archives-product-v3/result.json` (`1e0903e132d395e4c815a82169ad1d58b9176f99d4d8dc64acde3d9af9ed0426`) passe24 scénarios en6.183s :1290 SQL réservées et exactement1290 observées côté PostgreSQL,65 HTTP. Les comptes serveur sont1143 propriétaire,142 API,4 initialisation et1 refus d’écriture runtime25006. La session ordinaire est TLS, lecture seule,8s SQL/1s verrou/5s idle. Les8 calibrations réseau étrangères sont bloquées et les tentatives externes opérationnelles restent à0. API/pool, propriétaire, PostgreSQL et racine locale nettoyés. Pic disque PG73 736 192B, preuve durant la campagne8 170 499B, preuve finale8 769 943B.

| GET local | Octets | SQL |
| --- | ---: | ---: |
| Index résultats | 243 | 2 |
| Index buts | 236 | 2 |
| Saison résultats | 1779 | 3 |
| Saison buts | 1230 | 3 |
| Supplemental | 729 | 4 |
| Archive d’un match | 2743 | 9 |

Les HEAD/304 des quatre routes positives ont deux requêtes de métadonnées et aucun corps. L’archive d’un match réutilise les lecteurs SQL V1 match et tirs au même pro1 ; elle rend explicitement indisponibles les autres sections. Les vrais consommateurs inchangés lisent les corps HTTP : une saison, quatre rencontres dont une avec buts seuls, deux résultats complémentaires et extraction `match`/`shots` sans repli fournisseur. Les scores réglementaire, prolongation, final et tirs au but restent distincts. Les chaînes source date, lieu, présence et commentaire arrivent dans leurs colonnes CSV. Le second document admis contradictoire provoque503, même en conditionnel ; une correction seule change la publication courante, sans changer l’ancien corps/ETag ni le supplemental indépendant.

L’insertion d’une collection incomplète échoue réellement au sceau natif23514 : `Collection child count differs from its full typed parent: football.match_events`. Les94 tables restent exactes ; seules les deux séquences allouées au début de génération avancent chacune de1, preuves avant/après conservées. Les lectures et le refus runtime ne changent aucune des94 tables ni67 séquences (355 lignes physiques ; `native-read-before.json` et `native-read-after.json` sont byte exact, SHA`3e55487a285c7d30f063616e0ed3b168a0a3fd6e70457b7a17e05b14a2c0df9a`). Les quatre corps/ETag V1 retenus sont inchangés.

Le RED pré-code Node24 d’entrée absente (`c8f70767…`) est conservé. Le contrôle actual-app avant câblage confirme quatre501 sans cache ni accès DB (`ROUTER_BEFORE_V1.json`, `03dc19e0…`). V2 s’arrête après12 réussites au casA12,4.365s,406 SQL et31 HTTP : Python avait transporté le nombre0.82 comme chaîne vers l’oracle, tandis que le vrai corps HTTP était numérique. Le rejeu hors PG des six corps bruts passe ; la reprise V3 transmet ces textes sans conversion Python, sans changer produit, fixture ou attentes. Temps cumulé des deux campagnes10.548s sous90s. Les preuves V2, le rejeu et les65 pins sont préservés.

Le fixture n’exerce pas le stress à10001 rencontres ou20001 buts. Il exerce la limite réelle d’un champ trop grand (413), le compte exact, la séparation entre absence et vide observé, et la non-troncature sur la cohorte testée. Le mode est module HTTP indépendant avec contrôles actual-app V1. Il reste à câbler les quatre routes dans l’app et à vérifier l’alimentation des vraies cohortes et le déploiement. Zéro source/AWS/Neon/RDS dans ce lot. Le point archive ne revendique pas les13 familles originales complètes ; seules celles effectivement qualifiées ont `status:200`.

Commit suggéré : `feat: serve typed historical archives and supplemental match data`.
