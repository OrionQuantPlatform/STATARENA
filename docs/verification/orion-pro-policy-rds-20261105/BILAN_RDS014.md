# Bilan — correction014 réellement installée dans RDS

Statut : appliquée puis vérifiée depuis une deuxième connexion indépendante le5novembre2026 à10:19UTC (11:19Paris). Le code opérateur2c6f75dd511854e0e4d3d7aa94341bc88d43e11c avait été committé/poussé avant l’exécution. Le modèle103 et les migrations012/013 sont inchangés. La correction014 conserve les règles métier et remplace les comparaisons non-nullables coûteuses qualifiées dans le pilote local.

| Élément | Avant | Après |
|---|---|---|
| Journal installé |012/013|012/013/014|
| Tables / colonnes / FK |94 /1709 /431|identiques|
| Contraintes natives / vues |2475 /46|identiques|
| Valeurs des67séquences |baselineRDSacceptée|toutes strictement identiques|
| Propriétaires, ACL, propriétés et OID des fonctions |baselineRDSacceptée|identiques ; une définition de fonction remplacée|
| Anciennes lignes/horloges du journal |012/013|strictement identiques|
| Faits sportifs importés |0|0|
| Sources supprimées / collecteurs activés |0 /0|0 /0|

La comparaison exhaustive des groupes natifs ne trouve que deux différences : la définition de ingest.validate_generation(g bigint) et l’ajout d’une ligne014. L’OID259027, les propriétés/ACL/propriétaire, toutes les autres fonctions/triggers/index/colonnes/contraintes, les rôles/appartenances/droits et les données bootstrap restent identiques. La nouvelle horloge014 vaut2026-11-05 10:19:36.362104+00, exactement le début de transaction. L’étatP1 après transaction et l’état réellement relu après commit ont le même SHAe24d2f4864f2a24c639d5556b4012d276b8958f5df3d02e2a80e52a601ae9a32. Aucune acceptation locale n’a remplacé les métadonnées de sécurité RDS.

Opération complète :13,989s (14,120s avec supervision),2connexions,47SELECT dont42projections de catalogue,51appels execute plus4contrôles BEGIN/COMMIT,7250139octets décodés. Métadonnées retenues comptabilisées au plus18501184B, sous32MiB avec la réserve transitoire8MiB. Limites8s/instruction et1s/verrous conservées. Les deux connexions et le fichier privé d’authentification sont fermés/supprimés. L’allocation à exécution unique est consommée ; aucun retry d’écriture. Le contrôle de valeurs secrètes connues passe sur15863fichiers et63gzip, sans correspondance ; ce n’est pas un scan général ou de l’historique.

L’ancienne fonction n’a pas été relancée en charge sur RDS : aucun gain de latence RDS/web/CPU ne peut donc être chiffré pour ce lot. La preuve dense locale précédente conserve478547valeurs avec seal6010,858ms/commit5892,778ms et une reprise à0recopie ; elle ne devient pas rétroactivement un benchmark RDS. Aucune économie de stockage ou de coût n’est revendiquée ici.

Vérification des déploiements après adoption :13/13contrôles,12requêtes,359249octets reçus en5,862s. Les3HEADet3réponses304ont un corps de0octet. Les deux aliasVercel désignent toujours le même build74ea3f76de READY/production/cle1 ; Lambda garde sa release6827c8a8… Active/Successful/Node24 et ProOFF. Ces contrôles prouvent disponibilité/ETag uniquement. Le frontend conserve son bridgeNeon sauvegardé ; l’APIAWS conserve son manifeste legacy différent. La bascule typée et la fidélité applicative complète restent à vérifier sur les données réelles.

Preuves reproductibles : ROOT_ADOPTION_PROTOCOL.md ; commande --execute-released-rds du codecommitté root_adopt.py ; ROOT_RDS_TRANSITION_RELEASE.json et son budget consommé ; trois observations natives avec requêtes/paramètres/comptes/octets/horloges ; ROOT_RDS_ADOPTION_SUPERVISION.json ; ROOT_RDS014_FINAL_REVIEW.json ; post-adoption-deployment/verify_public.py et son run ; scan_post_adoption_credentials.py. Les8cas de frontières CLI et le REDécrit avant l’opérateur sont conservés. Les anciens compteurs/reçus ne doivent jamais être réinitialisés pour reproduire un déploiement.

Prochain travail : qualifier le transport vers l’acteur RDSingest réel et reprendre une capture bornée des sources (l’ancien processusRAM n’existe plus), puis importer le pilote métier. Conserver la complétude/fidélité et les sources jusqu’à acceptation globale ; terminer ensuite la publication, les autres routes, les collecteurs et la bascule. L’amendement107 reste distinct et non appliqué sans validation utilisateur.

Commit suggéré : `test: verify native RDS adoption and deployed availability`.
