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

UX : pagination et état actif lisibles, données lourdes à la demande. DX : nouveau mode isolé par le manifeste et un adaptateur dédié ; les deux chemins restent temporairement à maintenir. AX : tokens, curseurs et états inspectables dans les requêtes et le DOM. Les autres pages typées, les détails supplémentaires et la pagination globale de plusieurs éditions restent ouverts ; ce lot exige une compétition lorsque le scope est ambigu. La parité complète du site Pro reste ouverte ; le déploiement du code frontend a été vérifié séparément ci-dessous.

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_ui_local.py --label react-final-geometry-and-cache
python3 docs/verification/orion-pro-react-integration-20261104/verify_build.py
```

Commit proposé : `feat: integrate frozen SQL match pages in React`.


## Publication du code frontend et contrôle réel

Le commit `74ea3f76de622315cb3df787c3c748bc73357e60` est poussé sur `main`. Les trois jobs du [run GitHub 41921701810](https://github.com/OrionQuantPlatform/STATARENA/actions/runs/41921701810) réussissent ; les neuf suites Pro exécutent 129 cas. Les métadonnées et le log Pro sont dans `deployments/ci-main-74ea3f76de.json` et `deployments/ci-main-74ea3f76de-pro.log`.

Le candidat Vercel `dpl_VZuf4rdjRcoX21SknjbgFXKn8GDB` a d’abord été créé sans prendre les domaines, puis testé : **12/12 parcours navigateur** passent sur le vrai déploiement, avec les données enregistrées existantes et sans réponse football simulée. Le même build a ensuite été promu. Le contrôle du domaine principal passe sur desktop et mobile historique (**2/2**) ; les navigateurs détenus sont fermés. Les reçus sont respectivement `output/playwright/20261104T221405262276Z-vercel-candidate/result.json` et `output/playwright/20261104T222340062477Z-canonical/result.json`.

Les lectures du plan de contrôle lient les deux anciens domaines publics au même déploiement `READY`, au bon projet, à la cible production et au commit exact. **Quatre contrôles HTTP sur deux domaines passent** : santé et manifeste répondent 200, manifeste `json-packed`, six saisons. L’ancien alias `orion-football-ranking.vercel.app` a été trouvé en 404 `DEPLOYMENT_NOT_FOUND`, alors que le reçu antérieur le liait à ce projet ; sa cause n’est pas établie. Il a été rattaché au même build testé, puis relu. Les preuves sont `deployments/promotion-control-plane.json` et `deployments/public-alias-readback.json`. La requête bornée de logs error/fatal n’a retourné aucun groupe ; ce résultat ne prouve pas l’absence de toute erreur.

Le premier script d’upload a sorti un reçu « failed » après un **upload exit0** : son ancien parseur ne reconnaissait pas le préfixe actuel `statarena-…`. Ce reçu et son log restent inchangés dans `../orion-availability-20261104/vercel-stage-20261104T220542289264Z.*`. Le plan de contrôle a réconcilié l’unique upload avec le bon commit ; aucun deuxième upload n’a été lancé. Le parseur accepte désormais les deux noms connus, et exige toujours une vérification projet/équipe/commit/environnement avant publication.

Le flag Pro reste **désactivé** ; la production utilise toujours le bridge temporaire des données enregistrées. Ce lot publie le code frontend et conserve les liens existants ; il ne valide ni la complétude RDS, ni une bascule finale AWS. Aucun gain de latence, de coût ou de stockage n’est déduit de ces contrôles. La transition build→READY observée de 12,729 s est une mesure ponctuelle de plateforme, sans avant comparable.

```sh
python3 docs/verification/orion-pro-react-integration-20261104/verify_deployed_browser.py
python3 docs/verification/orion-pro-react-integration-20261104/verify_canonical_browser.py
```

Commit proposé pour les preuves de publication : `docs: verify the promoted frontend and compatibility alias`.
