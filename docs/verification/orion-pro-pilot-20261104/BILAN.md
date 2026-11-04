# Pilote Orion Pro — 4 novembre 2026

Le schéma pilote est **installé sur le RDS existant** et son contrôle indépendant passe **11/11**. L'importeur réel reste un prototype local partiel : **aucune acceptation de migration complète, publication publique ou suppression de sources** n'en découle. RDS contient ici le schéma et ses dix références initiales ; les joueurs, matchs et observations réels du pilote n'y ont pas encore été importés.

| Mesure RDS directement vérifiée | Avant | Après |
|---|---:|---:|
| Tables dans les trois nouveaux schémas | 0 | 94 |
| Colonnes / FK | 0 / 0 | 1 709 / 431 |
| Contraintes PK + FK + UQ + CHECK | 0 | 1 476, toutes validées |
| Vues courantes / index | 0 / 0 | 46 / 352 |
| Références typées initiales | 0 | 10, génération 1 scellée |
| Tables métier/index : empreinte mesurée | 0 | 3 710 976 octets, soit 3,539 Mio |
| Santé Vercel / manifeste Vercel / santé AWS | 200 / 200 / 200 | 200 / 200 / 200 |

L'empreinte indiquée couvre tables, index et éventuels TOAST ; elle exclut séquences, catalogue système et WAL. C'est une occupation supplémentaire de fondation, pas de l'espace récupéré. Aucun gain de latence/coût de production n'est annoncé pour ce lot de schéma.

Commits associés : `docs: record the approved Orion pilot and native metric amendment` et `feat: add the approved Orion Pro schema and integrity pilot`. Commits suivants proposés : `feat: import the bounded Orion Pro pilot from existing AWS sources`, `feat: add guarded Orion Pro RDS pilot gate`, `ci: exercise the approved Orion Pro pilot without cloud access`.

## Ce qui est acquis

L'accord explicite « Valider et lancer le pilote » est conservé dans `approval.json`, avec le modèle original `028c221d…` et le commit de plan `411207645f…`. `model-amendments.json` enregistre séparément la correction ciblée `18da43f9…` : quatre expressions CHECK et quatre descriptions pour distinguer les états natifs des métriques. Aucune table, colonne ou clé n'a été ajoutée par cette correction ; elle n'est pas présentée comme un second accord utilisateur.

| Mesure comparable | Avant ce pilote | Après vérification locale | Portée |
|---|---:|---:|---|
| Tables actives du nouveau modèle créées par les migrations | 0 | 94 | 1 709 colonnes, 431 FK ; les anciennes tables AWS existent toujours |
| États admis dans les observations de métriques enregistrées | nombre, texte, booléen | mêmes états + `null` explicite + propriété absente prouvée | Une ligne SQL manquante reste inconnue |
| Scénarios de schéma/intégrité | premier lancement impossible sans migrateur | 23/23 passent | 57 écritures invalides rejetées dans les workflows |
| Scénarios d'états natifs | 19 réussites, 4 échecs, 2 non vérifiés sur le modèle approuvé original | 25/25 passent sur le modèle corrigé | RED original conservé |
| Valeur xG et total de la cohorte témoin | 0,82 ; somme 1,00 | correction 0,67 ; somme 0,85 | Ancienne lecture figée conservée ; éditions partagées A/B affectées, C préservée |
| Sources brutes nouvelles dans S3 ou RDS | 0 | 0 | Décodage des sources AWS existantes en mémoire, puis SQL typé local |
| Ressources AWS supplémentaires créées pour ce pilote | 0 | 0 | Même RDS 64 Gio ; aucun redimensionnement |

Les neuf tables réservées aux futurs modèles ne sont pas installées : les 94 tables actives n'ont aucune FK qui en dépende. Les dix lignes de référence sont six périodes et quatre positions ; leur génération est réelle et scellée, leur empreinte lie le modèle, le migrateur et les migrations réellement appliquées. Les versions nécessaires restent dans les tables métier ; aucune table sœur `_history` ou registre universel de lignes n'est créée.

Preuves SQL : `runs/20261104T183222785812Z-recorded-metric-amendment-regression/result.json`, `metric-state-runs/20261104T183139777229Z-targeted-native-metric-candidate/result.json` et `bootstrap-artifact-review.json`. Chaque répertoire conserve la commande, les entrées, le SQL appliqué, les journaux et la fermeture du PostgreSQL possédé. Les échecs initiaux et intermédiaires restent présents.

## Pilote sur les sources réelles

