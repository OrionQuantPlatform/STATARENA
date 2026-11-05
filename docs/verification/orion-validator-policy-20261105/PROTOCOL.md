# Protocole proposé — adoption de la politique P1

**Aucun E2E, SQL apply, connexion ou nouveau budget de campagne n'est autorisé/consommé par ce document.** Les seuls contrôles effectués dans ce lot sont des lectures et comparaisons statiques, consignées dans [static-review.json](static-review.json). Les tests ci-dessous doivent précéder le futur code d'adoption ; leurs résultats ne sont pas présumés verts.

Le [PLAN](PLAN.md) fixe M0/P0 →M0/P1 et sépare107PENDING. Le futur runner est plan/offline par défaut ; un mode RO ne doit pas appeler le mode apply. Les vieux runners/compilateurs et leurs gardes restent inchangés.

## Matrice E2E avant implémentation

| Cas complet à construire | Résultat observable attendu |
|---|---|
| Runner/helper nouveau absent | Vrai RED conservé, sans connexion, corps source ou faux reçu de succès |
| Plan offline, environnement contenant des variables cloud/DSN | Zéro accès env secret/service/client DB ; manifeste/code/SQL/hashes affichés sans credentials ; aucun fichier012/013 réécrit |
| P0 exact →P1 sur B0 local | Uniquement un corps de fonction modifié et une ligne014 ajoutée ;94 tables/1709 colonnes/431 FK, dix seeds/deux contrats/snapshot B0, toutes séquences et publications inchangés |
| M0 ou012/013/générateur/fonction/manifest/acceptation altéré d'un octet | Refus avant DDL, et zéro mutation/nextval |
| M0 modèle NOTNULL mais catalogue nullable, ou inverse | Refus explicite ; ne pas «réparer» la nullabilité |
| Corps P1 sans014 ou014 avecP0 | Refus de dérive, pas adoption opportuniste ni réécriture de journal |
| Journal014 inconnu, checksum différent, numéro occupé, autre version présente | Refus ; aucun numéro choisi automatiquement |
| Modèle107 proposé, absent d'approbation | Refus séparé, même si le nom de fonction est identique ou le patch semble additif |
| Remplacement exact139/46 | Inversion octet exacte versP0 ;81 clauses ; chaque paire liée à sa colonne/FK et au catalogue ; aucune comparaison globale changée |
| Position NULL/NULL, équipes/provenance correctes | Admit commeP0 ; position reste null-safe |
| Parent clos, mauvaise équipe, position NULL/nonNULL, noncanonical ou deleted | Mêmes23514 et FK de membership queP0, pas un23503 prématuré qui masquerait la règle |
| Ancres physiques/provider faux | Mêmes23503 natifs, séparés des cas sémantiques |
| Génération historique sélectionnée avant une correction | Même membership historique, sans appeler directement le validateur transactionnel sur un snapshot étranger |
| DB synthétique peuplée locale, valeurs précises et états natifs | Oracle SQL natif de toutes94 relations, valeurs métier inchangées. Ne pas décoder JSONB via float ; SQL NULL/JSON null, nombre précis, tableau/texte, zero/false/empty/Unicode/timestamps exacts |
| Propriétés de fonction ou grants altérés avant adoption | Refus, aucun ALTER OWNER/REVOKE/GRANT correctif automatique |
| OID/owner/ACL/procprops avant/après | OID et propriétés inchangés dans la même DB ; seule définition attendue varie ; effective privileges et default privileges inclus dans l'oracle de sécurité |
| Ingest/runtime essaient l'upgrade ou le journal | Refus42501 ; le propriétaire existant seul applique ; aucun rôle élevé ou nouveau grant |
| Migration/génération lease déjà tenue, écrivain concurrent ou activité inconnue | Refus/lock timeout≤1s, aucun kill de session ni attente prolongée ; zéro changement |
| Faute après remplacement mais avant INSERT journal, puis faute avant commit | Rollback réel : P0 et journal initial, séquences/seeds/faits inchangés. Rerun ensuite une fois, sans doublon |
| Accusé de COMMIT interrompu | Reconnexion RO classe P0 ouP1 avec journal exact ; aucune relance aveugle ; état mixte refusé |
| Réapplication P1 exacte | No-op : pas DDL, ligne journal, génération, nextval ou nouveau hash B0 |
| Bootstrap dont le hash migrateur est historique | Comparé à B0 exact, pas au nouveau code d'upgrade ; ancienne preuve reste attribuée à son commit et ses octets |
| Réexécution d'un ancien guard sur cible014 | Refus attendu «version non supportée» ; ne pas changer le vieux test pour accepterP1 et ne pas déclarer son ancien vert comme un vert actuel |
| Compensation après commit P1/M0 exact | Nouvelle version de journal, retour au corpsP0 exact ;014 conservé ; métadonnées/faits inchangés ; no-op de compensation qualifié |
| Compensation après autre politique ouM1 | Refus ; aucun retrait des règles nouvelles sous prétexte de revenir à013 |
| Futur streamer sourceP0/cibleP1 | Seul couple explicitement qualifié admis, diff catalogue exactement borné ; source/acceptation/phase/generation/snapshot/transform exacts. Bulk v1 gelé refuse toujours |
| Reprise après une phase avec politique changée | Refus jusqu'à acceptation explicite de la nouvelle paire ; aucune modification d'ancien reçu/import_runs scellé |
| Fixture dense478547 canonical,15,437×31,612matches | Source setup, plan ciblé, seal et deferred commit séparés ; pas de variantes artificielles pour simuler la densité |
| Seal oucommit>8s, tempfiles/disk/metadata/buffer au plafond | Conserver RED et arrêter la campagne. Pas hausse de bornes, index ajouté, split de génération ou deuxième grand start implicite |
| Cleanup et gel | Toutes connexions fermées, deux DB/PG détenus supprimés, commandes/inputs/logs/erreurs/hashes et zéro action distante dans chaque reçu |

