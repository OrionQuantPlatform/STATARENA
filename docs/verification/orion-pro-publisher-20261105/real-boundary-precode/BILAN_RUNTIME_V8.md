# Qualification locale des adaptateurs natifs — 5 novembre 2026

Commit suggéré : `feat: qualify native Pro admission and immutable SQL publication`.

La campagne owned source-free V8 passe **31/31 cas** dans leur version3 revue par ROOT. Le publisher synthétique V1 antérieur reste qualifié séparément30/30. Ces résultats ne qualifient ni une admission RDS positive ni le backend entier. Aucune production, infrastructure, donnée réelle RDS, source cloud ou RAM n'a été appelée par la campagne.

Les fichiers produit qualifiés sont :

- `dashboard/scripts/orion_pro_admit_real.py` : `0030eae7d08464ef3b9ebfdfe6485ab8db8aa1b1c732bf1d4629ce301b404fd0`.
- `dashboard/scripts/orion_pro_publish_real.py` : `6b6cd2ffd380d298429744a94cb0f587c653a990579518af2af4f2b90c80e38c`.

Le commit `7f3d4e692e8980bdedf72eb5793d40a7697c6df5` est explicitement un **ownedBaseCommit**. Les nouveaux bytes de helpers ne sont pas présumés présents dans ce commit ; leur SHA réel est enregistré séparément. Une release RDS devra épingler les helpers effectivement committés.

## Preuve finale

`runtime-runs/20261105T143528215642Z-owned-real-publisher-runtime-v8-tls-reconnect/result.json` :
`f7b16b926e593f1c1e2207a5e3f089940e0d5d433c7960cb589a8917b74ea36b`.

| Mesure | Observé |
| --- | ---: |
| Cas de la version revue |31 PASS,0 FAIL,0 unverified|
| Durée, nettoyage inclus |104.855s|
| SQL réservés / commandes client serveur |7301 /7301|
| Répartition SQL owner / publisher / admission / API |5662 /942 /514 /183|
| HTTP |87 :69×200,5×404,13×304|
| Invocations CLI consignées |109|
| Fetch/batch natif maximal observé |1000 lignes|
| Dernier scope sélectionné dans le plan |5198 lignes|
| Disque PG possédé maximal échantillonné |75530240 octets|
| Preuves maximales échantillonnées pendant le run |26786280 octets|
| Preuves du run après émission du résultat |34006444 octets|
| Source RAM / cloud / RDS business writes |0 /0 /0|
| Sources de code modifiées pendant le run |0|
| Nettoyage serveur / API / workers / dossier possédé |4/4 vérifiés|

Les bornes allouées sont600s cumulées pour V7+V8,15000SQL,200HTTP,20000 lignes typées,1GiB de disque possédé,96MiB de preuves,5connexions/2workers,1000lignes par fetch/batch. V7+V8 ont observé193.320s au total. Le deadline V8 partagé était491s, avec20s réservées au nettoyage. L'augmentation interne6000→15000SQL est une correction de budget de qualification ; elle n'est pas présentée comme une optimisation produit. Les anciens champs hérités `generations=24`/`builds=20` du fichier de compteurs V1 ne sont pas les bornes de cette allocation réelle ; seuls les champs explicitement alloués ci-dessus définissent cette campagne.

Avant les dérivations :384 lignes natives physiques consignées,6matchs draft/3éditions,124slots natifs31 pour4observations,0build/summary/publication. La fixture ajoute ensuite5000tirs complets sur5matchs, en conservant les familles source/variant indépendantes et un6e match réellement inconnu. Le dernier état complet natif sauvegardé avant le crash R23 contient5495 lignes physiques ; aucun comptage final supplémentaire n'est inventé après destruction du PG.

La première publication native a créé3READY/6match summaries/3competition summaries et3pointeurs, pair effectif31/31, génération de publication32. Les événements après COMMIT READY consignent les IDs durables1,2,3,5,6,7,8,9,10. Le dernier no-op demandé à43/43 conserve les builds actifs6/10/9, avec paires effectives35/35,42/42 et39/39. Le trou d'identité4 correspond au crash natif contrôlé ; il n'est pas une ligne READY.

Les dérivations ont exercé les engagements observés par cohorte exacte, `played=True` uniquement avec preuve positive, les inconnus, les labels du même ID, les priorités de profil, BIGINT9007199254740993/Decimal exact, scores absents/NULL/observés et shootout séparé, UTC connu/inconnu, coverage PK/source/variant/IDs et coordonnées non qualifiées. Les natifs31 ne sont jamais réécrits par les helpers ; leurs corrections de fixture sont explicitement des successeurs source et ne sont pas confondues avec les écritures produit.

Les READY natifs, l'orphan reuse, les crashes, les deux workers concurrents, l'activation atomique, le hook sans verrou global, le recheck d'entrée modifiée, les deux no-op avec67séquences inchangées et les deux COMMIT_ACK_UNKNOWN suivis d'une reprise sans écriture ont été exercés. Les privilèges réels ont refusé DELETE dirty/direct validate/nextval commitseq/runtime UPDATE avec42501. Les trois démarrages API incluent chacun8calibrations négatives et une reconnexion réelle du pool sous fence, identité runtime/readonly/8s/1s inchangée et SSL natif true. Les anciens pins HTTP restent identiques après corrections ; HEAD/304 restent metadata-only. Les environnements provider/Neon empoisonnés n'ont déclenché aucun accès source.