Périmètre : Ligue 1 `l_3FJFUl`, saisons 2025/2026 et 2026/2027, uniquement à partir de sources déjà sur AWS. Le transfert physique Neon → AWS du second Codex n'a pas été relancé.

- 612 rencontres planifiées ou terminées, dont 387 terminées ; 839 joueurs et 20 clubs.
- 15 437 participations/statistiques et 9 795 tirs normalisés ; identifiants publics conservés.
- 61 748 observations d'état pour xG, xA, xGOT et minutes, rattachées au même record source, participant, période, variante et cohorte sélectionnée que la projection commune.
- 13 familles détaillées exercées pour un match réel de chacune des deux saisons : **projections typées partielles**, pas reprise complète des feuilles de chaque observation.
- 776 profils de joueurs et 20 observations de clubs sélectionnés par identifiant exact. Une référence de joueur pointait vers un autre joueur : sa biographie a été rejetée. 62 clés de ressources de profils restent introuvables dans la recherche ciblée ; cela ne prouve pas leur absence globale sur AWS.

Le run `real-source-runs/20261104T185546803265Z-final-native-states-and-real-families/result.json` passe 14 contrôles, avec `fullAcceptance=false`. Les 61 748 états ont le même SHA source/SQL `e08b11c0…`, zéro ligne inconnue dans ces quatre slots attendus et zéro divergence de rattachement/cohorte. Une correction explicitement simulée d'un vrai record passe par le même normaliseur, conserve la lecture précédente et distingue xA `null` de xGOT absent. Le réimport sans changement n'ajoute aucune ligne **dans la même instance et son cache** ; la reprise dans un processus neuf reste à implémenter/vérifier.

La revue indépendante a ensuite identifié deux défauts du prototype : valeur vide inventée depuis une collection manquante et arrondi possible dans les empreintes au-delà de 28 chiffres. Le RED pré-code `real-source-runs/20261104T190633468265Z-review-red-decimal-and-collection-shapes/result.json` les reproduit sans lecture AWS. Après correction, `real-source-runs/20261104T190755631159Z-final-reviewed-exact-numbers-and-collections/result.json` passe **15/15**, y compris ces contre-exemples, avec les mêmes 61 748 états source/SQL et `fullAcceptance=false`. Le budget cumulé des passes réelles est 67 requêtes / 190 950 214 octets décodés, inférieur aux limites 100 / 256 Mio. Le schéma additif et ses 23/25 scénarios ne dépendent pas de cette logique d'import.

Les requêtes locales suivantes ont été exécutées une fois sur les données du pilote : liste de 100 matchs 1,617 ms ; agrégat joueurs 10,129 ms ; clubs 3,813 ms ; agrégat matchs 0,731 ms. **Ce sont des lectures locales, sans baseline équivalente : aucun pourcentage de gain RDS/API n'est déduit.** Les latences, octets HTTP et invalidations du futur lecteur public restent à mesurer.

## RDS et production

Le wrapper `dashboard/scripts/orion_pro_rds.py` sépare le plan hors ligne, le précontrôle en lecture seule et l'application explicite. Sept scénarios CLI passent sans appeler AWS. Les premiers précontrôles RDS confirment l'instance existante PostgreSQL 18.6, 64 Gio, TLS et les rôles distincts ; les trois nouveaux schémas sont absents. Environ 47,03 Gio libres, CPU 4,45–5,525 % et 59,455 crédits ont été observés à ces instants. Ces mesures de capacité ne constituent pas un benchmark causal.

Les précontrôles ont correctement bloqué tant que le code n'était pas publié, l'acceptation parent absente, une métrique trop ancienne ou le pilote source encore en transaction. Aucun travail concurrent n'a été annulé pour forcer un passage. Le readback indépendant passe **8/8 E2E locaux sous TLS** : golden 11/11 et six dérives réelles rejetées (droit UPDATE sur colonne, CHECK affaibli, index, vue, action FK, sémantique UQ). Son oracle lie les définitions normalisées PostgreSQL aux octets exacts du modèle et des migrations. Preuve : `rds-readback-local-runs/20261104T190937868865Z-catalogue-guards-green/result.json`.

