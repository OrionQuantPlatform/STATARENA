# Pilote réel natif et spatial — 5 novembre 2026

Les **15 contrôles exécutés passent**, sans échec ni contrôle non exécuté. Les empreintes indépendantes des sources et des tables SQL concordent pour **478 547 valeurs statistiques** et **1 344 cellules spatiales ordonnées**, avec 32 parents heatmap. ROOT a relu les résultats, recompté les états, vérifié les fichiers épinglés, les séquences et le nettoyage : [revue](ROOT_REAL_V2_REVIEW.json).

| Mesure | Avant | Résultat de ce lot |
|---|---:|---:|
| Champs communs vérifiés par performance sur le même corpus | 4 | 31 |
| Valeurs dont états et contenus source/SQL sont comparés | 61 748 | 478 547, soit ×7,75 (+675 %) |
| Cellules spatiales acceptées par comparaison source/SQL | Non vérifiées | 1 344/1 344 |
| Relance dans un processus neuf | Non exécutée après l'échec spatial v1 | 94 tables et 67 séquences exactement inchangées |
| Nouvelles lectures distantes de ce lot | — | 0 SQL source, 0 HTTP source ; capture RAM existante réutilisée |
| Écritures dans RDS de production | — | 0 |

Les valeurs se répartissent en **45 591 absences**, **188 032 null**, **175 407 nombres non nuls** et **69 517 zéros**. Aucun état n'est remplacé par un autre. Empreinte statistique commune : `5f9175c1526ad2db4426ebe02d3e412e20999c2bd6486aef5d82d082f34255e0`. Empreinte spatiale commune : `25325f5163ab25a842e6ddbba25dea19d6d16d090761b4e88d7d4d37ed0b5db3`.

Le premier run réel v1 reste conservé : 13 contrôles réussis, 1 échec de comparaison spatiale, 1 non exécuté. Le défaut concernait la sérialisation de Decimal et d'entiers SQL dans l'oracle. Le correctif ne change ni les données, ni le normaliseur, ni le modèle. Les 14 contrats du sérialiseur avaient été écrits avant ce correctif ; le run réel v2 le confirme désormais avec le corpus source. La comparaison spatiale est enregistrée avant l'assertion.

Le run v2 dure **226,101 s**, avec **1 860 562 944 octets alloués au pic observé** dans ses répertoires temporaires. Il s'agit du disque local, pas de la mémoire RSS ou du stockage RDS. Aucune réduction de latence web, de coût de calcul ou d'espace RDS/S3 n'est établie. Le run v1 s'arrêtait avant la relance ; comparer leurs durées comme un gain serait incorrect.

Le corpus couvre 612 fixtures, 387 matchs terminés, 15 437 performances, 9 795 tirs, 839 joueurs uniques et 20 équipes. **62 profils exacts restent introuvables**. Les noms/numéros observés dans les sources spatiales et les autres familles détaillées ne sont pas déclarés complètement intégrés. `fullAcceptance=false` : transfert typé RDS, publications, routes, collectes et réconciliation globale restent nécessaires avant bascule et nettoyage.

## Preuves et reproduction

- [Superviseur](runs/20261105T015838104703Z-real/result.json), SHA `8a0b1c438eaabb1d72de1d867a57d16e0ae6c51e0f7162c0d46069b71112d8d4`.
- [15 contrôles](../orion-pro-real-native-spatial-20261104/runs/20261105T015838183427Z-real-native-spatial-overlay-e0810f-v2/result.json), SHA `9decef355c43bab976fb1af58b229b47f8cf07574652bdbeec9d1463266c62c6`.
- [Oracle spatial](../orion-pro-real-native-spatial-20261104/runs/20261105T015838183427Z-real-native-spatial-overlay-e0810f-v2/spatial-oracle-result.json).
- [Allocation exacte](ROOT_REAL_RELEASE_V2.json) et [compteur consommé](real_execution_ledger_v2.json). Les anciens compteurs et les 18 fichiers épinglés sont inchangés.

Commande exécutée :

```sh
python3 docs/verification/orion-real-supervision-20261105/supervise_real.py --run --mode real --attempt v2 --release docs/verification/orion-real-supervision-20261105/ROOT_REAL_RELEASE_V2.json --release-sha256 128deca3ddc9f1cc3cc91593b7bcd098dc41052809bf5b08242136626b8e8ea4
```

Le protocole et les entrées exactes sont archivés dans les runs. L'allocation est épuisée : une reproduction exige une nouvelle allocation explicite sans réinitialiser l'ancienne. Les quatre PostgreSQL possédés et leur répertoire privé ont été supprimés après arrêt. Le processus RAM source reste vivant pour la suite ; aucun contenu brut n'a été exporté par cette vérification.

UX : la production disponible reste servie. DX : les états natifs sont vérifiés directement en SQL. AX : résultats, échecs antérieurs, entrées et limites sont inspectables. Cette couverture partielle ne justifie aucune suppression de source.

Commit suggéré : `test: verify real native and sparse spatial reconciliation`.
