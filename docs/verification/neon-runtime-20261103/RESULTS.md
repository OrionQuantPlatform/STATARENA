# Migration StatArena vers Neon — 3 novembre 2026

Le backend utilise exclusivement PostgreSQL et le stockage privé Neon. Le site sert ces données par ses propres routes : aucun appel direct à Pitch API, aucun repli vers GitHub ou un dossier local `data`. Les variables de production utilisent un rôle SQL et une clé de stockage en lecture seule. La clé Pitch a été retirée de Vercel et du `.env` local ; le secret GitHub existant a été conservé.

## Données et intégrité

- Source immuable : `579b47107e0cd4fa4f9a12a5a95dd6a1be274ed9`, **250 748 fichiers, 2 692 640 453 octets**. Arborescence conservée : `data/raw`, `data/computed`, `data/sources` dans `statarena-data`.
- SHA-256 de chaque source, MD5 côté serveur à chaque transfert, puis inventaire complet indépendant des clés/tailles/ETags ; GET de contrôle pour chaque partie. Inventaire et manifeste eux-mêmes sauvegardés et relus dans Neon. Voir `source-layout-verified.json`, `inventory-backup.json`, `catalog-integrity-final.json`.
- Les anciens manifestes modifiés par la synchronisation sont conservés sous leur empreinte dans `raw/neon/versions`. Les anciennes versions locales ont été sauvegardées sans remplacer les versions canoniques.
- Dernier contrôle : **288 160 objets, 401 197 ressources, 58 922 rencontres**, zéro référence de ressource sans objet. SQL **570 032 128 octets**, objets catalogués **3 932 139 708 octets**. Les ingestions suivantes font évoluer ces chiffres. Voir `production-cutover-state.json`.
- La branche temporaire `statarena-migration-validation` a été supprimée après confirmation explicite de l'utilisateur. Seule `production` reste.

## Validation et performances

