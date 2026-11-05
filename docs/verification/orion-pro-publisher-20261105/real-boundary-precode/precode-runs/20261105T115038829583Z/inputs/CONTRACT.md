# Frontière réelle minimale des quatre readers V1

Commit suggéré : `test: specify real SQL publication admission before adapter code`.

Préparation avant adaptateur réel. Aucun PostgreSQL, RAM source, AWS, RDS,
SSM, Neon, schéma, grant ou déploiement n'est ouvert ou modifié par ce lot.
Le publisher synthétique222c4647… et ses30/30 restent une livraison distincte.
L'adaptateur futur est `dashboard/scripts/orion_pro_publish_real.py` ; ce document
et sa matrice E2E le précèdent. Le test exécutable actuel ne qualifie que son
absence réelle ; les parcours PG/HTTP futurs sont spécifiés, non exécutés.

## État établi et portée

Le reçu global source `source-runs/20261105T111626302849Z/result.json` est FAIL.
La récupération ROOT distincte établit pourtant un core commis : un run partiel
core1, génération2/snapshot2 scellés,839 joueurs,612 matchs et478547 slots natifs ;
la phase spatiale57014 a rollback, zéro heatmap. ROOT a arrêté et conservé ce
répertoire. Le nouveau contrôleur RO du chantier données doit encore qualifier
ce core par native31/94tables/67séquences et no-op, sans reconstruction.

RDS typé reste au bootstrap B0/g1 sous014/P1 tant que ROOT n'a pas transporté puis
relu les faits. Les612 matchs du core ne sont donc pas annoncés sur AWS typé.
Le core provient des deux partitions normalisées **déjà présentes dans AWS**,
ligue publique `l_3FJFUl`, saisons2025/2026 et2026/2027, aux hashes du manifeste
gelé. Les fichiers/index existent déjà ; aucune dépendance runtime Neon n'est
nécessaire pour ces partitions. La portion spatiale Neon n'est pas nécessaire
aux quatre readers V1 et reste explicitement hors de cette première admission.

Le premier scope public peut être une seule édition complète effectivement
qualifiée, ou les deux. Il doit énumérer **tous** ses matchs canoniques utiles,
leurs révisions et les exclusions justifiées. Il ne peut choisir arbitrairement
quelques matchs déjà faciles ni cacher les drafts restants de cette édition.
Un match incohérent bloque l'édition ; une autre édition complète peut avancer
avec une exception nommée pour la première. Les IDs sont lus en SQL et reliés
aux alias, jamais déduits de la saison, d'un dossier ou d'un ordre d'array.

## Trois opérations séparées

1. **Transfert core** : ROOT transporte le checkpoint validé, préserve les91
   relations métier et mappe les3 contrôles techniques. Un readback RDS indépendant
   prouve IDs/révisions/types/valeurs/états, pas seulement des totaux. La policy
   source est `real_source_core_v2_native31`, distincte du transform de transport.
2. **Admission dérivée revue** : un producteur distinct transforme seulement
   les prérequis explicitement justifiés ci-dessous dans une génération possédée.
   Il préserve les faits sources, clôt une seule fois les intervalles nécessaires
   et conserve les anciennes révisions. Aucune mise à jour en place des drafts,
   aucun broad flip, aucun framework d'historique ou nouveau schéma.
3. **Publication** : l'adaptateur réel consomme uniquement les faits déjà admis,
   construit les deux produits existants et active le groupe atomiquement. Il
   ne décide pas de l'admission ni ne répare les sources pendant un build.

Chaque opération a son code/hash, input closure, reçu et autorisation ROOT.
Une acceptation de transport, un SHA de fichier ou un run local n'autorise pas
à publier. `fixtureOnly`, `synthetic_declared_business_admission`,
`pilot_priority_v1` et `local-owned-e2e-v1` sont interdits dans l'admission RDS.
Le commit de code réel est celui relu par ROOT, jamais un label local inventé.

## Ce que le core doit qualifier ou compléter

