# Bilan — lecture native réelle du RDS

Connexion AWS renouvelée et vérifiée sur le compte361769570630/utilisateurhugo.lemonnier. AWS doit utiliser Dia pour la connexion navigateur. L’inspection a réellement atteint statarena_prod sur l’unique RDS existant, PostgreSQL18.6, TLSverify-full, transaction Repeatable Read en lecture seule,8s par instruction/1s pour les verrous. Le fichier d’authentification privé a été supprimé et la connexion fermée.

14SELECT/17instructions,2418433octets décodés, sous16SELECT/20instructions/4MiB.94tables,1709colonnes,431FK,352index,90fonctions,84triggers,46vues et67séquences. Aucun fait sportif hors bootstrap.012/013 seulement, journaux/horloges natifs présents ;014 toujours absent. Le contrôle indépendant ROOT_RDS_NATIVE_BASELINE_REVIEW.json vérifie16conditions et enregistre les hashes des données natives de catalogue.

L’ancienne attestation ne comptait que1476contraintes structurelles. Cette inspection couvre aussi995NOTNULL et4contraintes de triggers, soit2475. C’est une couverture de vérification élargie, pas un gain de vitesse. Elle capture les ACL/propriétaires, rôles, appartenances, droits effectifs, horloges et valeurs de séquences réels de RDS ; ces informations ne sont pas remplacées par celles des fixtures locales. L’administrateur a effectivement CREATEDB/CREATEROLE et appartient à rds_superuser. Les deux acteurs ingestion/runtime restent ordinaires ; runtime ne peut écrire aucune table métier.

Lecture de la configuration Lambda : même release6827c8a8…, Active/Successful/Node24, flag Pro absent doncOFF. Les13workflows montrent11désactivés ; seuls Dependency Graph et Verify ingestion sont actifs. Aucun changement de configuration, aucune collecte, aucune migration ou écriture de donnée dans ce lot.

Le temps SQL de chaque projection et le coût maximal d’une instruction figurent dans la preuve native et sa synthèse ROOT. Le temps de la commande complète inclut la connexion et la résolution privée du paramètre SSM ; il ne constitue pas un benchmark de latence du site. Aucune économie de stockage/calcul ou amélioration de performance web n’est revendiquée.

Commande exacte et préconditions : ROOT_READONLY_PROTOCOL.md et root_readonly.py. Le reçu brut, les14requêtes/paramètres/comptes/octets/durées, le budget consommé, la référence au parcours local20/20 et les configurations observées sont conservés. Cette acceptation du bootstrap natif n’autorise pas seule une écriture : l’adoption014 et son readback indépendant nécessitent leur allocation concrète séparée. Le transfert réel et les fonctionnalités restantes restent ouverts.

Commit suggéré : `test: retain fresh read-only RDS native policy evidence`.
