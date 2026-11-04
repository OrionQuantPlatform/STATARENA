# Preuves — audit d’architecture du 4 novembre 2026

Rapport : [AUDIT_ARCHITECTURE_2026-11-04.md](../../AUDIT_ARCHITECTURE_2026-11-04.md).

## Setup et limites

- Checkout : `/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking`, `main`, commit `b2ec973d2d4aa9b25f66b58c32c9806d13e23a51` au relevé.
- AWS CLI existant, profil `statarena`, compte `361769570630`, région `us-east-2` ; accès existant à RDS, SSM et aux métadonnées S3/CloudFront.
- Python 3, `psycopg` déjà installé dans `/tmp/statarena-publication-test-python` ; certificat `dashboard/backend/certs/rds-us-east-2.pem`.
- `gh` authentifié au dépôt `OrionQuantPlatform/STATARENA` pour les lectures de workflow.
- Les scripts SQL récupèrent le paramètre SSM préconfiguré en mémoire, ouvrent des transactions READ ONLY et exportent uniquement catalogues, noms techniques et agrégats. Aucun secret ou corps métier n’est écrit.
- Chaque lecture live possède son horodatage. L’inventaire de chaque base est cohérent dans son instantané SQL ; l’ensemble AWS/Neon/S3 n’a pas été figé par cet audit.
- Aucune implémentation ni E2E applicatif n’est exécuté dans ce lot. Les sondes HTTP sont des lectures de healthcheck ou HEAD de fichiers.

## Résultats attendus et constatés

| Vérification | Attendu | Constaté / preuve |
|---|---|---|
| Topologie | Identifier les deux bases et leur serveur sans supposer le sens de `prod` | Une instance, deux bases applicatives, consommateurs AWS sur `statarena_prod` ; `databases.json`, `runtime.json` |
| Tables métier | Identifier les entités, contraintes, tailles, couverture et schémas | 161 tables app, profils limités, schéma caché dans DataGrip ; `model-analysis.json`, `datagrip-scope-trees.json` |
| Stockage | Inventaire S3 terminé et tailles SQL vérifiées | 307 pages / 306 124 objets ; 10,43 Go de `file_documents` ; `s3.json`, `databases.json` |
| Références métier | Repérer les IDs renseignés non résolus et les statuts divergents | Matchs/participations : 0 référence manquante ; calendrier : 108 liens domicile et 108 extérieur manquants, 15 statuts divergents ; `domain-integrity.json` |
| Origines importées | Distinguer documents SQL, faits et fichiers binaires | 2 195 735 `sqlite-row`, dump et six ZIP dans les payloads ; `semantic-checks.json`, `supplement.json` |
| CDN | Vérifier ce qui est réellement accessible, sans corps téléchargé | Image et JSON immuable 200 ; manifeste mutable et dump 403 ; `cdn-checks.json`, `cdn-function.js` |
| Pause | Vérifier annulation, nettoyage, workflows et absence de bail de publication | Run annulé, nettoyage réussi, trois workflows backend désactivés, bail 0 ; `pause.json`, `supplement.json` |

## Commandes exactes de reproduction

Depuis le checkout ci-dessus, les commandes suivantes ne modifient aucun service distant. Elles réécrivent les reçus locaux avec un nouvel horodatage ; conserver les originaux avant de les relancer si une comparaison historique est nécessaire.

```bash
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/aws-architecture-audit-20261104/db_inventory.py
python3 docs/verification/aws-architecture-audit-20261104/s3_inventory.py
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/aws-architecture-audit-20261104/supplement.py
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/aws-architecture-audit-20261104/domain_integrity.py
python3 docs/verification/aws-architecture-audit-20261104/cdn_checks.py
python3 docs/verification/aws-architecture-audit-20261104/summarize_inventory.py
python3 docs/verification/aws-architecture-audit-20261104/verify_artifacts.py
```

`db_inventory.py` contient les requêtes originales de catalogues/comptages ; `domain_integrity.py` enregistre SQL, colonnes, résultats et erreurs par contrôle. `summarize_inventory.py` ne contacte aucun service : il dérive le CSV et les totaux du relevé sauvegardé en utilisant les migrations locales.

`supplement.json` conserve aussi les étapes du run annulé, les statuts de tous les workflows et les deux réponses `/api/health`. La ligne `workflow_state=running` est un marqueur périmé ; le run réel est annulé et le bail est libre.

`artifact-validation.json` conserve la validation locale des JSON, scripts Python, liens et totaux S3. `credential-scan.json` copie le reçu du scanner existant, exécuté après rédaction : 2 796 fichiers et 62 contenus gzip inspectés, aucune correspondance avec les valeurs des identifiants AWS/RDS préconfigurés. Reproduction : `python3 docs/verification/aws-release-20261104/scan_credentials.py` ; cette commande met à jour le reçu dans son dossier d’origine. Ce contrôle exact n’est pas une recherche de tous les secrets possibles ou de tout l’historique Git.

Les reçus de configuration additionnels sont `runtime.json` (Lambda : cible SQL et noms de variables uniquement ; Vercel : déploiement et métadonnées des variables), `bucket-policy-readback.json` et les deux fichiers `datagrip-*.json`. Les extraits `database-references.txt` et `storage-consumers.txt` décrivent les références du code à l’instant de l’audit ; aucune valeur de connexion n’y figure.

## Essais initiaux et limites conservés

- `databases-initial-attempt.json` : échec de permission pour la taille de `rdsadmin`. Le script corrigé évite cette opération ; les deux bases applicatives sont intégralement inventoriées.
- `s3-initial-attempt.json` : réponse vide de `get-bucket-versioning` mal interprétée par le helper. L’inventaire final `s3.json` est complet, `complete=true`.
- `semantic-checks.json` : la requête `jobStates` utilisait `status` au lieu de `state` ; la requête `activityByDb` manquait d’un espace après `GROUP BY`. Les versions corrigées sont exécutées et enregistrées dans `supplement.json`. Ces erreurs ne sont pas attribuées au produit.
- `supplement.json/imageHead` : premier HEAD d’image 403 avec mauvais préfixe. `cdn_checks.py` applique `/data/` comme le code applicatif ; résultat 200 dans `cdn-checks.json`.
- Le dérivé `model-analysis.json` est régénéré avec filtre explicite sur `statarena_app` pour ne pas mélanger les colonnes des deux tables `fixtures` présentes dans deux schémas.
- La présence d’archives et fichiers est vérifiée par métadonnées et types SQL ; aucun corps de dump, ZIP ou donnée fournisseur n’est lu. Pas d’estimation de facture future, de p95 ou d’égalité complète des sources.

Nom de commit suggéré : `docs: audit StatArena databases, domain model and S3 usage`.
