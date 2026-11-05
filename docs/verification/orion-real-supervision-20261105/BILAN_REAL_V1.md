# Premier rapprochement réel — résultat partiel

**13 parcours passent, 1 échoue, 1 reste non exécuté.** Sur les deux éditions capturées, les31champs des15437performances donnent **478547états identiques entre source et SQL** :45591absents,188032nulls et244924nombres. Les digests indépendants et les distributions de types correspondent. Les69517zéros observés appartiennent aux nombres ; aucune valeur manquante n’est transformée en zéro.

Le contrôle spatial a lu1344cellules, sans écart signalé par ses comparaisons de valeurs, mais son digest final diffère. Le reçu reste en échec. La relance dans un nouveau processus n’a donc pas été exécutée. Le diagnostic porte sur l’encodage du contrôle :32actionsparentes sont des Decimal côtéRAM et des entiers côtéSQL ; l’ancien JSON default=str encodait ces représentations numériques comme chaîne/nombre. Les digests spatiaux historiques n’avaient pas été persistés avant l’assertion et ne sont pas reconstruits a posteriori.

Un nouveau sérialiseur distingue explicitement nombres, chaînes, booléens, nulls et tableaux, tout en donnant la même représentation exacte aux int/Decimal numériques égaux. Ses14contrats isolés écrits avant le code passent ; cela ne remplace pas le futur rapprochement réel. La prochaine exécution aura une release et un ledger v2 distincts. Le ledger v1 reste consommé et ses preuves sont conservées.

Le nettoyage des bases locales est vérifié. Les trois ledgers de sources sont inchangés :0nouvelle requête distante et0nouvelHTTPobjet. Le serveurRAM reste actif. Aucun fait n’a été écrit dans RDS, aucune publication ou bascule n’a été effectuée. Les champs utiles encore non repris, les62profils exacts manquants et les autres familles demeurent ouverts ; fullAcceptance=false. Les temps et le pic de disque observés sont consignés dans ROOT_REAL_V1_REVIEW.json, sans gain de latence RDS ou HTTP déduit.

Commit suggéré : `test: retain real native field reconciliation and spatial oracle failure`.
