# Publisher SQL V1 — qualification locale

Commit suggéré : `feat: publish immutable Pro V1 SQL summaries`.

Le produit `dashboard/scripts/orion_pro_publish.py` est implémenté et la campagne
locale V2 passe **30/30 cas et 5/5 contrôles de préparation**, en **25,464 s**.
Il construit les résumés SQL et active les publications des quatre readers V1
existants. Ce résultat termine ce lot local ; le backend complet, la publication
réelle sur RDS et les 50 autres formes de route restent à terminer.

## Résultat observé

| Mesure | Entrée initiale | Fin de la campagne V2 |
|---|---:|---:|
| Lignes SQL conservées | 171 | 255 |
| Éditions | 3 | 3 |
| Identités match conservées | 5 | 6, dont le draft négatif rendu supprimé par successeur |
| Builds READY | 0 | 10 |
| Résumés match | 0 | 20 |
| Résumés édition | 0 | 10 |
| Snapshots acceptés | 3 | 20 |
| Intervalles de publication | 0 | 9 |

Les trois premiers builds utilisent le pair effectivement déclaré **dg7/cg2**,
après les générations négatives/restaurées ; le jeu initial était dg3/cg2.
Les dix builds finaux comprennent l'orphelin READY de la course dirty conservé
pour audit. Le nombre de snapshots acceptés est distinct du compteur de
séquence final24 : les générations annulées ne sont pas des snapshots acceptés.

La campagne consomme **2 049 commandes SQL réservées**, **2 048 observées par
PostgreSQL**, et **158 requêtes HTTP**. Les traces serveur distinguent1421
commandes du harness principal,327 de l'API,288 des deux workers et12 des
probes de privilèges ; les194 commandes de construction initiale sont séparées.
Le budget d'exécution révisé est4000SQL/600s/200HTTP ; aucune borne n'est dépassée.
Ce budget corrige une allocation interne insuffisante, sans gain SQL revendiqué.
Il ne constitue pas une mesure de performance de RDS ou du site déployé.

## Contrats effectivement vérifiés

- Les données, révisions, scores finaux et shootout, dates inconnues, valeurs
  zéro/false/chaîne vide et NULL sont préservés. A3 distingue score absent et
  score observé NULL/NULL. Le profil équipe C peut rester NULL et le tir C
  conserve ses champs optionnels NULL. Les compteurs A/B/C sont respectivement
  (3,2,2,1), (1,1,2,2), (1,1,2,1) ; B contient deux joueurs d'effectif distincts,
  dont un seul played. Aucun total de buts ni formule nouvelle n'est calculé.
- La clôture typée exacte, la sélection des profils de même source, les clés
  réelles de couverture, les snapshots effectifs, le code et l'environnement
  correspondent à l'oracle indépendant. Les fins d'intervalle et les champs
  physiques de stockage n'altèrent pas les anciennes clôtures.
- Les drafts, engagements manquants et déclarations source/révision/type/
  couverture/période/acteur incohérentes sont refusés avant publication.
- Les builds et résumés partiels s'annulent ensemble. Les orphelins READY sont
  réutilisés avec les mêmes IDs4/5/6. La validation READY native013 est réellement
  exécutée par son trigger, sous le rôle writer existant.
- Les workers concurrents dédupliquent le même plan et publient des scopes
  disjoints. Les pointeurs A/B changent atomiquement ; leur crash partiel laisse
  l'ancien ensemble public. C conserve ses IDs, snapshots, tokens et octets
  pendant les corrections A/B, et réciproquement.
- `before_activation_recheck` s'exécute sans verrou global détenu. La correction
  C plus récente peut se committer à cette barrière ; le plan préparé reçoit
  STALE_PLAN, conserve son orphelin READY et ne consomme aucune génération de
  publication. Aucun watermark dirty n'est effacé ou écrasé.