Ces constats sont déduits du normalizer gelé4b98a829…, pas d'une nouvelle lecture
du core. `READBACK_REQUEST.json` sépare les quantités déjà observées des mesures
qui manquent encore.

| Prérequis | Core actuel dans le code | Admission minimale proposée |
|---|---|---|
| Matchs | Tous insérés draft, ligne674 | Vérifier individuellement chaque membre de la cohorte complète ; insérer des successeurs published seulement après preuves |
| Engagements | import_core n'insère aucune competition_teams | Dériver l'engagement de chaque équipe réellement observée dans les participants de l'édition, statut **observed**, provenance derived ; jamais confirmed par défaut |
| Participation | played=None, starter ou observed, lignes692–694 | Conserver l'inconnu sauf preuve native de minutes numériques strictement positives ou tir accepté du joueur dans ce match et cette équipe |
| Joueur de tir sans ligne d'effectif | À mesurer par anti-join | Un tir réellement accepté peut justifier une nouvelle participation derived/observed/played=True ; sans preuve d'identité/équipe exacte, refus. Ne créer aucune statistique31 NULL pour ce nouveau membre |
| Noms d'équipes | Identités teams.name conservées, pas de team_profile_versions avant la phase profils1052 ; participant_label non renseigné | Préférer un profil réellement retenu et de même source. À défaut, dériver explicitement le label du participant depuis l'identité typée teams.name, avec règle/ID/source-record témoin et preuve de lignée. Garder NULL si réellement inconnu ; ne fabriquer aucun profil provider |
| Scores | Scope final_without_shootout, score_basis unknown, pas de shootout importé dans core | Réconcilier présence/NULL/valeur et portée des champs normalisés ; si le source contient le shootout, l'importer séparément. Aucune somme de scopes ni zéro par défaut |
| Date/heure | match_date est la partie date, kickoff inconnu | Prouver que l'entrée acceptée est effectivement une date ; une heure source existante ne doit pas être jetée puis annoncée comme inconnue |
| Shots | Couverture créée à partir de tables.matches et comptages ; projection SHOT_MAP partielle | Réconcilier le **set** attendu, IDs, source/variant/révisions/périodes/acteurs et chaque champ V1 ; compter les lignes ne suffit pas |
| Profils joueurs | Profils normalized retenus, priorité source à contrôler | Qualifier l'unique gagnant same-source provider_exact > normalized > manual. Les62 trous d'URL full-profile historiques ne prouvent pas une absence du fallback normalized |

La règle played doit utiliser `legacy_normalized_minutes`, value_kind=number,
numeric_value>0, avec source/variant/période/participant exactement compatibles.
Une ligne de performance, starter=true, zéro, NULL, absent, chaîne ou boolean
ne prouve pas à elle seule que le joueur a joué. Zéro ne prouve pas unused.
Un tir accepté est une preuve de participation ; ses minutes restent inchangées.
L'evidence textuelle identifie la règle et les vrais PK témoins. Les faits
derived gardent un transform propre ; ils ne sont pas relabellisés observations
provider. Les dérivations et leurs règles exigent la revue ROOT avant écriture.

Le label dérivé depuis teams.name est une proposition minimale à qualifier :
il ne prétend pas être un participant_label observé dans la fixture. Le readback
doit montrer la vraie identité typée, les alias source et le reçu du document
qui justifie ce nom. Si la lignée n'est pas reconstructible à partir du core,
ROOT normalise uniquement les lignes équipes nécessaires des deux partitions
AWS existantes, avec leurs locators exacts ; aucun source-record factice.

## Révisions et dépendances

Une modification pure de publication_state n'oblige pas à copier aveuglément
478547 métriques. Le modèle approuvé et013 autorisent un enfant à référencer
une ancienne ancre compatible quand identité et appartenance métier sélectionnée
restent identiques (`_membership_checks`). Cette règle native doit être appliquée
explicitement et testée : aucune référence vers une autre équipe/édition/joueur
n'est acceptée. Une référence ancienne compatible n'est pas un alias latest.

