# Revue ROOT — fermeture des replis Pro

Le correctif local passe **19/19 parcours E2E**. Le code ne modifie que `dashboard/backend/aws-app.js` ; le lecteur V1, le modèle103 et les migrations012/013 restent inchangés. Les15 fichiers du manifeste et les5 reçus conservés ont été revérifiés par SHA256.

Avant correction, un appel direct à la partition historique en mode Pro répondait200 et exécutait1SQL avec matérialisation ; son ETag pouvait encore donner304. Après correction, les153 appels aux routes non implémentées (GET,HEAD,conditionnels et cas inconnus) répondent501/no-store avec **0SQL,0appel au lecteur historique,0matérialisation et0accès source observés**. Les11 contrôles ProOFF non vides restent identiques à la référence. Les quatre routes V1, leurs anciens pins, ETags, HEAD/304 et les corrections A/B/C conservent leurs réponses.

Ce chiffre mesure le travail évité sur des routes explicitement indisponibles ; il ne mesure pas une accélération d’une fonctionnalité complète. Aucun pourcentage de latence ou gain RDS n’est annoncé.261 requêtes HTTP métier ont été exécutées dans deux serveurs Bun et PostgreSQL18.6 locaux réels. Les reçus gardent les erreurs pré-code et les entrées exactes.

Les redirections de médias exigent une référence immuable et un MIME enregistré cohérent avec PNG/JPEG/WebP ; le cache Pro est séparé du cache historique. Le contenu binaire et le chemin Next/Vercel/CDN ne sont pas validés par ce lot.

La CI ajoute ce même E2E, avec son reçu de référence pré-code, son graphe de sources explicite et ses artefacts. Son résultat sur main sera consigné après exécution. Aucun déploiement ni activation Pro n’est inclus ; le publisher, les autres routes et la parité complète restent à réaliser.

Commit suggéré : `fix: close unversioned football fallbacks in Pro mode`.