Le [site public](https://statarena-analytics.vercel.app) sert Neon depuis le [déploiement validé](https://statarena-analytics-di0c3vdya-hlemonniers-projects.vercel.app) (`dpl_7qVcQ54JRwXiGQv7nMBmjCTkvvma`). Les fonctions sont effectivement déployées en `cle1`, vérifié dans les métadonnées Vercel après correction du réglage de région du projet. Voir `final-deployment.json` et `region-deployment-http.json` (50 contrôles réussis après ce changement). Le code applicatif validé est celui de `4b1e1d15cd7e0a70db87f17cb099e81786037fd9`. Il conserve la page d'accueil locale `00be3aa` (reprise dans `c9ffb5c`), le nouveau rendu des clubs `2186cc1`, les portraits `0eb953a` et leur reprise d'import `c21380d`.

- Build de production et **50 contrôles HTTP réussis** depuis le vrai dossier local sans données sur disque, puis sur le déploiement propre. Contrats d'archives, profils, sélecteurs de rencontres, empreintes gzip de toutes les saisons, HEAD/ETag/304 et erreurs de paramètres vérifiés. Voir `local-checkout-http.json`, `latest-deployment-http.json`.
- **Neuf pages et 11 interactions navigateur réussies**, bureau/mobile : onglets de match, sélection persistante puis restaurée, profils joueur/club, thèmes. Aucune exception JavaScript, aucun appel direct Pitch/GitHub, aucun débordement horizontal mobile. Voir `latest-deployment-browser.json`, `latest-browser-interactions.json` et les captures.
- L'ingestion a été testée sur une branche isolée avec fournisseur contrôlé : refus 403/404 suivis du travail suivant, 401 fatal, 429 repris, déduplication, reprise de bail, verrou exclusif, réutilisation des archives sans requête fournisseur et publication normalisée atomique. Voir `ingestion-e2e-final.json`.
- Index PostgreSQL utilisés pour les recherches ponctuelles ; pool limité à trois connexions, caches bornés avec mutualisation des chargements, ETags et cache CDN. Mesure HTTP/2 compressée après les tests navigateur : manifeste en cache, 10 requêtes successives **p50 66 ms / p95 90 ms** ; 20 simultanées **p50 281 ms / p95 349 ms**. Ce sont des mesures depuis cette machine, pas un SLA. Le lot HTTP Bun exécuté en parallèle du navigateur était plus lent ; ses résultats bruts sont conservés. Voir `deployment-performance.json`. Après rapprochement en `cle1` : p50 58 ms / p95 75 ms en séquentiel, p50 273 ms / p95 350 ms avec 20 requêtes simultanées ; `final-deployment-performance.json`.
- Les premières tentatives en échec sont conservées : fixtures de test corrigées, ancien motif `.vercelignore`, contrôle HEAD adapté aux en-têtes Vercel et démarrage du navigateur avant disponibilité du déploiement. Elles ne sont pas présentées comme réussies.

Rerun local, variables Neon en lecture seule configurées dans `dashboard/.env` :

```sh
cd dashboard
bun install --frozen-lockfile
bun run build
bun run verify
```

Pour le navigateur, ouvrir l'origine prête avec `playwright-cli`, puis exécuter `--json run-code --filename dashboard/scripts/verify_neon_browser.js` et `verify_neon_interactions.js`. Chaque rapport conserve l'origine, les entrées et le résultat. Pour rejouer l'ingestion contrôlée, utiliser une nouvelle branche Neon isolée selon `docs/NEON_STORAGE.md` ; la branche de validation originale a été supprimée.

## GitHub Actions

Seulement deux fichiers de workflow applicatifs, tous deux activés :

1. **Daily Sync**, chaque jour à 00:00 UTC : données récentes, projections complémentaires, images et portraits, insertion directe dans Neon.
2. **Historical Backfill**, toutes les six heures à :15 UTC : découverte/reprise des ressources manquantes, réutilisation des réponses archivées, insertion sans doublons et publication des vues.

Les deux ont réussi en conditions réelles ; voir `final-daily-run.json`, `final-historical-run.json` et leurs logs. Daily Sync a aussi réussi après les derniers changements (`latest-daily-run.json`). Le workflow ponctuel des portraits a terminé avec succès (`coach-recovery-run.json`) avant son retrait. Un [backfill réel de 60 minutes](https://github.com/OrionQuantPlatform/STATARENA/actions/runs/41664756751) a été relancé et est en cours de collecte ; son résultat final reste à venir. Voir `ongoing-backfill-run.json`.

GitHub ajoute aussi son analyse système **Dependency Graph** aux dépôts publics. Elle est indépendante des deux fichiers du repository et ne peut pas être désactivée comme un workflow applicatif : [documentation GitHub](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-security-and-analysis-settings-for-your-repository).

## Nettoyage et limites

**126 205 fichiers locaux** supprimés après vérification exacte de leur sauvegarde, plus 21 archives générées et les caches d'extraction/inventaire. Total vérifié à cette étape : **6,609,256,448 octets alloués libérés** (6,61 Go décimaux). Voir `local-cleanup.json`, `archive-cleanup.json`, `bootstrap-cache-cleanup.json`, `temporary-inventory-cleanup.json`. Les détails par fichier sont compressés et sauvegardés dans Neon (`cleanup-audit-backup.json`). Les caches de développement et dépendances temporaires, ainsi que les copies éphémères de secrets, ont aussi été supprimés (`temporary-runtime-cleanup.json`). Les variations globales d'espace libre du Mac ne sont pas attribuées à cette opération.

Un seul journal iCloud non matérialisé, `data/computed/pitchapi-world/queue 2.sqlite-wal`, reste volontairement conservé : son contenu n'a pas pu être vérifié et il occupe **zéro octet SSD**. Cela explique le statut partiel du rapport de sauvegarde des fichiers supplémentaires ; aucune donnée non vérifiée n'a été supprimée. L'ancien `main` local est conservé dans `codex/pre-neon-local-main-20261103`. Les autres worktrees et copies numérotées de code ont été préservés.

La migration de l'existant est complète ; l'exhaustivité de toute l'histoire mondiale n'est pas revendiquée. Les refus fournisseur restent enregistrés et sautés. Certaines identités/photos externes restent indisponibles ou limitées en fréquence et sont réessayées par l'ingestion ; le site conserve ses états indisponibles. Cartes et iframes officielles des stades utilisent leurs services de rendu existants ; les métadonnées et aperçus proviennent de Neon. Des seuils de capacité arrêtent l'ingestion avant saturation du plan gratuit.

La copie de migration jetable et l'export Vercel ont enfin été supprimés après confirmation de leur commit dans `main` local et distant (`temporary-checkout-cleanup.json`). Le cumul des fichiers supprimés représente **11,354,628,096 octets alloués (11.35 Go)** ; les extents partagés APFS et les nettoyages d'autres processus empêchent d'assimiler ce chiffre à la variation globale d'espace libre. Le code utilisateur, ses dépendances de travail et son historique Git sont conservés.

Commit proposé : `docs: record Neon cutover verification and verified cleanup`.
