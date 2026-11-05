# Supervision ROOT du rapprochement réel

Le lanceur passe **4/4 parcours CLI/PGvide** et **2/2 scénarios de processus défaillants**. Ces résultats ne comparent aucune donnée sportive réelle. Le défaut initial est conservé : une racine initdb orpheline restait sur disque malgré cleanupVerified=true ; un descendant conservant les pipes bloquait10,166s. Après correction, la racine est réellement supprimée et le détenteur des pipes est arrêté en moins de4s. Les exécutions volontairement interrompues restent marquées échouées par le superviseur.

Un TMPDIR privé0700 est créé avant tout enfant. Les racinesPG et les preuves imbriquées sont liées à ce lancement ; les nettoyages vérifient propriétaire,PID et répertoire. L’environnement est minimal, sansPG* ni identifiants cloud, et interdit explicitement les lectures de sources distantes. Le socket RAM existant reste hors de cet espace et n’est jamais arrêté.

Un premier essai après isolation a révélé une limite réelle de103octets sur les sockets Unix macOS ; son reçu3/4 reste conservé. Le préfixe privé est désormais court sous/tmp. Les entrées exactes de la première passe4/4 et des scénarios RED/verts sont conservées.

La future exécution réelle exige une releaseROOT exacte, son SHA explicite et un ledger à usage unique. Plafonds :1800s/4GiB, interruption1770s/3,5GiB, heartbeat15s, SQLécrivain8s/verrou1s et nettoyage borné. Le succès exige15cas présents et réussis,478547états et1344cellules égaux par digests indépendants, puis un nouveau processus sans modification des94tables/67séquences. Un status enfant partiel n’est jamais accepté. Les branches de dépassement disque/temps et d’arrêt d’un postmaster encore actif restent non exercées par le smoke ; aucun gain RDS ou succès métier n’est déduit de ce lot.

Commandes reproductibles sans données réelles : `python3 docs/verification/orion-real-supervision-20261105/monitor_gate.py --label reproduction` et `python3 docs/verification/orion-real-supervision-20261105/fault_gate.py --label reproduction`. Les artefacts précisent les inputs, sorties, erreurs, digests et nettoyages. Toute exécution réelle reste séparément autorisée.

Commit suggéré : `test: supervise native source reconciliation within fixed local bounds`.