Sur le commit publié `256fce7b96…`, les trois jobs GitHub CI passent, dont les quatre suites Orion locales/hors ligne ; `ci-main-256fce7b96.json` conserve jobs et métadonnées des artefacts. Le précontrôle `rds-runs/20261104T191730693147Z-committed-schema-bootstrap/result.json` passe 15 portes, sans écriture. Le premier essai réel `rds-runs/20261104T191848988657Z-first-schema-bootstrap/result.json` a ensuite été **arrêté avant connexion administrateur et avant DDL** : le paramètre administrateur existant ne contient pas d'hôte et conserve le nom historique `statarena`. La cible de connexion reste exclusivement l'hôte vérifié et `statarena_prod` ; le paramètre n'est pas modifié. La lecture indépendante `admin-capability-readonly.json` confirme que le rôle administrateur existant est propriétaire de `statarena_prod` et possède CONNECT/CREATE.

Après RED du format historique et d'une erreur d'itération du catalogue en réapplication, le wrapper corrigé passe **20/20 E2E locaux**, puis de nouveau **7/7 CLI**. La première application crée réellement les 94 tables sur le PostgreSQL possédé sous TLS ; les réapplications réutilisent la génération et les dix références ; trois readbacks passent 11/11 ; onze formats invalides sont refusés avant connexion. Les identifiants simulés et clés TLS ne sont pas conservés dans les preuves. Résultats : `rds-apply-local-runs/20261104T192817694935Z-historical-admin-green/result.json` et `rds-gate-runs/20261104T192907889103Z-historical-admin-offline-gates/result.json`. La CI inclut cette cinquième suite. Ce correctif ne modifie ni modèle, ni migration, ni cible, ni paramètre AWS.

Les trois jobs CI sur le correctif publié `c66e036521…` passent (`ci-main-c66e036521.json`). L'acceptation parent v2 conserve la précédente et lie ce commit aux mêmes preuves SQL/métriques/sources, plus l'application locale complète. Après rafraîchissement de la mesure de crédits, le précontrôle `rds-runs/20261104T193720255471Z-fresh-credit-reviewed-admin/result.json` est prêt. L'application réelle `rds-runs/20261104T193736115395Z-reviewed-schema-bootstrap/result.json` confirme **`atomic_committed`** : 012/013, dix références et droits des rôles existants, uniquement dans les trois nouveaux schémas. L'appel gardé entier dure 13,827 s, précontrôle compris ; ce n'est pas un benchmark de requête.

Le readback réel `rds-readbacks/20261104T193830558195Z-rds-schema-bootstrap/result.json` passe **11/11 avec 14 SELECT**. Il retrouve exactement le catalogue attendu, 90 fonctions/84 triggers, les empreintes journalisées, la génération 1 et dix graines, et zéro droit d'écriture effectif du runtime sur les nouvelles relations/colonnes. Aucun fait métier au-delà du bootstrap n'est présent. Les fichiers 012/013 sont maintenant scellés : toute évolution ultérieure exige une nouvelle migration.

La production Vercel reste `dpl_2YjDXsva7FBr4yDnzRShmZ776MbA`, READY, code `f65036cdb9…` déjà accepté lors du lot disponibilité. `vercel-production-readback.json` conserve la réponse de contrôle. Les probes publics avant et après installation (`public-probes/20261104T190448902600Z-before-schema-apply/result.json`, `public-probes/20261104T193830583003Z-after-schema-apply/result.json`) vérifient **3/3 HTTP 200** : santé Vercel, manifeste Vercel et santé CloudFront/AWS. Le frontend utilise toujours le pont temporaire vers les données sauvegardées ; **aucune bascule vers le nouveau modèle n'est déclarée**.

## Restant et limites

Restent notamment : toutes les feuilles utiles des 512 sources ciblées, les autres métriques communes et leurs états natifs, coordonnées/unités des tirs, médias et biographies détaillées, les classements/enrichissements, la reprise sans cache de processus, l'import RDS réel, les agrégats de production, lecteurs et contrats API, invalidation A/B/C sur le site, workflows de collecte adaptés, parité desktop/mobile complète et réconciliation globale avec Neon.

La suppression des anciens documents RDS/objets S3 et la bascule finale attendent l'acceptation conjointe données + backend. Aucun espace récupéré ni gain de coût/latence de ce futur modèle n'est revendiqué à ce stade. Le gain mesuré du lecteur existant du lot précédent (−22,49 % sur une seule paire SQL comparable) reste documenté séparément dans `../orion-availability-20261104/BILAN.md`.

Le contrôle d'espaces Git a signalé des espaces terminaux dans le SQL généré 013 et ses copies de preuve. Les octets appliqués et empreintes ont été conservés ; ce contrôle n'est pas présenté comme réussi pour ces fichiers immuables. Les journaux bruts sont également conservés sans nettoyage éditorial.