La preuve locale9/9 actuelle qualifie l'équivalence du candidat ; elle ne couvre pas ce nouveau runner, son journal, ses refus et sa compensation. Les temps existants sont réutilisés comme contexte, jamais comme résultat de cette matrice non exécutée.

## Oracle et empreintes

L'oracle indépendant compare des lignes natives/canoniques SQL avec framing et ordre PK exacts, pas les objets Python du producteur. Le journal attendu change seulement par ajout de014, puis éventuellement de la compensation. Les clocks/code_commit des **nouvelles** lignes de migration sont capturés avec le commit de release ; les anciennes lignes ne changent pas. Aucune tolérance de timestamps des faits ou du bootstrap existant.

Pour deux installations locales distinctes, les différences d'installation autorisées restent énumérées : clocks d'installation du journal/bootstrap, txid/xmin, OID locaux et mappings génération/snapshot explicitement attestés. Ces différences ne sont pas des exemptions au comparateur avant/après d'une même cible. La politique n'a aucune raison de consommer une génération ni une séquence. Ne pas exiger le même owner local queRDS ; vérifier le propriétaire approuvé de chaque cible et conserver ce propriétaire pendant son upgrade.

Produire un catalogue attendu **P1 nouveau** depuis une préparation locale B0 exacte puis014 réelle ; ne pas modifier l'ancien `expected-catalogue.json`. Les fingerprints distinguent : faits/structure inchangés, ensemble complet fonctions/triggers/propriétés, chaîne de migrations, B0 et manifeste de politique. On peut composer un diff autorisé explicite ; on ne supprime pas toutes les fonctions du hash.

Les preuves historiques continuent d'être vérifiables par leurs snapshots et le code à leur commit. Un chargeur futur de preuves doit lire le manifeste historique exact et ses sources capturées, puis un reçu de transition séparé ; pas remplacer «sources historiques» par «sources du HEAD» ni éditer `rds_catalogue.load_expected()` pour accepter arbitrairement les deux.

## Budget local proposé — nouvelle autorisation nécessaire

