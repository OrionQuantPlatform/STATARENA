# État du pilote — modèle Pro à valider

Le protocole initial à 54 tables sœurs d’historique est **supersédé**. Sa copie
exacte est dans [superseded-prototype/PROTOCOL.original.md](superseded-prototype/PROTOCOL.original.md).
`approval-initial.json` conserve l’accord initial ; `approval.json` signale
explicitement son remplacement après les corrections de l’utilisateur et la
priorité donnée à la revue Pro. Cet accord ne vaut pas validation du modèle
révisé de 103 tables.

Aucun nouveau schéma métier n’a été appliqué à RDS. Les six fichiers de code,
migrations et tests de l’ancien prototype ont été retirés des répertoires
applicatifs actifs et archivés avec leurs preuves. Les quatre essais locaux
n’ont pas atteint l’acceptation complète ; leurs échecs et journaux restent
inspectables. Leurs serveurs PostgreSQL ont été arrêtés.

## Contrat du prochain pilote

Le [plan Pro courant](../../architecture/orion-plan-20261104/PLAN.md), sa section
9 et [la conception des versions](../../architecture/orion-plan-20261104/PRO_VERSIONING_DESIGN.md)
définissent les résultats attendus. Le modèle révisé doit être validé avant la
réorganisation distante. Les protocoles de transformation documentaire ne
remplacent pas les E2E SQL et applicatifs du futur pilote.

Avant son implémentation, figer les entrées et les cas d’échec, puis écrire les
E2E : bootstrap sur PostgreSQL vide, clés/FK et mêmes parents sélectionnés,
correction 0,82 → 0,67 avec recalcul antérieur, réimport sans doublon, types et
états natifs, collections atomiques et grilles, normalisation corrigée d’un
même record, H2H de mauvais fournisseur, deux écrivains, interruption/reprise,
générations ordonnées et droits immuables. Chaque run conserve les commandes,
attendus/résultats, journaux et nettoyage local.

Le pilote représentatif reste une compétition et deux saisons, avec mesures
comparables des lignes/index, SQL/HTTP, volumes, mémoire, WAL et espace libre.
L’inventaire complet des champs/variantes et la réconciliation précèdent toute
purge. Les premières réussites de DDL ne suffisent pas à accepter le pilote.

Rafraîchir le préflight avant toute écriture distante : instance/base/rôle,
version, consommateurs, espace libre, transactions/baux et sources disponibles.
Aucun agrandissement ni changement de classe automatique. Aucun second transfert
Neon → AWS. Nouvelles collectes directement en mémoire → RDS typé ; S3 médias.

Les relevés `preflight*.json` sont historiques et en lecture seule. Le premier
échec de requête de bail reste conservé. La disponibilité AWS/Vercel a été
traitée séparément et ne constitue pas l’acceptation du nouveau schéma.

Commit suggéré : `docs: synchronize the Orion Pro schema and review evidence`.
