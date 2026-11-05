# Bilan — import SQL natif par flux

Le nouveau transport passe29/29contrôles E2E dans un véritable PostgreSQL18.6 jetable. Le corpus dense comprend478547valeurs/15437participations/31métriques/612matchs. Il ne contient aucune réponse fournisseur réelle. Les91relations métier sont comparées par leurs valeurs SQL natives, en inversant uniquement les106références techniques de génération/snapshot ; les3tables de contrôle ont leurs propres contrats exacts. Les identifiants métier, décimaux, états absent/null/zéro/vide, échappements et champs JSONB techniques restent inchangés.

| Mesure observée | Résultat |
|---|---:|
| Durée de toute la campagne, avec négatifs/rollback/reprises |472,564s|
| Première phase dense transportée |513751lignes dont478547valeurs statistiques|
| Commandes COPY pour cette phase |820|
| Octets COPY encodés pour cette phase |171531679|
| Durée du worker de première phase, préflight/oracles inclus |266,155s|
| Lecture COPY cumulée côté source |199,231s|
| Écriture COPY cumulée côté cible |23,104s|
| Validation native seal/commit de cette phase |6010,858ms /5892,778ms|
| Validation seal/commit de la phase reprise |3745,850ms /3708,065ms|
| Valeurs statistiques recopiées après interruption |0|
| Nouveau lancement no-op |0COPY/0nextval ;94relations/67séquences inchangées|
| Métadonnées/buffers maximaux comptabilisés |15999887B /5013799B|
| Plus gros batch encodé |276768B|
| Pic de disque PG local alloué |2379386880B|

Le parent de stage revision2000 est réellement copié dans la commande15 et son enfant revision2 dans la commande16, sur deux batches de1000puis10lignes. Les rangs progressent sans recopie. Les cinq corruptions cohérentes de contrôle (checksum, champ inconnu, compteur falsifié, horloge manquante, horloges ordonnées mais différentes) sont refusées ; après restauration native exacte, le worker est no-op. Les compteurs2576du petit jeu excluent explicitement ses12lignes bootstrap déjà présentes, toutes conservées et vérifiées.

La réussite apporte un transport dense complet là où l’ancien pilote013 avait rencontré la limite de8s. Le nouveau seal mesuré reste sous cette limite sur cette exécution locale ; ce n’est ni une mesure RDS ni un p95 ni une comparaison de temps total avec un ancien transport réussi. La reprise vérifiée évite de recopier les478547valeurs de la première phase. Aucun pourcentage de gain web/stockage/coût n’est inventé.

La lecture source représente environ75%du temps du worker dense. Ce coût reste une piste d’optimisation mesurée : le comptage des buffers parcourt actuellement une liste croissante pour chaque bloc reçu. Il faut conserver les mêmes bornes et comparer sur le même jeu avant de revendiquer un gain. Les limites mémoire sont des allocations de conteneurs comptabilisées avec réserves, pas la RAM totale/RSS. Le pic disque n’est pas une économie de stockage RDS.

Les trois échecs de fixtures sont archivés, sans les reclasser en succès : suppression d’une relation immuable (9/1/19), comparaison comptant les12bootstrap comme imports (18/1/10), insertion explicite dans une identité ALWAYS (20/1/8). Les corrections ne changent pas le writer, les attentes de fidélité, les guards, le modèle ni les migrations. Chaque tentative a son allocation distincte consommée ; aucune n’avait construit le jeu dense. La quatrième construit et copie une seule fois cette première phase. Tous les clients/PG/répertoires temporaires sont fermés/supprimés ;0appelcloud/source/RAM,0écritureRDS,0publication.

Les7tests de processus physiques, écrits avant leur nouveau helper, vérifient le délai global partagé, l’arrêt forcé et le drainage borné. Les reçus initiaux rouges restent inspectables. Le transport reste explicitementlocal et lié aux fixtures/politiques fermées : il n’autorise ni un transfert RDS réel ni un corpus de production plus grand que ses bornes de qualification. Le transfert réel, le support global des volumes et la bascule restent à terminer.

Reproduction : champcommand/inputs du reçu indiqué par ROOT_DENSE_V4_REVIEW.json ; PROTOCOL.md et ROOT_REVISION_PROTOCOL.md pour les attentes/caps, code/fixture/paires/acceptations/plans/timings/erreurs/ressources hachés. Les anciens compteurs ne sont jamais réinitialisés. L’ancienne préparation reste exacte dans859cbb3221 ; ROOT résout explicitement ses deux anciens fichiers modifiés via ce commit. Aucun changement des anciennes politiques qualifiedImportPairs.

Commit suggéré : `fix: bound streaming workers and verify exact resume controls`.