- Les deux no-op conservent séquence24, pointeurs et dirty, avec **zéro appel à
  begin_generation**. Les anciennes pages, résumés, tirs, ETags et curseurs
  restent exacts ; le curseur mutable périmé reçoit409/no-store.
- HEAD et304 utilisent les métadonnées, les lectures légères évitent les familles
  lourdes et seuls les tirs explicitement demandés sont matérialisés. Les états
  unavailable, unknown, absent et null donnent404/no-store sans ETag.
- Writer : DELETE dirty, validation directe et nextval de génération restent
  refusés42501. Runtime : UPDATE reste42501 même readonly désactivé ; zéro table
  ou colonne métier accessible en écriture. Les délais réels sont8s/1s/5s ;
  les probes observent1,002–1,003s pour le verrou et8,002–8,004s pour l'instruction.

## Preuves et limites

Reçu principal :
`runs/20261105T112847690581Z-product-v2/result.json`, SHA256
`22333214e581e424aa9f66f0feab94f5f8bac9e123722ae5684194aa4375b614`.
La supervision est `campaign-v2-supervision.json`, SHA256
`55dda1fbeda8a8488d0e9403370cfe61d711879ea7b45d141b8755a42feeb8f0`.
Le produit qualifié est SHA256
`222c4647a850eb3fe51dcc8c9ba71e35dafbfe28f69443c558675ebcca8faf59`.

Le dossier du run contient setup, admission et inputs exacts,15 readbacks
indépendants,30 résultats, traces SQL/HTTP, bodies synthétiques, événements de
barrière, processus et logs. `CLEANUP_READBACK_V2.json` confirme directement que
le répertoire `/tmp` possédé a disparu et qu'aucun serveur, API ou worker du lot
ne reste actif. Zéro accès source pendant les requêtes, zéro input modifié,
zéro action cloud ou déploiement. Les101 preuves qualifiées et les148+20
prédécesseurs restent byte-identiques.

Commande réellement exécutée, depuis la racine du dépôt :

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-publisher-20261105/product-campaign/run_campaign_v2.py --label product-v2
```

Une reproduction exige une nouvelle allocation ROOT et un nom de reçu
superviseur distinct ; le reçu existant bloque volontairement sa réutilisation.
Le wrapper V2 diffère du wrapper V1 uniquement par ce nom. Les fixtures, les
oracles et les attentes métier sont inchangés ; le dossier conserve les copies
originales et les trois seules adaptations d'exécution (allocation SQL et path).

La V1 a réellement échoué et reste conservée dans
`runs/20261105T112352655419Z-product-v1/` :5/5 setup,9 cas marqués pass, mais
P21 portait encore retryPendingVerification, donc8 cas pleinement vérifiés et
21 non vérifiés.769 réservations/766 commandes serveur/5HTTP. Le garde lexical
interprétait `DO UPDATE SET` comme une mutation de table SET. Le produit utilise
désormais INSERT ou UPDATE explicite avec compare-and-swap sous verrou global ;
le garde et ses attentes n'ont pas été changés. Aucun retry implicite n'a eu lieu.

Cette CLI n'accepte que l'admission synthétique possédée et le label de code
`local-owned-e2e-v1`. Les pins SQL/JS sont des dépendances de release déclarées,
vérifiées séparément ; les fichiers modèle/helpers Python sont réellement lus.
Cette frontière locale n'est pas une sécurité RDS : elle ne qualifie pas le
pinning hostname/hostaddr/CA/acteur ni le refus de toute configuration libpq
ambiante. La future admission réelle doit traiter source_policy, drafts,
participation et engagements avec leurs faits réels, sans réutiliser fixtureOnly
ou le code_commit local. Aucun broad flip draft→published n'est autorisé.
La voie structurée COMMIT_ACK_UNKNOWN est implémentée ; aucun défaut réseau
immédiatement après COMMIT n'a été injecté dans ces30 cas gelés.
