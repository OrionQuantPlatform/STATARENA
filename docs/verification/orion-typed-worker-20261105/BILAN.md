# Accès des collecteurs SQL typés — 5 novembre 2026

Le mode `typed-ingest` de l'action AWS charge uniquement le credential RDS existant. Il impose l'instance, le port5432, la base statarena_prod et le rôle statarena_ingest. Il conserve le TLS verify-full et n'exporte aucun paramètre S3, alias Neon ou mode de stockage de documents bruts.

**10/10 vérifications passent** après le véritable échec avant implémentation :0pass/1fail/9non exécutées. Les tests ont exactement les mêmes octets avant/après (`1a0f9f0d5ecbfd91e6a96e9f4d8fde88ff4ce6b324eeea6ff4d6226cb531cffc`). Ils exécutent le script et la véritable CLI AWS contre un serveur SSM local possédé. Les réponses SSM sont des fixtures synthétiques ; il ne s'agit pas d'une exécution AWS réelle.

| Mesure, même fixture d'entrée | Mode transitoire ingest | Nouveau typed-ingest |
|---|---:|---:|
| Paramètres SSM déchiffrés | 2 | 1 (−50 %) |
| Lecture du paramètre S3 | 1 | 0 |
| Credentials S3 exportés | 2 | 0 |
| Variables exportées | 17 | 7 |

Les refus pour mauvais hôte/base/port/rôle, refus SSM, paramètre non chiffré et mode inconnu passent. Aucun refus n'écrit de variable. Les deux anciens modes ingest/runtime restent des contrôles positifs vérifiés. Les fichiers temporaires privés sont supprimés ; aucun secret visible hors directives GitHub de masquage n'est observé.

Le run complet dure9,571s. Il ne permet pas de conclure à un gain de latence ou de coût AWS. La réduction mesurée porte sur les paramètres chargés et les credentials exposés. Aucun fait métier, média ou fichier brut n'est transféré dans ce lot.

La CI réexécute ces dix cas sans OIDC ni credential réel et conserve les preuves, y compris en cas d'échec. Résultat Linux distant encore à vérifier après push. [Résultat local](runs/20261105T022456481688Z-rds-only-typed-worker-green/result.json), [échec initial](runs/20261105T022432082863Z-missing-typed-mode-red/result.json), [environnement](ENVIRONMENT.json), [protocole](PROTOCOL.md).

Le [relevé GitHub](WORKFLOW_READBACK.json) confirme11workflows désactivés ; seules Verify ingestion et Dependency Graph sont actives. Aucune collecte n'est activée ou déclenchée. Les futurs workflows devront adopter ce nouveau mode une fois les producteurs SQL et leurs publications qualifiés. La configuration de credentials n'est pas, à elle seule, une preuve de collecte quotidienne complète ou de connectivité RDS depuis un runner.

UX : la production reste disponible. DX : une configuration SQL distincte évite les aliases historiques et le credential de stockage pour ces collecteurs. AX : le mode, la cible, les refus et les variables sont bornés et inspectables. Les modes de compatibilité sont temporaires et restent limités aux anciens chemins désactivés.

Reproduction : `python3 docs/verification/orion-typed-worker-20261105/e2e.py --label <label>`.

Commit suggéré : `feat: add RDS-only typed ingestion worker credentials`.
