# Reprise du normaliseur — bilan du lot

Les phases importées sont désormais liées à des reçus SQL scellés comprenant source, sélecteurs, transformateur et modèle. Un nouveau processus peut retrouver le périmètre du pilote sans conserver l'état Python initial. Un changement d'entrée ou de transformateur est refusé explicitement ; sa réconciliation automatique n'est pas implémentée.

La preuve finale [17/17 workflows](real-source-runs/20261104T204329068716Z-final-scoped-restart-and-explicit-checkpoint/result.json) comprend onze cas de frontière CLI. Deux nouveaux interpréteurs réimportent les mêmes sources ; deux autres refusent une source ou un sélecteur altéré. Après chacun des quatre processus, les empreintes globales des **94 tables et 67 séquences** restent identiques. Aucun fait, révision, génération acceptée ou incrément de séquence supplémentaire n'est observé. Le joueur synthétique étranger au pilote et son alias restent inchangés.

Le contre-exemple précédent échouait à cause d'une réhydratation globale des identités. Le correctif limite les recherches aux identifiants, documents et source du pilote. Les essais RED, y compris les erreurs du harness, restent inspectables et ne sont pas requalifiés en succès. [Résumé complet et patch de revue](real-source-runs/20261104T204329068716Z-final-scoped-restart-and-explicit-checkpoint/SUMMARY.md).

Périmètre réel inchangé : 612 fixtures, 387 matchs terminés, 839 joueurs, 20 clubs, 15 437 participations et 9 795 tirs ; les **61 748 états** des quatre métriques communes vérifiées ont le même digest source et SQL. Les treize familles détaillées restent des projections partielles, pas une réconciliation exhaustive des feuilles.

L'acquisition temporaire a consommé au total **89 requêtes et 254 796 352 octets décodés** sur le budget historique 100/268 435 456. La dernière exécution finale a utilisé uniquement la RAM : **zéro nouvelle lecture AWS**, aucun corps sauvegardé et aucune écriture distante. Le serveur RAM, sa socket et son répertoire privé ont été supprimés. Une capture exige maintenant les compteurs exacts explicites et refuse avant connexion une marge insuffisante ; le budget existant n'est pas réinitialisé.

Ce lot ne mesure aucun gain de temps ou stockage en production. Il prouve l'absence de duplication dans les workflows exécutés. `fullAcceptance=false` : fidélité intégrale, autres contrats natifs, réparation d'une source modifiée, reprise de chaque interruption intermédiaire, bulk import RDS et publication réelle restent ouverts.

Rejouer les frontières sans accès cloud :

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_real_pilot.py --preflight-only --label review
```

La reprise réelle exige une nouvelle acquisition RAM avec un budget distinct explicite ; la marge du budget historique ne permet plus une capture entière de 32 Mio. Les commandes exactes et préconditions historiques sont conservées dans les reçus, sans les relancer implicitement.

Commit proposé : `fix: scope pilot retries and require explicit capture checkpoints`.
