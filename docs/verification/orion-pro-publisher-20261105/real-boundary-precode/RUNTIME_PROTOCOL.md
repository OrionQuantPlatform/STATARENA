# E2E réel V1 — fonctions avant adaptateurs

Commit suggéré : `test: implement native admission and publication E2E before real adapters`.

Les31 fonctions R00–R30 sont implémentées dans `runtime_cases.py`. Leur contexte
concret est `runtime_context.py`, avec fixture typée indépendante
`runtime_fixture.py`, vrai CLI via `runtime_worker.py`, PG18.6/012013014 et vrai
serveur HTTP exportant les readers existants. Aucun adaptateur réel n'est encore
écrit. La présence des fonctions n'est pas un résultat de test.

Le défaut `python3 .../runtime_e2e.py` produit uniquement l'inventaire offline.
Il ne répète pas le RED CLI déjà conservé. Le mode `--run-owned` exige une
allocation ROOT séparée, fermée et hash-bound au runner/cas/contexte/fixture/
worker/helpers, à un commit réel et aux bornes exactes. L'allocation est consommée
une seule fois avant setup. Aucun RDS, RAM, provider ou source cloud n'est appelé.

Une qualification de **setup avant code** est prévue par
`--run-owned --qualify-setup-only` : pas de hash helper fabriqué, aucune fonction
R00–R30 exécutée. Elle construit une fois6 matchs/3éditions dans un PG privé,
avec drafts, engagements absents, participation inconnue, vrais natifs31 et
preuves de source synthétiques. Elle qualifie aussi5000tirs plus participations
en flux sans l'ancien cutoff5000, la clôture indépendante et l'identité TLS
du writer réel du test. Les31 cas restent unverified dans son reçu.

Les bornes **proposées, non encore allouées** sont600s absolues,6000SQL/200HTTP,
20000lignes totales,1GiB de disque possédé,96MiB de preuves,1PG/1API/2workers/
5connexions,1000lignes par batch/fetch. Le worker mesure les vrais fetches et
refuse un fetchall métier supérieur à1000. Ce ne sont pas des plafonds de
production. ROOT doit approuver les bornes après revue et qualification du setup.

Chaque enfant est un nouveau processus possédé. Les commandes setup/stop passent
par le helper de deadline qualifié ; les workers ont le même deadline partagé,
le SQL8s/lock1s/idle5s et une barrière bornée3s. Le watchdog annule le SQL et tue
seulement les enfants possédés. Premier échec inattendu : aucune autre fonction,
restauration de fixture ou relance de campagne ; nettoyage avec sa propre borne.
Les rapports incluent sources exactes, release, setup, fonctions, CLI, PG/HTTP,
fences, budgets, cleanup et échecs. Les séquences réelles sont lues par l'owner du
test, jamais demandées au writer comme privilège de production.

## Interface à implémenter après revue

Deux programmes distincts sont testés :
`dashboard/scripts/orion_pro_admit_real.py` (plan/apply des seules dérivations)
et `dashboard/scripts/orion_pro_publish_real.py` (plan/publish des produits).
Ils ont un défaut offline, une CLI help sans driver et des arguments explicites
`--environment`, `--mode`, `--input/--input-sha256`,
`--endpoint/--endpoint-sha256`, `--release/--release-sha256`, `--receipt`.
Le contrat de release/proof fixe le scope et les dépendances ; aucun DSN libre.

Le mode de qualification est **owned_local_tls** exclusivement. Son input kind
`orion_real_publication_owned_fixture_admission_v1`, son origine
`owned_source_free_fixture`, ses hashes de générateur et sa release
`real_publication_owned_operation_release_v1` sont distincts de la véritable
admission RDS définie par `ADMISSION.schema.json`. La même entrée offerte au mode
rds doit être rejetée avant driver. Le mode RDS ne réutilise jamais une
fixtureOnly, une identité/policy locale ou le commit local-owned-e2e-v1.

Le worker impose les vrais paramètres C libpq : host ET hostaddr littéraux
127.0.0.1, port/db/acteur/CA du marker privé, verify-full, délais et aucun DSN.
Les tentatives de driver sont enregistrées avant connexion, indépendamment de
la fence socket Python. Les cas PG*/DSN/CA/acteur doivent être refusés par la
frontière réelle **avant ce driver**. Le rôle writer actuel est réellement utilisé.
Le SQL publisher est limité aux5 sorties analytics ; celui d'admission aux
successeurs métier justifiés et contrôles existants. DELETE/DDL/grants/roles/
relaxation de délai sont refusés. Aucun oracle n'est importé par le produit.

L'input owned sépare `sourceInput` et `sourceInputEpochSha256` de `dataset`/
`catalogue`. Seule une génération du générateur de fixture avance l'époque source.
Un commit d'admission ou de publication ne devient pas sa propre nouvelle entrée.
Cela permet de vérifier un vrai no-op et la reprise COMMIT_ACK_UNKNOWN, sans
génération acceptée servant uniquement de transport/accusé de réception.

La fixture ne prétend pas avoir été produite par le normalizer réel4b98… : ses
lignes portent le vrai hash du générateur, son transform propre et le contrat
de test déclaré. La policy source porte le même nom réel pour vérifier que cette
chaîne seule n'est jamais une autorisation d'origine. Les facts réels du min-core
ne sont ni copiés ni altérés par ce test. Les valeurs nominatives sont synthétiques.

## Précisions issues du GET RAM unique autorisé

Le GET unique a qualifié l'inventaire de types/présence/identifiants/locators,
sans préserver de corps, noms ou valeurs scalaires sources. Il a établi612
chaînes `time_utc` non vides,9795 couples x/y numériques sans frame/unité dans les
partitions normalisées, et quatre acteurs non résolus dans la partition2025.
Le readback RO indépendant a ensuite confirmé que ces2 IDs joueur ne se résolvent
pas non plus dans le core fusionné ; les4 tirs typés ont player/profile=NULL.
Cela n'est jamais présenté comme une absence des IDs dans les sources/fournisseur.

La normalisation réelle conserve l'heure UTC exacte après validation de son
format/date/tz. Les coordonnées restent **non qualifiées** : aucune conversion
en mètres ni acting_ltr inféré. Un DTO V1 coordinate_state=unknown ne constitue
pas un NULL effectivement observé ; l'admission nomme cette limite et conserve
ses témoins/hash source. Les champs réellement absents tels que body_part/outcome
dans ces partitions peuvent rester absents/inconnus selon le contrat établi.
Une déclaration `observed_null` substituée à des x/y disponibles mais non qualifiés
doit être refusée. Les coordonnées sources restent conservées par le chantier
données tant que leur intégration n'est pas qualifiée ; aucun nettoyage n'est autorisé.

Ces précisions actualisent la spécification initiale de R18 **avant code** et
sans changer les tests historiques du publisher synthétique. Les versions
initiales de la matrice/contrat restent dans les inputs du premier RED et leur
manifest19fichiers ; aucune preuve antérieure n'est réécrite.

Les schémas/provenances/acteurs réels et la reprise minimale ne sont qualifiés
qu'après l'exécution de leurs oracles. Ce harness source-free n'est pas une
preuve d'admission RDS ni de backend complet.