## Corrections du précode conservées et revues

Les cas originaux `runtime_cases.py` SHA `b3844c7e6bd4f0fb98df69e72fed32a95484cb0d2df69a92a7ab6dbc62570db0` sont inchangés. La version2 conserve les30autres fonctions et corrige seulement R13 après revue ROOT : deux gagnants de même rang sont interdits par l'unicité native `(acteur,profile_context)` et les intervalles historiques. R13 exige maintenant23505 sur l'index exact `football_team_profile_versions_sv_canonical_current_idx`, rollback et clôture/plan inchangés. Les4priorités positives sont conservées. La branche défensive produit `PROFILE_AMBIGUOUS` reste **UNEXERCISED**.

La version3 corrige seulement le premier contrôle de rollback R23, après revue ROOT : les94tables et66autres séquences restent exactes ; l'identité build doit avancer de la liste contiguë exacte des IDs alloués, jusqu'à son maximum. Les deux états sont persistés avant assertion. V8 confirme réellement94tables identiques et le seul écart buildseq3→4 pour l'événement[4]. R25/R26 continuent d'exiger les67séquences identiques sur chaque no-op. Les autres attentes ne sont pas affaiblies.

Les défauts de fixture/harness et tous leurs reçus restent conservés :

| Tentative | Résultat réel et cause |
| --- | --- |
| SetupV1 |Échec avant PG : archivage d'un chemin release relatif.|
| SetupV2 |Échec natif : canonical_policy_version requis absent du volume shots.|
| SetupV3 |Échec seal : fermeture indue des variantes non canoniques indépendantes.|
| SetupV4 |Setup PASS,31cas applicatifs non exécutés.|
| RuntimeV1 |R00 : import voisin sous Python-I.|
| RuntimeV2 |13cas PASS ; profil courant non canonique réinséré avec même clé.|
| RuntimeV3 |13cas PASS ; attente R13 impossible avec les contraintes canoniques natives.|
| RuntimeV4 |14cas PASS ; SET CONSTRAINTS avant seal déclenchait le commit guard ouvert.|
| RuntimeV5 |21cas PASS et publication native exécutée ; export API sans nouveaux modules locaux.|
| RuntimeV6 |23cas PASS ; attente R23 sur rollback des67séquences invalide.|
| RuntimeV7 |25cas PASS ; reconnexion TLS locale Bun rejetée par la fence du harness.|
| RuntimeV8 |31cas de la version revue PASS.|

Les défauts d'export concernent seulement les snapshots de test. Le graphe final copie exactement18fichiers(app+17services) et aucune bibliothèque provider. La correction TLS normalise la signature Bun réellement reproduite, accepte TCP sur l'unique peer possédé et un upgrade TLS sur un vrai Socket déjà connecté au même peer ; les cibles étrangères/faux sockets restent refusés. Aucun reader, schéma, grant ou guard n'a été relaxé.

## Reproduction et conservation

Commande exacte exécutée, sous allocation ROOT consommée une seule fois :

```sh
PYTHONPATH=/tmp/statarena-publication-test-python \
ORION_E2E_PG_BIN=/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin \
python3 docs/verification/orion-pro-publisher-20261105/real-boundary-precode/runtime_e2e.py \
  --run-owned --remaining-seconds 491 \
  --release '/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/docs/verification/orion-pro-publisher-20261105/real-boundary-precode/ROOT_RUNTIME_RELEASE_V8.json' \
  --release-sha256 3f80b427ccd69187920a62cc77f9f4ced4416bb873e2ee8cd28aa7e0e1b8773c \
  --label owned-real-publisher-runtime-v8-tls-reconnect
```

La release est expirante et consommée : une reproduction opérationnelle requiert une **nouvelle allocation/release ROOT**, sans supprimer/reset l'ancien reçu ou ledger. Le run archive les inputs exacts ; les commandes initdb/TLS/start/stop, traces SQL main/workers/API, fetches, événements de phases, contrôles R13/R23, HTTP et résultats sont inspectables. `PRESERVATION_AFTER_RUNTIME_V8.json` confirme les101qualifiés+13copies exactes+148preuves antérieures+20statiques inchangés. `CLEANUP_READBACK_RUNTIME_V8.json` confirme l'arrêt pg_ctl0, l'absence du dossier possédé et de processus restants, sans ouvrir de connexion PG supplémentaire.

## Limite et suite réelle

La qualification positive RDS reste **false**. `REAL_HANDOFF_BOUNDARY.md` décrit les prérequis UTC/acteurs/labels/coordonnées et la conservation RAM→typedSQL sans copie sportive JSON. Une frontière REALRDSv2 séparée doit d'abord qualifier : adresse C hostaddr distincte de l'inet serveur NAT relu par ROOT ; digests sémantiques native91/31 et contrôles3 distincts des hashes de fichiers reçus ; reçu/stdout RDS limité aux clés/counts/digests au lieu des `matchProducts` utilisés par la fixture ; chaîne015/politique cible explicite. Aucun de ces points n'est couvert par une affirmation d'admission RDS ou de backend terminé. Les bytes0030/6b6 qualifiés localement restent gelés avant les contrats/tests de cette version2.
