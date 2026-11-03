# StatArena : livraison backend/cache P0

Le premier lot de l'audit est implémenté et vérifié localement sur Neon + Vercel : A00, A01/A02, A03 et le rejet des objets surdimensionnés A06. Le code de départ était `bb7812bd1e`. Les modifications ne comprennent ni déploiement de production, ni écriture dans Neon, ni changement du collecteur ou du matérialiseur.

## Résultats observés

- **21 scénarios HTTP réussis**, dont 19 sur PostgreSQL 18 local avec TLS vérifié et le vrai SDK S3, puis deux parcours Next.js de production : backend embarqué et proxy HTTP local.
- **197 requêtes identiques avant/après** dans les scénarios communs, y compris les contrôles de temps et de télémétrie. Les 12 requêtes des deux parcours Next sont supplémentaires après correction. La comparaison vérifie l'ordre exact des chemins et méthodes ; elle ne compare pas les totaux de trafic de deux journées différentes.
- **50 contrôles réussis avec les vraies données Neon**, via un serveur Next de production local et le rôle runtime existant : neuf pages, manifeste, chunks de six saisons avec vérification SHA-256/décompression, archives, profils, listes, erreurs, HEAD/304 et lectures concurrentes.
- Build de production et vérification du format réussis. Aucun test unitaire ajouté après implémentation. Les scénarios HTTP et leurs résultats attendus ont été écrits avant les corrections correspondantes.

| Parcours contrôlé | Avant | Après |
| --- | --- | --- |
| GET conditionnel après expiration des métadonnées | 32 octets de corps SQL relus ; tags faibles/listes/wildcard incorrects | 0 corps SQL/S3 ; tous les validateurs testés donnent 304 |
| GET d'une version dont les octets sont retenus, après expiration des métadonnées | 32 octets de corps SQL relus | 0 corps SQL/S3 ; mêmes octets de réponse |
| Profil JSON déjà analysé, après expiration des caches courts | 82 octets SQL relus | 0 corps SQL/S3, 0 décompression, 0 parse |
| HEAD d'une projection | Corps JSON transféré depuis SQL | Requête d'existence seule |
| Lectures chaudes à 1 / 5 / 20 requêtes simultanées, avec expiration à chaque palier | 96 octets de corps SQL au total | 0 corps SQL ; une recherche de métadonnées par palier |
| GET SQL entièrement froid | 1 requête SQL, 32 octets utiles | 2 requêtes SQL, les mêmes 32 octets utiles |
| GET S3 entièrement froid | 1 requête SQL + 1 objet | 1 requête SQL + 1 objet |
| Petit cache : A, B, gros objet non admissible, puis réutilisation | A chargé 3 fois, B 2 fois | A et B chargés une seule fois ; gros objet toujours non retenu |

Ces volumes minuscules sont ceux des fixtures déterministes : ils démontrent les lectures supprimées, sans estimer l'économie mensuelle ni un gain de latence en production. Voir [comparison.json](comparison.json), [before-final/results.json](before-final/results.json) et [after-final/results.json](after-final/results.json), avec leurs logs SQL/application et requêtes objet.

La référence instrumentée ne satisfait pas 10 assertions d'acceptation sur 19 scénarios. Ce nombre comprend des exigences nouvelles de télémétrie des erreurs S3 et de comportement borné lors de publications répétées ; il ne signifie pas « dix défauts produit distincts ». Les deux corrections du banc initial — cache par hash commun à deux chemins et lecture cohérente d'une version plus récente — ont été intégrées avant la comparaison finale.

## Couverture et limites

Les vérifications couvrent les versions SQL et S3, les tags forts/faibles/listes/wildcard, l'absence de fichier, les erreurs 403/404/429/503, les références cassées, les réponses d'archive partielles et leur priorité, les listes vides, les valeurs nulles et zéro, le fallback catalogue valide/malformé/absent, les TTL GET/HEAD et les alias d'image réaffectés après expiration. Les erreurs d'intégrité ne sont pas mises en cache. Les requêtes concurrentes partagent leurs chargements, avec des contextes de mesure distincts ; sample=0 ne produit pas d'événement échantillonné.