En revanche l'alias public match doit être un successeur pointant vers la
révision publiée exacte : le reader joint alias.match_revision_id à la révision
du résumé. Les couvertures et ancres conservées sont inventoriées avec leur
vrai PK et révision. Le contrat d'admission décide chaque rebase réellement
nécessaire ; il ne réécrit pas une famille sportive inchangée pour un faux fetch.
La stratégie finale doit donc être revue à partir des FKs et readbacks réels.

La phase d'admission possède sa propre input closure et les dépendances des
dérivations (minutes natives, tirs, identités, participants). Une correction de
ces entrées exige sa réévaluation avant toute nouvelle publication. Le publisher
conserve `orion-four-readers-dependencies-v1` pour les **faits admis** des quatre
readers ; ce n'est pas le graphe d'invalidation du producteur d'admission.
Les deux clôtures, leurs snapshots et leurs invariants sont distincts et pinés.
Si ce contrat ne peut être tenu, ROOT doit versionner explicitement la dépendance,
jamais ajouter silencieusement des tables à l'oracle V1 gelé.

Le code de publication ne reprend pas le plafond local5000 lignes. La clôture
doit pouvoir lire en flux les participants et tirs d'une édition entière,
avec buffers/batches bornés et aucune omission. Les limites de qualification
restent dans l'allocation des tests, pas dans la portée fonctionnelle finale.

## Frontière RDS explicite

Le mode par défaut est offline : zéro driver, socket, subprocess, SSM ou provider.
Le mode réel exige admission réelle complète, hashes de contrat/code/environnement,
readback RDS du core et de l'admission, puis release ROOT distincte et non expirée.
Aucun DSN libre, alias remote, fallback ou découverte de secret n'est accepté.

Avant toute connexion, refuser les variables libpq ambiantes PG* (incluant
PGHOSTADDR/PGSERVICE/PGSERVICEFILE/PGOPTIONS/PGDATABASE/PGUSER/PGPASSWORD/PGPASSFILE),
les URLs DB ambiantes et toute clé d'endpoint inconnue. L'authentification est un
argument secret explicite validé par la frontière déjà prévue par ROOT, jamais
une valeur d'un fichier d'admission ni un fallback `.pgpass`/service.
Construire les paramètres nommés exacts : hostname RDS connu, hostaddr littéral
relu dans l'ensemble DNS approuvé de la release,5432/statarena_prod/
statarena_ingest, sslmode=verify-full et CA pinée par contenu. Aucun paramètre
peut être ajouté ou remplacer host/hostaddr/options/role par héritage.

Après connexion, vérifier avant toute DML current_database/current_user/session_user,
inet_server_addr/port, TLS, PG180006, rôles ordinaires/non propriétaires sans
membership élevé, deadlines8s/1s/idle borné, search_path/timezone/date/float
déterministes, native014/P1 et journal réels. Le catalogue/OID/ACL source local
ne devient jamais une policy RDS. Le couple DNS/hostaddr/CA/acteur fait partie du
reçu d'opération ; un failover exige un nouveau preflight, pas un autre endpoint
essayé automatiquement. ROOT garde auth, pair, release, writes et readbacks.

## E2E et condition de suite

`FAILURE_MATRIX.json` est la spécification avant code : cas réels de CLI,
connexions protégées, vrai PG013/014, admission dérivée, anciennes versions,
cohortes, natifs31, lazy DTO et HTTP. Le petit `e2e.py` exécute actuellement la
vraie CLI absente et produit un RED unique ; les autres cas restent unverified.
Il ne remplace pas un harness PG/HTTP complet. La prochaine étape est de remplir
les readbacks manquants, finaliser les règles dérivées avec ROOT, puis écrire ce
harness exécutable avant le code de l'adaptateur et de l'admission.

Le résultat métier attendu est SQL RDS → API AWS → CloudFront → Vercel, sans
Neon/source/provider dans les requêtes runtime, avec HEAD/304, anciennes versions
et métriques comparables. Ce premier contrat ne couvre que les quatre readers ;
la parité des autres routes reste un chantier backend distinct.
