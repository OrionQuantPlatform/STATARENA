# P1 : analyse chiffrée et état de livraison

Le lot résumés de matchs, pagination et publication immuable est implémenté, validé localement et poussé sur `codex/backend-p1-reads-publication`. La CI GitHub41733564574 est réussie et la prévisualisation Vercel est READY sur a4ade8c17b (avant la seule mise à jour documentaire de livraison). Les reçus sont `ci.json`, `ci.log`, `preview.json` et `CI_REPLAY.md`. Le P0 est déjà poussé et vérifié sur Vercel. **Le P1 n'est pas activé en production** : les lecteurs compatibles, les migrations et la fin des anciens jobs doivent précéder les nouveaux writers. Le job 41723613754 était encore actif lors du contrôle ; il n'a pas été interrompu.

## Mesures contrôlées

Les valeurs suivantes comparent deux contrats sur les mêmes fixtures, dans un PostgreSQL18 temporaire avec TLS et un serveur S3 HTTP local. Elles ne mesurent ni le trafic facturé ni un p95 de production. Les longues chaînes répétées injectées dans les détails sont volontairement synthétiques ; leur forte compressibilité explique l'écart entre octets bruts et gzip.

| Mesure | Route complète P0 | Contrat P1 | Variation |
| --- | ---: | ---: | ---: |
| SQL pour une archive froide de 13 familles / son résumé minimal | 40 requêtes | 1 | −97,5 % |
| Corps SQL lus dans ce parcours | 107 696 octets | 305 | −99,72 % |
| Corps JSON envoyé | 108 211 octets | 305 | −99,72 % |
| Corps gzip calculé sur ces réponses | 592 octets | 205 | −65,4 % |
| Liste complète de 123 matchs / première page de 50 | 1 048 934 octets | 21 468 | −97,95 % |
| Gzip de cette liste / page | 3 345 octets | 817 | −75,6 % |
| Nombre de lignes maximum par réponse du nouveau contrat | Ancienne limite 20 000 | 100, défaut 50 | Travail transféré borné par page |

Le résumé de 305 octets est la fixture minimale du protocole HTTP, pas une taille moyenne de fiche réelle. Le véritable producteur testé sur les fixtures enrichies génère des résumés de **1 237 à 1 284 octets**, avec score, statistiques d'aperçu, points xG/buts et leaders. Les routes complètes restent disponibles ; la réduction vient du choix d'une représentation adaptée au premier écran.

La pagination ne fait pas disparaître le coût d'un export complet. Le client de classement/coupe qui a besoin des123 lignes les retrouve toutes avec deux pages de 100 maximum, soit deux appels au lieu d'un. Les pages sont no-store pour éviter qu'un premier curseur ancien soit rejoué après une publication. C'est un compromis de fraîcheur et de reprise, pas un gain de taux de HIT revendiqué.

Données brutes et commandes : `final-all/results.json`, `final-all/p1-summary-comparison.json`, `final-all/p1-payload-comparison.json`, logs SQL/application et requêtes objet. Les premières exigences HTTP sont enregistrées en échec avant implémentation dans `before/`. Des cas E2E supplémentaires couvrent les erreurs découvertes en revue ; les échecs intermédiaires sont conservés et ne sont pas comptés comme réussites.

## Chargement à la demande et conservation du contenu

Le parcours navigateur démarre par **un résumé**, sans archive complète ni tirs/heatmap/réseau avancé. L'ouverture de Tirs déclenche **un** appel tirs ; revenir sur cet onglet ne le répète pas. L'ouverture de Chronologie/Heatmap déclenche uniquement leurs réponses. Le parcours contrôlé complet contient quatre appels liés au match : résumé, tirs, événements, heatmap ; **zéro archive agrégée** et aucun réseau de passes non demandé.

Le navigateur est un Next de production local. Le bootstrap est lu sur les vraies données Neon avec le rôle runtime ; seules les réponses du match QA sont interceptées et explicitement synthétiques. Onze assertions passent, sans exception applicative et sans débordement horizontal, à 1440 px et 390 px dans les deux thèmes. Quatre captures sont conservées dans `browser/`. Les 404 des scripts Analytics Vercel absents en local sont distingués des exceptions applicatives. Ce contrôle ne prouve pas qu'une projection a déjà été publiée dans Neon.

Le calendrier existant conserve sa pagination locale et ses règles de jour parisien/horaire. Les consommateurs de listes backend passent par une traversée explicite complète ; les matchs sans projection affichent un résumé pending honnête ou leur fallback établi. Les statistiques absentes restent distinctes de zéro.

## Publication immuable : gains et coût réel

La suite PostgreSQL + vrai SDK boto3 passe **18/18 scénarios**, dont visibilité avant commit, rollback, lecture des versions antérieures, ancien writer, rôle d'ingestion restreint et quotas. L'analyse détaillée et les baselines figées sont dans [publication/RESULTS.md](publication/RESULTS.md).

