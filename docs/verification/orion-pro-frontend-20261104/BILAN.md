# Client de données Pro — bilan du lot

Le nouveau client épingle chaque page, résumé et requête de tirs à sa représentation publiée. Il borne son cache par taille et nombre d'entrées, mutualise les demandes simultanées et protège les données conservées contre les mutations de l'appelant. Il ne remplace pas encore le contexte React du site.

La preuve finale [11/11 workflows](runs/20261104T204130609959Z-frozen-reader-client-acceptance/result.json) utilise le vrai serveur HTTP local et PostgreSQL, sans réponse football simulée. Elle contient 14 GET et 33 instructions SQL sur le scénario complet ; ce total inclut les validations et essais de rejet/reprise.

| Comportement demandé | Résultat observé |
|---|---|
| Première page puis action suivante | Une requête par page demandée ; deux pages donnent trois identifiants distincts |
| Trois appels simultanés du même résumé | Un seul GET ; aucune requête de tirs avant demande |
| Cache limité à 512 octets | L'entrée utile de 145 octets reste conservée ; le résumé de 682 octets est rendu sans être retenu |
| Correction de A/B, C indépendante | Nouveau token pour A ; anciennes données A et C reprises avec zéro GET supplémentaire |
| Mauvais token de réponse injecté dans le test | Rejet puis nouvelle tentative réussie ; échec non conservé |
| Tirs vides / indisponibles | Réponse vide acceptée distincte de HTTP404 `NOT_COLLECTED` |

Les ratios précédant l'implémentation n'ont pas été mesurés sur un client comparable ; aucun pourcentage de gain n'est annoncé. Les trois demandeurs → un GET prouvent la mutualisation dans ce workflow. Les octets désignent le JSON logique, sans en-têtes ni coût réseau. Aucune latence Vercel/RDS/CDN ni consommation navigateur réelle n'est mesurée ici.

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_frontend_local.py --pg-bin /tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin --label review
```

Les processus HTTP/client/PostgreSQL détenus ont été arrêtés et le répertoire PostgreSQL supprimé. Le RED initial sans module reste conservé. [Protocole et limites](PROTOCOL.md). L'intégration React et son E2E navigateur constituent le lot suivant ; le frontend de production conserve son comportement actuel.

Commit proposé : `feat: pin frontend match pages and lazy details to published representations`.

CI du commit `523fbcb35c` : [run41911385349](https://github.com/OrionQuantPlatform/STATARENA/actions/runs/41911385349), trois jobs réussis ; huit suites Pro totalisant121 cas, en82 secondes pour ce job. [Reçu et limites](../orion-pro-readers-20261104/CI_BILAN.json). Cette preuve source-free ne vaut pas déploiement ou benchmark production.
