# Adoption versionnée du validateur de cohortes

Statut : **proposition statique, aucune application ni nouvelle campagne**. Ce lot ne contient aucun SQL exécutable, migrateur, helper produit ou test. Le candidat local [9/9](../orion-validator-membership-20261105/RESULTS.md) reste gelé. Les écritures de ce lot sont limitées à ce nouveau dossier.

Décision proposée : adopter l'unique fonction optimisée par une migration append-only **014**, si ROOT confirme que ce numéro est libre, sur le modèle103 actuel `18da43…`. Cette optimisation sémantiquement équivalente relève du périmètre optimisations déjà autorisé ; elle **n'attend pas107**. La proposition107 reste PENDING et exige son approbation et ses migrations propres. Aucun accord pour appliquer014 ou107 n'est émis par ce document.

## Pourquoi un chemin distinct est nécessaire

| Chemin actuel lu | Comportement établi | Conséquence pour l'adoption |
|---|---|---|
| [orion_pro_migrate.py:25](../../../dashboard/scripts/orion_pro_migrate.py#L25), lignes25–35 | `compiled_migrations()` produit012/013 puis réécrit leurs fichiers si les octets diffèrent | Ne pas modifier le compilateur par défaut ni l'appeler pour produire014 |
| [orion_pro_migrate.py:38](../../../dashboard/scripts/orion_pro_migrate.py#L38), lignes38–68 | Bootstrap indexé par le hash du modèle ; bundle comprenant modèle, migrateur et012/013 ; seeds/manifest liés à ce bundle | Conserver le bundle d'installation original. Ne pas le recalculer avec un nouveau runner ou avec014 |
| [orion_pro_migrate.py:147](../../../dashboard/scripts/orion_pro_migrate.py#L147), lignes147–162 | Un hash journalisé différent est refusé ; le runner ne connaît que012/013 | Ajouter un chemin d'upgrade séparé, sans élargir les anciens gardes |
| [orion_pro_rds.py:152](../../../dashboard/scripts/orion_pro_rds.py#L152), lignes152–200 et222–260 | L'acceptation lie les octets du code courant ; la cible autorisée est absente ou journal exact012/013 et bootstrap seul | Ne pas réutiliser cette acceptation pour une fonction nouvelle ; prévoir un scope d'upgrade explicite |
| [rds_catalogue.py:108](../orion-pro-pilot-20261104/rds_catalogue.py#L108), lignes108–119 | L'oracle attendu exige les hashes des sources courantes | Garder cet oracle historique. Construire un nouvel oracle par politique, sans changer son ancien chargeur |
| [rds_readback.py:75](../orion-pro-pilot-20261104/rds_readback.py#L75), lignes75–87 et123–145 | Journal à deux versions, corps de fonctions exacts et bootstrap recalculé avec le migrateur courant | Après014, ce vieux readback doit refuser la cible actuelle ; son ancien reçu reste valide pour son instant/commit |
| [orion_pro_bulk.py:150](../../../dashboard/scripts/orion_pro_bulk.py#L150), lignes150–171,246–269 et342–343 | Le catalogue inclut définition/owner/ACL des fonctions ; bootstrap et journal012/013 sont stricts ; source et cible doivent avoir le même catalogue | Bulk v1 doit continuer à refuser une cible014. Un futur streamer doit déclarer la paire de politiques compatible et vérifier son delta exact |
| [orion_pro_schema.py:59](../../../dashboard/scripts/orion_pro_schema.py#L59), lignes59–110 | L'approbation initiale et l'amendement borné de huit chemins autorisent18da seulement | Aucune tolérance pour le patch107, aucun remplacement silencieux du modèle approuvé |

Ces constats sont des lectures de source, pas de nouveaux tests PostgreSQL. Les empreintes exactes figurent dans [inputs.json](inputs.json).

## Trois identités distinctes

1. **Modèle physique M0** : SHA256 `18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08`,103 définitions dont94 tables actives,1709 colonnes actives et431 FK. Il reste inchangé.
2. **Installation B0** :012 `f255868599c72d69f40f575a919045325ea1093a00fe4f5a6b96eae9f2c49f65`,013 `85525221cad51b32aff79a777098211b4112f9f00ea7161ac93945654eeb6968`, migrateur `d9bdf60ef48a527276499fedb82a435c26b42653432d3a1a3c94cc2db02ee2dd`. Le reçu RDS historique lie ce bundle à `codeSha256=379ef1e6d9efe2e5ec9a4c78779892d9dda68015c4f91ec8e95a18990864e08f`, dix seeds et un bootstrap scellé g1 ; manifest `2158706bd7c2ee638b6b178c2b45cc673755b315fdd5f1e846d60567650e9c88`. Ce sont des observations du reçu, pas un nouveau readback distant.
3. **Politique d'exécution P0/P1** : même modèle M0, une seule fonction différente. P0 correspond à013 original ; P1 à `membership-nonnull-m18da43-v1`. La politique et son manifeste ont leur propre hash ; ils ne deviennent ni un nouveau hash du modèle ni un nouveau transform du bootstrap.

Le journal existant `ingest.schema_migrations` reste le registre de migrations. Aucun registre ou colonne de politique supplémentaire n'est nécessaire. Un manifeste immuable hors DB associe une chaîne de versions/hashes exacte à une politique ; le runner vérifie aussi le corps réel. **Le journal seul ne prouve pas la politique active** : un remplacement hors journal, même identique au candidat, est une dérive à refuser dans le premier outil.

## Chemins proposés, à créer seulement après revue

| Futur artefact | Contrat |
|---|---|
| `dashboard/backend/schema-policies/orion-pro/m18da43-p013-original-v1.json` | Manifest B0/P0, modèle et approbation/amendement historiques, hashes012/013/migrateur, bundle bootstrap, extraction de la fonction originale, oracle catalogue initial |
| `dashboard/backend/schema-policies/orion-pro/m18da43-p014-membership-nonnull-v1.json` | Parent exact P0, migration014, modèle M0, fonction P1, preuve139/46 et nullabilité, propriétés de routine, hashes de code/E2E/oracle après adoption ; acceptation extérieure séparée |
| `dashboard/backend/migrations/014_orion_pro_membership_nonnull.sql` | Une seule définition de `ingest.validate_generation(bigint)` ; aucun bootstrap, trigger, index, rôle, table, seed, grant ou donnée métier. Hash du fichier complet à sceller plus tard |
| `dashboard/scripts/orion_pro_policy.py` et `orion_pro_upgrade.py` | Nouveaux modules proposés : sélection fermée du manifeste et upgrade append-only. Plan hors ligne par défaut ; read-only explicite ensuite ; apply explicite et lié à l'acceptation ROOT |
| Nouveau namespace de preuves d'adoption | Source snapshots, RED avant code, SQL réellement appliqué, chaines de journaux, catalogue et reçu indépendant après commit. Aucun ancien reçu écrasé |

Les noms014 sont proposés sous allocation ROOT, sans fichier créé ici. Une collision de numéro ou un journal hors chaîne est un refus ; on ne recherche pas automatiquement « le prochain numéro libre » pendant une application. Le hash du manifeste de release doit être fourni à l'outil ; aucun pointeur mutable `latest` ne décide de l'application. Un manifeste indique le hash de son parent et des artefacts externes, pas son propre hash ni celui d'un reçu qui le référence : éviter les cycles d'empreintes. L'acceptation ROOT et les reçus d'exécution sont des artefacts séparés qui le lient.

Contrat de manifeste proposé, schéma fermé : `kind=orion_pro_validator_policy_v1`, `policyId`, `model={path,sha256}`, `baseline={manifestPath,manifestSha256,bootstrapArtifact,bootstrapArtifactSha256,bootstrapManifestSha256}`, `parent={policyId,path,sha256}`, `migrationChain=[{version,path,sha256}]`, `function={identity,sqlSha256,prosrcSha256,normalizedDefinitionSha256,properties}`, `equivalence={clauseCount,changedComparisons,retainedComparisons,proofPath,proofSha256}`, `expectedCatalogue={path,sha256}`, `implementationSources={path:sha256}` et `qualifiedImportPairs`. Les hashes de catalogue/prosrc/propriétés seront calculés par la future préparation locale, jamais inventés ici. `properties` contient les valeurs natives/symboliques énumérées ci-dessous ; les OID et propriétaires cibles sont attestés séparément. L'acceptation extérieure lie le hash de ce manifeste, le commit qui le contient et les preuves ; ne pas mettre le hash du commit contenant le manifeste dans le manifeste lui-même. Le manifeste B0 n'a pas de parent ; aucun champ inconnu n'est accepté par défaut.

Ordre des artefacts pour éviter aussi un cycle oracle/manifeste : figer code et SQL ; préparer l'oracle attendu avec ces hashes etB0, **sans hash du futur manifeste** ; créer le manifeste qui lie cet oracle ; exécuter les nouveaux E2E avec ce manifeste ; créer l'acceptation extérieure qui lie ces reçus et le manifeste. Le manifeste ne contient pas le hash des E2E d'adoption qui le prennent comme input. Son `equivalence.proofSha256` peut viser le9/9 historique déjà indépendant, accompagné du contrôle statique exact des octets de release.

Le nouveau runner lit les octets scellés012/013 pour vérifier B0 ; il ne les régénère ni ne les réexécute lors d'un upgrade. Pour une installation neuve, l'étape B0 utilise les outils/artefacts historiques exacts, puis un upgrade distinct vers P1. Le nouveau runner ne prend jamais la place du migrateur dans `B0.artifact`. Aucun changement des sources anciennes n'est nécessaire pour adopter P1.

## Garde de fonction exacte

| Empreinte | Valeur actuelle qualifiée |
|---|---|
| Fonction P0 extraite de013, sans REVOKE ni saut de ligne ajouté | `246af203d171f286b3760ccdc67b579dbce967b5f209e3fb0825bc00b9211eaa` |
| Fonction P1 : chaîne SQL effectivement exécutée dans le9/9 | `30f86fa262fd4cf10307e78431350f25b9d7a5b353d0c76abc0594340edb5d20` |
| Fichier `candidate.sql`, même définition avec saut de ligne final | `e0810f8670b2cb627ade2c76e3c8eb527ab31fd595d5cf939fd63bfc5cf649d6` |
| Générateur candidat gelé | `357b9feb06f486593fd4b9c34c03a740319b59ad38871c50025fd76ef2bca8ae` |
| Reçu9/9 gelé | `925cf8676d99e18617d711c1a56140eceed84450adc351f23f90af5aef23866f` |

Le futur hash du **fichier014 complet** sera distinct de celui de la fonction. Ne pas lui attribuer par anticipation un de ces hashes. `pg_get_functiondef` est une sérialisation du catalogue PostgreSQL, distincte du fichier SQL ; son empreinte attendue proviendra de la préparation locale du nouvel oracle. Comparer également `prosrc` et les propriétés natives, sans normalisation générique de SQL.

Avant de produire014, le contrôle hors ligne reconstruit P1 depuis013 exact et M0 exact, puis démontre l'inversion octet pour octet vers P0 :81 clauses,139 substitutions ciblées en `=`,46 comparaisons nullables conservées. Chacune est identifiée par relation enfant/FK/parent/colonne, pas par remplacement global de `_equal`. Les deux opérandes sont des alias de la même colonne parent, donc `=` et `IS NOT DISTINCT FROM` sont équivalents lorsque sa déclaration NOTNULL est vraie pour les deux. La preuve doit être vraie dans le modèle **et** dans les1709 déclarations du catalogue cible. Une seule nullabilité divergente fait refuser l'adoption.

Tous les autres octets de la fonction restent identiques : génération, `xmin`, verrou, intervalles, canonical/deleted, ancres physiques, provenance et messages d'erreur. En particulier `match_players.position_code` reste nullable et null-safe ; match_id/player_id/team_id utilisent `=`. Ne pas changer globalement `_equal`, la sélection temporelle ou une comparaison de valeurs.

La définition est remplacée en conservant signature/OID/owner/ACL. Vérifier avant/après : schéma et identité `g bigint`, type résultat void, langage plpgsql, prokind, modes/noms/types/defaults d'arguments, security-definer, search_path exact `pg_catalog`, strictness, volatility, parallel-safety, leakproof, support/transform/bin/sqlbody, cost/rows, commentaire, ACL effective et brute. Les OID/owners sont comparés au sein de chaque cible ; ne pas exiger le même OID/nom de propriétaire entre une DB locale et RDS. Les noms de rôles attendus restent ceux de la cible approuvée.

PostgreSQL conserve owner et permissions lors d'un remplacement ; les autres propriétés sont celles indiquées ou implicites dans la commande. Cela impose une comparaison explicite, même si le candidat local a conservé ses propriétés. Aucun DROP/CREATE, ALTER OWNER ou réapplication globale de grants n'est admis. [CREATE FUNCTION PG18](https://www.postgresql.org/docs/18/sql-createfunction.html), [catalogue pg_proc](https://www.postgresql.org/docs/18/catalog-pg-proc.html).

## Transition contrôlée P0 → P1

Première livraison proposée : **upgrade d'une installation B0 bootstrap-only exacte**. Si de vraies données ont été importées entre-temps, arrêter ce mode et faire revoir un contrat de cible peuplée ; ne pas improviser une exemption. Le workflow local inclut néanmoins une DB peuplée synthétique pour démontrer l'absence d'effet sur les faits, sans en faire une permission RDS plus large.

1. Plan offline : vérifier manifeste, code/SQL/approbation, parent P0, allocation014, neuf contrôles locaux existants et nouvelles preuves d'adoption. N'effectuer ni connexion, génération SQL écrite ailleurs, commande AWS ni collecte. Aucune acceptation historique n'autorise cet upgrade par simple réemploi.
2. Préflight RO frais : identité cible/engine/TLS/rôle, journal exact012/013, fonction P0 exacte,94 tables/1709 colonnes/431 FK, nullabilité, tous les autres objets, permissions, dix seeds/deux contrats et B0 exacts. Pas de scan de corps legacy ; ne lire que les métadonnées prévues. Toute présence métier dans les nouveaux schémas refuse ce premier mode.
3. Application explicite après revue ROOT : une transaction du propriétaire actuel de la fonction, sans nouveau rôle/admin accordé. Délais8s par instruction/1s pour les verrous ; verrous coopératifs migration `(20261104,2)` puis génération `(20261104,1)` avant relecture des préconditions. Aucun début de génération ni publication. Vérifier aussi la quiescence/les transactions d'écrivains suivant le gate courant ; ne pas terminer des sessions pour obtenir le verrou. Les verrous transactionnels sont relâchés à la fin. [Verrous consultatifs PG18](https://www.postgresql.org/docs/18/functions-admin.html#FUNCTIONS-ADVISORY-LOCKS).
4. Revalider P0/journal/propriétés/manifestes sous les verrous. Appliquer uniquement P1 puis ajouter014 et son hash au journal avec le commit de release. Revalider corps/propriétés/autres objets et B0 dans la même transaction ; commit séparément mesuré. Aucun nextval, changement de snapshot/seed ou séquence n'est nécessaire.
5. Reçu indépendant RO après commit : journal012/013/014 exact, P1 exacte, mêmes objets/propriétés/ACL, mêmes B0/seeds/séquences/publications. Nouveau reçu vers le précédent ; aucun réétiquetage de l'ancien11/11 comme preuve de P1.

Idempotence : P1 +014 exact +B0 exact = réemploi sans DDL, INSERT journal ou allocation de séquence. P1 sans014,014 avecP0, hash de014 différent, migration inconnue, propriétés divergentes ou corps inconnu = refus. Si l'accusé de COMMIT est perdu, ne pas rejouer aveuglément : une nouvelle session RO classe l'état complet P0 ouP1 ; toute autre combinaison reste bloquée.

La journalisation014 et le changement de fonction doivent être atomiques. Une faute après remplacement et avant journal/commit doit restaurer P0 par rollback transactionnel. Une panne de réponse ne vaut jamais preuve de rollback.

## Retour arrière exact

Avant commit, annuler la transaction suffit ; le nouvel oracle doit montrer P0 et l'absence de014. Après commit, **ne pas effacer ni modifier014** et ne pas appeler le reset destructif du vieux runner.

Prévoir une migration compensatoire au **prochain numéro explicitement alloué par ROOT**, qui remet uniquement la définition P0 extraite de013 et ajoute sa propre entrée au journal. Elle lie P1 etM0 exacts, l'empreinte P0 ci-dessus et un manifeste `membership-original-restored-m18da43-v1`. La chaîne012/013/014/restauration reste complète ; la politique active devient P0-restaurée, pas un faux état «013 seulement». Même verrouillage, propriétés/OID/ACL, oracles et readback. Une réactivation ultérieure exige encore une nouvelle migration ; jamais supprimer la compensation.

Refuser la compensation si un modèle ultérieur, une autre politique ou une modification de fonction dépendante est intervenu. Restaurer une fonction M0 sur un futur modèle107 pourrait retirer des validations nouvelles : ce n'est pas un downgrade autorisé. La restauration P0 ne corrige aucune donnée et réintroduit le coût d'origine ; stopper les imports dont le seal ne tient plus8s, sans hausser le timeout.

## Prochain import et modèle107

Un futur streamer doit lier séparément : modèle source/cible, manifestes de politiques source/cible, chaîne de journal exacte, catalogue structurel, corps de fonction/propriétés, bundle B0, producer/transform, source-native oracle et writer/acceptation. Conserver ces références dans ses nouveaux reçus de phases, sans modifier les reçus déjà scellés.

Pour le seul couple M0/P0 →M0/P1, une compatibilité explicite peut être qualifiée : catalogue des faits/contraintes/indices/triggers/autres fonctions exact, seule fonction P0/P1 et entrée014 différant selon les manifestes ; destination validant chaque phase sousP1. Pas d'exclusion générale des fonctions ou du journal des empreintes. Le bulk v1 gelé reste inchangé et doit refuser ce couple. La paire de politiques doit être attestée pour la reprise ; un changement entre deux phases interrompt l'import jusqu'à nouvelle revue, même s'il paraît équivalent.

Les générations et IDs de snapshot gardent leurs mappings explicites après rollback/gaps. Une version de politique n'est pas une génération et ne justifie aucun découpage des478547 lignes. Le calcul d'ownership par joins/streaming et les graphes self-FK bornés restent le chemin de capacité envisagé ; aucun streamer n'est implémenté dans ce lot.

Si107 est ultérieurement approuvé, enregistrer **un modèle M1 à chemin/version/hash distincts** et son approbation, sans remplacer les octets M0 servant aux anciennes preuves. Une proposition de chemin est `docs/architecture/orion-pro-models/<model-sha256>.json` ; ne pas créer ce snapshot avant l'approbation. Générer ensuite un delta015+ ou autre numéro alloué, jamais régénérer012/013 ni copier aveuglément tout l'intégrity SQL deM1 sur la cible. Le nouveau validateur complet devra inclure les règles nouvelles et requalifier chaque optimisation selonM1/catalogue ;139/46 est une preuve **M0**, pas une constante à imposer àM1. Les couples M1/P… et compatibilités d'import auront leurs propres manifestes et E2E. Les quatre tables proposées de107 ne sont ni créées ni présumées acceptées ici.

## Coût et portée de l'acceptation

Le candidat local a mesuré core seal5578.437ms puis commit5667.145ms, et une phase familles5560.734/5532.907ms avec tout le core encore sélectionné. Chaque instruction tient8s ; les sommes sont11.246s/11.094s. La requête ciblée isolée était30.072ms, mais ce n'est pas le coût de toute la fonction ni une mesure de son plan interne. Aucune mesure isolée de la requête originale ne permet un ratio de gain.

Le validateur parcourt l'état sélectionné global et est appelé à la fermeture puis à la validation différée du commit. Ajouter une petite phase ne rend donc pas le coût proportionnel à ses seules lignes. Un fixture local à0.5M scalars n'établit ni la capacité d'une micro-instance RDS, ni les CPU credits, ni les plans/statistiques/tempfiles, ni le WAN, ni l'univers complet. Le readback d'adoption ne constitue pas un benchmark de seal ou une autorisation d'import réel. [Mécanismes existants, lignes168–198](../../../dashboard/scripts/orion_pro_integrity.py#L168).

Garder32MiB de metadata,16MiB de buffers,500k lignes/table,2M globales,64 phases et les plafonds de séquences existants. Ne pas contourner un seal/commit8s par hausse du délai, trigger bypass, nouveau privilège, fractionnement d'une génération ou publication partielle. Le serving et les anciens corps source restent en place jusqu'à acceptation séparée des données/publications ; adoption P1 n'autorise ni cutover ni purge.

UX : publication courante inchangée pendant l'adoption. DX : une nouvelle chaîne explicite coûte un petit runner et des manifestes, mais préserve l'identité des installations et des reçus. AX : choix fermé/versionné et refus déterministes ; aucun choix de «latest» ou réparation implicite. Le compromis reste le coût global de validation et l'entretien des politiques compatibles.

Voir [PROTOCOL.md](PROTOCOL.md) pour la matrice et le budget **proposés, non consommés**. Suggested commit: `docs: define append-only validator policy adoption and rollback`.
