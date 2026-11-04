# Heatmaps — intégration et contrôle ROOT

Le même jeu synthétique de six triplets produisait18 lignes de cellules avec le lecteur de matrice dense. Il produit maintenant **six lignes exactes**, avec leur ordre source, coordonnées, compteur et grille explicites. Les12 lignes erronées disparaissent ; ce constat de justesse sur cet exemple ne mesure aucune économie réelle de stockage ou latence. Le vrai RED reste dans `runs/20261104T220350142986Z-sparse-heatmap-precode-red/result.json`.

| Contrôle | Avant observé | Après vérifié |
|---|---|---|
| Six triplets sur trois parents | 18 enfants, coordonnées/grille incohérentes | Six enfants exacts, zéro densification/rotation |
| Source directe sous défaut archive | Cinq chemins source SQL inexistants acceptés | Refus atomique ; trois formes valides (archive, direct, record-at-data) conservent leurs chemins exacts |
| Valeurs absentes/null/vides/zéro | Cas spécifiés avant correction | États distincts et zéro observé conservé |
| Identité/cohorte et valeurs invalides | Contre-exemples explicites | 74 observations invalides et six incohérences d’acteurs/cohortes refusées sans famille partielle |

ROOT a relu le mapper, le correctif de provenance et le parcours SQL indépendant, puis relancé le vrai workflow local : **9/9 scénarios heatmaps et8/8 scénarios native31 inchangés réussissent**. Preuve `runs/20261104T224628219790Z-root-reviewed-portable-sparse/result.json` ; les deux PostgreSQL jetables sont arrêtés et leurs répertoires retirés. La correction ROOT transmet également le `--pg-bin` externe au sous-processus native31, afin que la CI Linux ne sélectionne pas son défaut Darwin ; ce point est spécifié dans PROTOCOL avant modification du harness.

La CI ajoute ce dixième workflow Pro et conserve ses preuves ainsi que celles de sa régression imbriquée. Les neuf autres suites représentent129 cas de premier niveau ; le nouveau workflow en ajoute neuf, et réexécute les huit native31. Le [run GitHub41928530242](https://github.com/OrionQuantPlatform/STATARENA/actions/runs/41928530242) du commit4a6ae73222 réussit ses trois jobs ; son log confirme les dix suites23+25+7+8+20+4+8+9+23+11=138cas de premier niveau. Les huit native31 sont aussi réexécutés par le workflow heatmap et conservés dans son artifact. Ces totaux ne sont pas138 tests uniques supplémentaires. Métadonnées/log : ci-main-4a6ae73222.json/.log.

Le normalizer4b98a829… reste celui vérifié par le sous-agent ; `ROOT_REVIEW.json` lie son hash complet, le nouveau hash du harness portable, les preuves, le modèle et l’ancien ledger immuables. Modèle103, SQL012/013 et RDS inchangés. Aucune source interrogée ; **0/1344 triplets réels comparés**. Noms/shirts observés, autres feuilles et la fidélité complète restent ouverts ; aucune publication/purge n’est autorisée par ces tests.

UX : les futures heatmaps n’afficheront plus des coordonnées fabriquées. DX : un seul mapper sparse, deux lectures de cohortes par famille, validations bornées ; l’import reste refusé quand le modèle ou la cohorte ne suffit pas. AX : chemins source explicites et preuves source→SQL inspectables. Aucune latence/capacité WAN ni réduction de coût n’est mesurée par ce lot.

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_heatmaps_local.py --pg-bin /tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin --label root-reviewed-portable-sparse
```

Commit proposé : `fix: preserve sparse heatmap coordinates and source locators`.
