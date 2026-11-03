# P0 publié : analyse chiffrée

Code `5510ca4bee`, preuves `6bea1b950a`, tous deux poussés sur `main`. Vercel a publié exactement `6bea1b950abf647c58cf9895761132191261e70f` en production : `dpl_HaiFSY9YKrs3R1YaBdNyhvJQMRq4`, état READY, région cle1, alias https://statarena-analytics.vercel.app. Construction observée par l'API : 21,327 secondes entre buildingAt et ready. Voir `vercel.json`.

## Gains contrôlés côté origine

La même séquence de 197 requêtes a été rejouée sur le même PostgreSQL/S3 de test. Les chiffres ci-dessous concernent les corps utiles lus depuis les sources, sans compter les métadonnées ni le transport réseau.

| Mesure | Avant | P0 | Variation |
| --- | ---: | ---: | ---: |
| Corps SQL relu sur GET conditionnel après expiration des métadonnées | 32 octets | 0 | −100 % |
| Corps SQL relu sur GET d'une version retenue en mémoire | 32 octets | 0 | −100 % |
| Corps SQL relu sur profil déjà analysé | 82 octets | 0 | −100 % |
| Corps SQL aux paliers concurrents 1 / 5 / 20, après amorçage | 96 octets | 0 | −100 % |
| Corps JSON de projection chargé pour HEAD | 1 ligne | 0 | −100 % |
| Chargements de la petite entrée A après deux gros objets refusés | 3 | 1 | −66,7 % |
| Requêtes SQL d'un fichier inline entièrement froid | 1 | 2 | +100 %, soit une requête supplémentaire |
| Octets utiles du même accès froid | 32 | 32 | inchangé |

Les faibles volumes des fixtures établissent le mécanisme, pas une économie mensuelle ni une vitesse générale. Les TTL d'identité passent réellement de 60 à 3 600 secondes ; ce facteur 60 concerne la durée du cache et retarde aussi la visibilité d'une correction. Ce n'est pas un facteur 60 de gain de latence.

## Vérification en production

Le protocole HTTP complet passe **50 contrôles** sur le domaine public après déploiement : neuf pages, six saisons, intégrité SHA des chunks, archives/profils/listes, HEAD/304, erreurs et lectures concurrentes. Résultat et commande : `public-http.json`. Les **21 scénarios** locaux PostgreSQL/TLS/S3/Next du P0 restent tous réussis.

Une petite comparaison descriptive alterne les anciens et nouveaux déploiements depuis la même machine : un profil public de **252 octets**, un amorçage puis **20 lectures par version**.

| Mesure HTTP complète | Ancien déploiement | P0 |
| --- | ---: | ---: |
| Réponses HIT CDN | 20/20 | 20/20 |
| p50 | 11,36 ms | 12,92 ms |
| p95 | 51,60 ms | 41,77 ms |
| Corps renvoyé | 252 octets | 252 octets |

Le p95 observé baisse d'environ 19 %, le p50 augmente d'environ 14 %. Avec seulement 20 observations par domaine, toutes en HIT CDN et sur une petite réponse, cette différence ne démontre pas un effet causal du P0 sur le backend. Elle valide le fonctionnement public ; les gains d'origine confirmés sont ceux du tableau contrôlé. Aucune baisse de coût Vercel/Neon, aucun p95 global des visiteurs et aucun taux de HIT global ne sont extrapolés.

Rejouer : `bun docs/verification/backend-cache-20261103/deployment/benchmark.mjs`. Données brutes, en-têtes et paramètres : `benchmark.json`.

## Suite P1

Mesurer séparément le nombre de requêtes et d'octets d'un résumé, la taille et l'exhaustivité des pages, les chargements réellement différés et l'intégrité des anciennes versions après publication/rollback. Conserver les routes complètes pour leurs consommateurs et isoler les fixtures de la production.

Commit proposé : `docs: verify P0 Vercel release and quantify cache changes`.