| Phase | Proposition bornée |
|---|---|
| Revue statique actuelle | Aucune connexion ;0 SQL/HTTP/AWS/Neon/Pitch ; artefacts de ce dossier≤1MiB ; aucune nouvelle campagne |
| Futur E2E compact d'adoption/compensation/refus | Une exécution≤10min, deux DB d'un PG détenu ; garde8s/instruction, lock1s ; RED puis code selon le protocole |
| Futur grand gate d'adoption | **Un** start dense≤20min, nouvelle ledger ;478547scalars15437×31, pas répétition routinière de baseline8s ; aucune tentative additionnelle implicite |
| Total proposé |≤30min ; owned PG8GiB, stop doux7GiB ; temp_file_limit512MiB/backend ; metadata32MiB, buffers16MiB ; preuves64MiB ; row/chunk/phase/sequence caps v1 inchangés |
| Mesures | Bytes metadata/graphes et buffers réels bornés, disque PG et workfiles/EXPLAIN, setup et coûts COPY/oracle/seal/commit séparés ; pas les confondre avec RSS/latence WAN |
| Arrêt | Premier autre setup/DDL/oracle/8s/borne échoué : receipt+cleanup, diagnostic ROOT avant toute relance. Les campagnes précédentes restent épuisées et inchangées |

Ce budget est **proposé, non accordé et non consommé**. Le dense9/9 déjà figé ne doit pas être rejoué simplement pour alimenter cette proposition. Un second start ne serait demandé qu'en réponse à un diagnostic concret et dans une campagne explicitement autorisée.

## Futur RDS : revue, application et readback distincts

L'adoption sémantiquement équivalente sur M0 ne dépend pas de107. Elle exige néanmoins sa nouvelle acceptation ROOT/release, la validation locale du runner puis un préflight RO frais. Les reçus schema/bootstrap d'origine ne l'autorisent pas. Aucun accès distant n'est fait ni autorisé ici.

Première cible proposée : B0 exact et bootstrap seul. Un readback RO utilise TLS verify-full avec CA/identité fixes, rôle ordinaire, repeatable-read,8s/instruction,lock1s et connect≤7s ; ni SSM retrieval ni paramètres secrets copiés dans les preuves. Les vérifications de propriétaire et de l'absence de privilèges runtime doivent aussi être effectives, pas limitées au texte des ACL.

Budget **à approuver séparément** : au plus16SELECT de métadonnées,20 instructions SQL totales en comptant BEGIN/SET/COMMIT,4MiB résultats décodés ; stop avant fetch si une réponse annoncée dépasse la borne. Réutiliser les cinq groupes de catalogue dans un nouvel oracle P1 plus identité/journal/B0/seeds/contrats/absence métier/procprops/permissions/publication/séquences ; grouper les lectures prévisibles plutôt qu'ajouter un aller-retour par colonne. Les rôles source/legacy ne sont pas lus au niveau des corps ; seules leurs métadonnées déjà requises peuvent être observées. Un dépassement reste non vérifié, jamais une lecture tronquée décrite complète.

L'application future, si autorisée, a son propre budget explicite et une seule transaction : préconditions RO d'abord, propriétaire existant, verrous migration/génération, corps P1 + ligne014, vérifications puis commit. Ne pas appliquer les délais60s du vieux bootstrap par héritage :8s/1s restent le contrat de cet upgrade. Un refus d'ownership ne conduit pas à un nouveau grant/admin. Le readback indépendant après commit lie réception/commit/model/policy/SQL et confirme B0 ; les namespaces/métadonnées legacy observés ne prouvent pas l'égalité de leurs corps. Aucun chemin d'écriture source, import ou génération de benchmark n'est admis.

Un futur benchmark RDS de seal sur données est une autorisation **différente** : le readback metadata ne prouve pas le coût d'une génération remplie. La0.5M locale et5.6s ne qualifient pas la micro-instance ni l'univers complet. Avant tout import réel, ROOT doit disposer du contrat source/acceptance et d'un plan de capacité réel ; si le validateur global dépasse8s, arrêter sans changer les garanties. La capture/source drift, le streamer, les nouvelles publications,107, le cutover et la purge restent des lots séparés.

Suggested commit: `docs: define append-only validator policy adoption and rollback`.