Une publication SQL terminée entre HEAD et GET est rattrapée par une seule relance des métadonnées, en recalculant aussi le validateur et le cache JSON. Le scénario de publications répétées utilise uniquement dans la base de test une vue/fonction qui change la version lors de chaque lecture : quatre requêtes SQL, puis 503/no-store. L'ancien chemin SQL atomique pouvait retourner une ancienne version cohérente dans cette situation ; le nouveau chemin privilégie l'intégrité et borne les relances. Le versionnement immuable A08 reste la solution durable. Les erreurs S3 ordinaires ne sont pas relancées par cette logique applicative.

HEAD des fichiers et des projections évite le contenu. Les archives et ressources dynamiques nécessitent encore certaines lectures/résolutions pour garantir le même statut que GET : pas de gain intégral revendiqué sur ces HEAD froids. Les réponses complètes et les familles lourdes d'un match, les listes jusqu'à 20 000 lignes, la décompression synchrone et les allocations simultanées restent des sujets P1.

Les TTL stables sont désormais réellement appliqués : une identité peut rester ancienne jusqu'à 61 min 30 s dans les couches HTTP/applicatives après publication, hors collecte et état déjà chargé côté client. Le navigateur ne reçoit pas de SWR sur les réponses mutables. La [politique détaillée](../../BACKEND_CACHE.md) décrit les autres bornes et compromis. Aucune invalidation CDN immédiate n'est promise.

Ce contrôle utilise Next de production **sur la machine locale**. Il ne mesure pas les HIT/MISS/STALE du CDN Vercel, le p95/p99 des visiteurs, le réveil d'une origine Neon inactive ou les coûts réels des plateformes. La vérification Neon réelle est en lecture seule ; elle ne constitue pas une simulation de charge pendant une ingestion.

## Rejouer

Depuis la racine du dépôt :

```sh
mkdir -p /tmp/statarena-cache-test-tools
bun add --cwd /tmp/statarena-cache-test-tools embedded-postgres@18.6.0-beta.19
bun --cwd dashboard run build
STATARENA_TEST_TOOLS=/tmp/statarena-cache-test-tools STATARENA_TEST_NEXT=1 STATARENA_TEST_EVIDENCE=docs/verification/backend-cache-20261103/replayed bun dashboard/scripts/verify_backend_cache.mjs
python3 docs/verification/backend-cache-20261103/compare.py
```

La commande `compare.py` reconstruit la comparaison des deux exécutions finales sauvegardées. Pour recréer la référence, créer un worktree détaché à `bb7812bd1e`, appliquer seulement [instrumentation.patch](instrumentation.patch), y copier le script E2E actuel, installer ses dépendances dashboard et lancer la même commande sans `STATARENA_TEST_NEXT=1`. Son code de sortie 1 indique les assertions d'acceptation encore non satisfaites. La référence finale ne contient aucune correction P0 en dehors de l'instrumentation.

Commande utilisée pour les vraies données, depuis `dashboard` ; elle démarre et arrête son propre Next, sans arrêter les serveurs existants :

```sh
ORION_EVIDENCE_DIR=../docs/verification/backend-cache-20261103/real-data-replayed STATARENA_METRICS_SAMPLE_RATE=1 STATARENA_SERVER_TIMING=1 bun --env-file='/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/dashboard/.env' scripts/verify_application.mjs
```

Le fichier d'environnement doit contenir le rôle runtime Neon et le stockage en lecture seule, jamais le rôle d'ingestion. Les valeurs ne sont ni imprimées ni copiées dans les preuves. Résultat final : [real-data-final/http-e2e.json](real-data-final/http-e2e.json) et [server.log](real-data-final/server.log). Build : [build-final.log](build/build-final.log). Le manifeste de sources et la réception d'intégration locale accompagnent ce rapport.

## Suite

Ce lot est prêt à être relu et publié. Après déploiement : exporter une fenêtre représentative des logs échantillonnés et mesurer les en-têtes réellement reçus et les états du CDN. Engager ensuite A04/A05/A07-A11 : résumés et regroupement des matchs, pagination compatible, granularité/concurrence et publication immuable avec invalidation ciblée. Les garder en lots indépendants conformément à la page 12 de l'audit.

Commit proposé : `fix: avoid redundant Neon reads and apply backend cache policy`.
