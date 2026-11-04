# P1 — contrat de vérification avant implémentation

Le plan a été explicitement validé. Le reçu `approval.json` fige son commit et ses empreintes. Aucun test unitaire n’est ajouté après implémentation : les parcours ci-dessous sont écrits avant les migrations et exécutés sur un vrai PostgreSQL 18.6 jetable, puis sur un pilote AWS borné.

## Périmètre et sorties attendues

- Créer les 152 tables métier/ingestion/lecture approuvées, 1 897 colonnes et 350 FK. Les neuf tables réservées aux futurs modèles restent documentaires. Les 54 historiques typés sont inclus.
- Nouvelles migrations 012 et suivantes ; aucune modification des migrations 003–011 scellées. Journal de versions/empreintes, transaction et verrou pour une reprise sans double application.
- Aucun nouveau stockage de réponse brute. Les nouvelles collectes iront de la mémoire aux colonnes SQL ; la provenance ne contient que des métadonnées. Le pilote utilise les sources AWS existantes, sans deuxième transfert depuis Neon.
- Les anciennes tables, données, lecteurs et médias restent disponibles. Le rôle web ne peut pas écrire ; les versions/snapshots publiés ne peuvent pas être modifiés par l’ingestion.

## Parcours E2E et échecs à provoquer

1. Base vide → migration → graphe métier → historique → instantané scellé → lecture SQL. Comparer les objets réellement créés au contrat complet ; rejouer les migrations sans modification ni doublon ; provoquer une interruption transactionnelle et prouver son rollback.
2. Deux saisons d’une même compétition, équipes et joueur communs, alias publics stables. Un profil ou nom modifié ne crée pas une nouvelle personne ; les versions historiques restent lisibles.
3. Match publié avec un côté absent, deux équipes identiques, équipe inconnue sans libellé ou équipe inconnue sur un match joué : refus au COMMIT. Autoriser les deux places explicitement non résolues d’une rencontre à venir.
4. Participant/statistique/tir rattaché à la mauvaise équipe ou au mauvais match : refus. Une performance avec minutes inconnues ne prouve pas une participation et ne devient pas zéro minute.
5. Valeur absente, null explicite, zéro, chaîne vide et type natif nombre/texte : conservation distincte. Les champs sémantiques sont enregistrés, pas des chemins JSON arbitraires. Refuser un état incohérent et un JSONB technique trop gros ou contenant un objet métier imbriqué dans les drapeaux.
6. Mise à jour canonique → nouvelle représentation typée immuable ; réexécution identique → aucune nouvelle version. Refuser une version orpheline, un mauvais grain/relation/hash, une mutation d’historique ou d’un membre d’instantané scellé.
7. Sceller un instantané seulement si ses FK historiques se résolvent dans ses propres versions. Une correction actuelle ne change pas les valeurs d’un ancien instantané. Deux écrivains concurrents ne créent pas un cycle ni deux révisions du même grain.
8. Refuser les nombres non finis, repères/grilles incohérents, cellules dupliquées/hors grille, provenance de classement incompatible et cycles de référentiels/métriques. Préserver les valeurs sportives signées autorisées.
9. Publication vers un build non prêt, snapshot non scellé ou édition différente : refus. Aucun agrégat d’un build prêt/publié ne peut être changé. La preuve des calculs complets et du cache HTTP appartient aux prochains lots backend, pas au simple DDL.
10. Suppression logique d’une source historique non réconciliée, reçus incomplets ou dépendance de transfert non levée : refus. En P1, aucune source réelle n’est supprimée. Le test n’autorise pas le nettoyage de production.
11. Vérifier la lecture seule du rôle runtime et la protection du registre/historique contre les écritures directes. Exécuter les mêmes transactions comme service d’ingestion, pas uniquement comme superutilisateur.
12. Pilote réel : sélectionner une compétition sur deux saisons dans les sources AWS, contrôler tous les champs du périmètre retenu, interruption/reprise/idempotence, comparaison des IDs/valeurs/types/relations et lectures sans conteneur source. Toute donnée inconnue reste un rejet explicite, jamais une valeur inventée.

## Mesures et preuves

Chaque exécution conserve : setup, moteur réel, paramètres d’entrée et requêtes de sélection, commande exacte, résultats attendus/réels, erreurs SQLSTATE, traces utiles et arrêt de l’instance locale appartenant au test. Conserver le premier échec avant correction.

Avant toute écriture AWS : contrôler la version, l’instance/base/rôle, les schémas présents, les consommateurs, le volume de toutes les bases, l’espace libre CloudWatch et les transactions actives. Délais de verrou et d’exécution bornés. Aucun changement de classe/stockage/service payant.

Mesurer les lignes et octets SQL, historiques et index, temps SQL de lectures comparables, coût d’import/reprise et requêtes nécessaires. Un DDL n’apporte pas à lui seul un gain HTTP. Les résultats locaux ne deviennent pas des latences RDS ; aucune économie n’est extrapolée de l’espace provisionné.

Commit suggéré : `feat: establish the approved Orion schema and transactional histories`.
