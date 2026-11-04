# Intégration React Pro — bilan du lot

Le parcours matchs utilise maintenant les pages SQL de 30 lignes, le résumé léger et les tirs chargés à l'ouverture de leur onglet. Les liens et requêtes portent la représentation publiée ; un ancien lien conserve ses anciennes valeurs. Le manifeste historique conserve son branchement existant. Le nouveau mode Pro reste désactivé en production.

Le [run final navigateur](../orion-pro-ui-20261104/runs/20261104T214821149806Z-react-clean-tracked-export-final/result.json) passe **15/15 scénarios**, sur le vrai Next.js, le backend Bun et PostgreSQL 18.6 locaux. Le parent a vérifié l’export propre de 396 entrées, dont 392 sources runtime et inspecté les captures mobile. Les copies locales étrangères au lot sont exclues du nouvel export et de la publication des anciennes preuves ; les six reçus historiques restent inchangés. Les [preuves et limites détaillées](../orion-pro-ui-20261104/RESULTS.md) conservent tous les RED et défauts du harness.

| Vérification sur les entrées synthétiques | Avant / observation initiale | Après |
|---|---|---|
| Affichage avec manifeste Pro | Ancien chargement de saison : HTTP503, zéro match visible | Trois pages de 30/30/1, 61 identifiants uniques |
| Travail de liste | Ancien parcours incompatible, aucune baseline réussie | Trois GET `limit=30`, aucune traversée automatique ; retour aux pages visitées sans quatrième GET |
| Résumé puis onglet tirs | Aucun avant comparable | Un GET résumé, zéro lecture de tirs avant intention ; un GET tirs à l'ouverture |
| Ancienne représentation A et C indépendante après correction | Valeurs initiales conservées par leur token | A reste à un GET résumé/un GET tirs ; C à un GET résumé/zéro GET tirs |
| Onglet actif à 390 px | Bouton hors du clip : x=481,06–555,97 | Bouton visible : x=293,06–367,97 dans le clip 14–376 ; défilement horizontal de 188 px, défilement vertical inchangé à zéro |
| Valeurs natives et repère | Contre-exemples préparés avant correctifs | xG/xGOT zéro, événement vide avec but vrai et point 52,5 m/34 m correctement rendus ; nom SQL NULL affiché comme inconnu |

Le scénario complet compte **22 GET API navigateur, 24 requêtes backend et 43 instructions SQL de lecture**, tous les appels API répondant 200. Deux scripts de télémétrie déjà présents sont neutralisés explicitement avant réseau par un shim local ; trois annulations de navigation RSC sont conservées et classifiées. Aucune réponse football n'est simulée et aucune transaction externe effective n'est autorisée. Les processus et répertoires temporaires détenus sont nettoyés.

Le [build de production final](builds/20261104T213300788050Z/result.json) sort à zéro en **7,049 secondes**, sans dérive de source, avec suppression de son répertoire temporaire. C'est un temps de compilation local ponctuel ; aucune accélération de compilation, latence RDS/Vercel, p95, économie réseau ou coût n'en est déduit. Le premier parcours HTTP503 ne fournit pas un avant performant comparable.

UX : pagination et état actif lisibles, données lourdes à la demande. DX : nouveau mode isolé par le manifeste et un adaptateur dédié ; les deux chemins restent temporairement à maintenir. AX : tokens, curseurs et états inspectables dans les requêtes et le DOM. Les autres pages typées, les détails supplémentaires et la pagination globale de plusieurs éditions restent ouverts ; ce lot exige une compétition lorsque le scope est ambigu. Le déploiement et la parité complète du site restent à valider séparément.

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_ui_local.py --label react-final-geometry-and-cache
python3 docs/verification/orion-pro-react-integration-20261104/verify_build.py
```

Commit proposé : `feat: integrate frozen SQL match pages in React`.
