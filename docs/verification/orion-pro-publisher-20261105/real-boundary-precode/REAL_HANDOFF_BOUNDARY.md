# Frontière réelle à qualifier après la campagne owned

Commit suggéré : `feat: admit and publish retained native Pro data with explicit release boundaries`.

Les helpers sont du code produit ; leur qualification owned n'est pas une admission RDS. Le commit `7f3d4e692e8980bdedf72eb5793d40a7697c6df5` est le **ownedBaseCommit** de cette campagne. Les SHA des nouveaux helpers décrivent leurs bytes de working tree, sans affirmer leur présence dans ce commit. Une release RDS devra épingler le commit final qui contient réellement les helpers.

La qualification réelle reste à ROOT : identité/authentification RDS, CA, adresse IP libpq et hostname, postmaster, politique native, génération/snapshot effectivement transportés, readbacks natifs31/94 et mapping source/cible. Aucun appel RDS, provider, RAM ou cloud supplémentaire n'est fait par ce chantier. Aucun endpoint local n'est présenté comme une sécurité RDS.

L'admission minimale attend un core déjà normalisé avec les états de champs et la provenance exacte. Elle peut dériver les engagements `observed` depuis les participants de chaque édition complète, les labels depuis un nom du même ID prouvé, `played=True` depuis une minute native strictement positive ou un tir accepté du même match/équipe, puis la publication individuelle des matchs justifiés. Les autres participations restent inconnues. Elle ne crée ni métrique, ni score, ni joueur/profil fictif, ni coordonnées, ni heure inférée.

Les points réellement ouverts sur le core historique sont :

- Les612 chaînes UTC ont été observées dans le GET unique autorisé ; le core initial ne les projette pas. Leur parse date+timezone doit être qualifié et leur valeur exacte conservée dans SQL avant admission. Le helper refuse une heure perdue ou inventée et ne retrouve pas une valeur depuis son hash.
- Les4 tirs2025 rattachés aux IDs sources `p_4D4L8O` et `p_2mYiIC` ont des liens SQL joueur/profil NULL. Le readback indépendant ne résout pas ces identités dans le core fusionné. La source possède ces IDs : aucune absence fournisseur n'est conclue. Une édition complète concernée reste non admise tant que leur traitement exact n'est pas qualifié.
- Les9795 couples x/y ont été observés sans unité/frame normalisée prouvée. Aucun mètre/acting_ltr n'est inféré ; leur représentation reste inconnue, avec témoins de source conservés.
- Les noms de16 équipes communes aux2 partitions ont des hashes identiques. Cela ne valide pas à lui seul les noms SQL : le nom retenu, l'ID, la version, le source_record et le locator/document exact doivent encore correspondre. Les hashes/locators existent dans les inventaires gelés, sans noms ni corps bruts persistés.

L'enveloppe de publication réelle fermée reste `ADMISSION.schema.json`. Le mode `rds` refuse l'origine owned et requiert une release d'opération distincte. Pour la préparation de l'admission, l'interface de normalisation implémentée est `orion_real_four_readers_normalization_input_v1`, avec `dataOrigin=existing_aws_saved_observations`, les preuves natives de transport, les cohortes complètes, l'époque source indépendante des commits générés et les preuves par champ/coverage/label. Son succès positif sur RDS n'a pas été exécuté ni qualifié. La release finale, ses fichiers et la disponibilité de leurs preuves doivent être relus par ROOT avant toute opération réelle.

Les deux chemins d'origine ont des kinds/releases distincts. Le publisher exige un reçu d'admission réussi, son identité de code réelle, sa clôture de sortie et les snapshots correspondants. La source policy `real_source_core_v2_native31` seule n'autorise aucun writer ou endpoint. Les protections natives012/013/014 et les grants restent actifs et inchangés.
