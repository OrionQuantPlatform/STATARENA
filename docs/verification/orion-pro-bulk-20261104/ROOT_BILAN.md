# Transfert SQL typé local — bilan ROOT

L’outil importe des phases SQL typées et reprend uniquement un préfixe exact déjà scellé. Il préserve les identifiants métier, remappe séparément générations et snapshots, régénère des reçus honnêtes et conserve les contraintes existantes. Le mode par défaut ne modifie rien ; cette version refuse les connexions distantes et les historiques fermés.

Le workflow PostgreSQL18.6 passe **21/21 scénarios**. ROOT a relu le code, les oracles et les529 hashes d’artefacts, puis ajouté le workflow à la CI Linux ; aucun second passage local identique n’est présenté comme une nouvelle preuve indépendante. Le résultat CI doit être lu après push. Les RED initiaux, erreurs de fixture et erreurs de mapping restent disponibles.

| Mesure locale, même jeu synthétique | Résultat vérifié |
|---|---|
| Données du candidat | 10114 lignes dans39 relations peuplées ;55 autres relations contrôlées vides |
| Transport | 10095 lignes par47 COPY, deux contrôles de runs régénérés |
| Fidélité | 91 relations par digests de toutes colonnes natives, trois contrôles à différences explicitement énumérées |
| Métadonnées client estimées | Pic conservateur6349164 octets, plafond32MiB |
| Buffers COPY estimés | Pic4960613 octets, plafond16MiB ; aucune mesureRSS |
| Seal | 100,490 et97,427ms |
| Commit | 83,407 et81,781ms |
| Interruption/reprise | Phase en cours annulée, préfixe conservé, reprise par nouveau processus, puis no-op sans consommation de séquences |

Ces47 commandes COPY ne représentent pas le total des requêtes SQL de contrôle. Aucun avant comparable, débit WAN, temps RDS ou gain de coût n’est mesuré. La capacité sur les478547 scalaires du vrai noyau reste non vérifiée : les cartes d’appartenance en mémoire de cette version peuvent dépasser32MiB avant les plafonds de lignes. La suite proposée remplace ces cartes par des jointures SQL bornées ; ses résultats ne sont pas anticipés ici.

UX : l’ancienne publication reste servie pendant les imports partiels. DX : types/identités et gardes préservés, avec un coût de complexité pour l’attribution des phases et les refus explicites. AX : plan sans écriture par défaut, bornes et reçus inspectables, reprise déterministe. Aucune donnée réelle importée dans RDS, publication ou suppression de sources n’est validée par ce lot.

Preuves et commande : [RESULTS.md](RESULTS.md), [summary.json](summary.json), [ROOT_REVIEW.json](ROOT_REVIEW.json).

Commit proposé : `feat: add guarded local typed bulk import phases`.