| Observation comparable | Avant | Après |
| --- | ---: | ---: |
| Tentatives d'écrasement avec des octets différents | 7 | 0 |
| PUT pour une publication puis une seconde URL des mêmes octets | 2 | 1, soit−50 % |
| PUT pour deux versions réellement différentes | 2 | 2 |
| Conservation de deux versions de 13 octets | 13 octets, ancienne version écrasée | 26 octets conservés |
| Upload avec budget objet déjà rempli | Accepté dans le scénario défaillant | 0 PUT, alias inchangé, aucune réservation refusée laissée |
| Deux writers pour un même budget restant | Deux admissions dans le scénario défaillant | Une admission, un PUT, plafond respecté |

Les sept tentatives initiales comprennent une écriture refusée par la fixture et six écrasements effectifs. Les totaux PUT/GET de suites entières ne sont pas comparables : les assertions en échec arrêtent des parcours avant leurs vérifications ultérieures.

La conservation augmente le stockage. Le registre inclut les réservations incertaines et les uploads dont la publication SQL a échoué ; il peut surcompter. Le cas de croissance d'un ancien objet montre pourquoi l'ancien calcul était insuffisant : 293 octets déclarés pour 1 245 octets physiques après croissance ; correction conservatrice 1 292 octets. Les orphelins historiques inconnus restent hors inventaire automatique.

Un nouvel upload unique coûte désormais six opérations SQL de registre, plus BEGIN/COMMIT, et une connexion d'ingestion réutilisée. La réutilisation vérifiée nécessite trois contrôles. Le pool web reste à trois connexions. Les limites existantes de 4,75Go objets et 900Mo SQL sont conservées ; le backfill de résumés vérifie aussi son budget SQL même sans nouvel upload. Aucun gain de latence d'écriture ou baisse de coût mensuel n'est inventé.

## Vérifications et limites de publication

- **34 scénarios/contrôles HTTP et client** : synthèse, métadonnées HEAD/304, curseurs, dates nulles, casse, recherche littérale/accents, changement de génération, absence de faux409 sur écriture vide, référence de stockage conservée, remplacement entre métadonnées/corps et les régressions P0. Les deux transports Next sont également exercés avec les nouvelles routes. `final-all/` fait foi.
- **8 workflows SQL du matérialiseur**, avec références d'archives, priorité récente, familles partielles,32 matchs entrelacés, rollback, mise à jour concurrente et refus de capacité. Les nouveaux noms publics vérifient le hash des octets gzip finaux. Les premières projections manquantes et le refus de capacité absent ont chacun été capturés en échec avant correction. `materializer-final/` fait foi.
- Régressions quotidiennes et pulse réussies pour MLS et Saudi Pro League : un but passe de 0 à 1 sans perdre la saison civile ou décaler le contrat des saisons. `daily-final/` conserve sortie et commande.
- Build de production, compilation Python et format des sources vérifiés. Les fichiers d'environnement, le collecteur actif et les données de production ne sont pas modifiés.

La voie de déploiement et les compromis UX/DX/AX sont décrits dans [BACKEND_P1.md](../../BACKEND_P1.md). Le prochain bilan en production devra mesurer les projections réellement prêtes, les fallbacks, la latence origine/CDN à trafic comparable et les octets facturés. Le P0 a son propre bilan de production ; les gains P1 de cette note sont locaux et contrôlés.

## Rejouer

Depuis la racine du worktree, avec les dépendances dashboard et les outils PostgreSQL/Python du protocole :

```sh
bun --cwd dashboard run build
STATARENA_TEST_TOOLS=/tmp/statarena-cache-test-tools STATARENA_TEST_NEXT=1 STATARENA_TEST_EVIDENCE=docs/verification/backend-p1-20261103/replayed bun dashboard/scripts/verify_backend_p1.mjs
STATARENA_SUMMARY_EVIDENCE=docs/verification/backend-p1-20261103/materializer-replayed bun dashboard/scripts/verify_match_summary_materializer.mjs
STATARENA_SUMMARY_EVIDENCE=docs/verification/backend-p1-20261103/daily-replayed bun dashboard/scripts/verify_match_summary_materializer.mjs --daily
```

Le sous-protocole publication précise son runner autonome et les dépendances Python épinglées. Le dossier browser contient configuration, code Playwright, commandes, résultats et captures. Les données restent des fixtures locales ; le rôle runtime réel est uniquement utilisé pour le bootstrap navigateur et un diagnostic de permissions en lecture seule.

Commits proposés : `feat: serve bounded match summaries and paginated fixtures`, `feat: publish match overviews through immutable storage`, `test: preserve P1 workflow evidence and quantified results`.
