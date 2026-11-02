# Déploiement avec un dépôt GitHub privé

Le dépôt `OrionQuantPlatform/STATARENA` est privé. Le code de cette branche permet au site public de lire uniquement les fichiers `data/raw` et `data/computed` par une fonction serveur, avec une révision Git immuable. La clé GitHub ne quitte pas le serveur. Les données de football affichées restent accessibles aux visiteurs ; le code source du dépôt reste privé.

## Configuration à effectuer par la personne qui administre Vercel

1. Créer un jeton GitHub à permissions fines limité au dépôt `OrionQuantPlatform/STATARENA` et à la permission de dépôt **Contents: Read-only**. Si l’organisation impose une approbation des jetons, la faire approuver. Ne pas le transmettre dans une conversation.
2. Dans le projet Vercel `statarena-analytics`, ajouter `GITHUB_DATA_TOKEN` aux environnements Production et Preview. Vérifier que `PITCHAPI_API_KEY` est toujours configurée. Un nouveau déploiement est nécessaire après toute modification d’environnement.
3. Conserver le paramétrage du projet documenté dans [DEPLOYMENT.md](DEPLOYMENT.md), notamment `dashboard/frontend` comme Root Directory et l’autorisation d’utiliser les fichiers situés hors de cette racine.

Vercel ne prend pas en charge les déploiements **Git** depuis un dépôt privé d’organisation sur un espace Hobby. Un passage à Pro permet le déploiement Git selon les règles de collaboration Vercel. L’alternative ci-dessous utilise un déploiement des fichiers sources via la CLI, sans changer la visibilité du dépôt ni le forfait. Voir la [documentation Git de Vercel](https://vercel.com/docs/git) et son [guide CLI](https://vercel.com/docs/cli/deploying-from-cli).

## Préparer un déploiement source

Dans une copie Git propre, à la révision exacte souhaitée :

```sh
node dashboard/scripts/prepare-vercel-source.mjs ../statarena-vercel-source
cd ../statarena-vercel-source
vercel link
vercel deploy
```

Au moment de `vercel link`, choisir le projet existant `statarena-analytics` dans l’espace qui le possède. Le dossier de sortie doit être nouveau. Le script inclut les fichiers suivis nécessaires au build et le manifeste, exclut les fichiers d’environnement et la base complète, et inscrit le SHA du commit comme révision des données. Il refuse les modifications locales non commitées dans les fichiers de déploiement. Ne pas ajouter de clé au dossier généré.

Vérifier le déploiement Preview (page compétitions, chargement des saisons, classement, coupes et archives) avant d’exécuter `vercel deploy --prod`. Un test doit inclure les appels `/data/<sha>/...` et les archives de matchs/profils, sans afficher le jeton. Les requêtes de données publiques passent désormais par la fonction serveur ; elles sont mises en cache par révision. L’utilisation GitHub et Vercel ainsi que les limites de charge doivent être observées en production.

**Actualisation quotidienne :** la collecte GitHub Actions peut continuer à commiter les données, mais les déploiements Git échouent tant que la restriction Vercel Hobby s’applique. Le déploiement source ci-dessus doit donc être répété après les nouveaux commits jusqu’à ce qu’un flux CLI automatisé ou un forfait compatible ait été configuré et vérifié. Cette branche ne configure pas cette automatisation.
