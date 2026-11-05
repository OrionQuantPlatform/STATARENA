# Revue ROOT — validation des appartenances

Le candidat local passe **9/9 E2E** sur478547scalaires canoniques :139comparaisons deviennent des égalités uniquement pour des colonnes réellement NOTNULL ;46comparaisons nullable restent inchangées. Les1709déclarations de nullabilité de la preuve PostgreSQL correspondent au modèle approuvé. ROOT a régénéré le candidat pur, revérifié ses99artefacts(12416144B) et les627artefacts antérieurs. Le modèle, les012/013 scellés et leur compilateur par défaut sont inchangés.

La référence dense sous013 échouait par timeout après8005ms. Le candidat termine le seal en5578,437ms puis le commit différé en5667,145ms, chacun sous8s. Leur total11245,582ms dépasse8s : il ne s’agit pas d’une limite de transaction complète. Aucune baisse en pourcentage n’est calculée à partir d’une référence interrompue. Le plan autonome candidat mesuré exécute30,072ms ; le plan original est seulement estimé. Aucun plan interne PL/pgSQL n’a été capturé.

Les sept contre-exemples natifs sont refusés comme par le013 compact, notamment NULL vers nonNULL, mauvaise équipe, parent fermé/noncanonique/supprimé et ancres physiques/fournisseur invalides. Les94relations conservent leurs digests après diagnostics et rollbacks. Les attributs de fonction, rôles et objets restent inchangés. Tous les PostgreSQL temporaires sont nettoyés. Les deux démarrages autorisés sont conservés ; aucune troisième charge n’est autorisée dans cette campagne.

Ce lot fournit un **overlay local explicite**, pas une014 appliquée, un import RDS ou un transfert streaming. La comparaison des vraies données RAM vient ensuite, après préparation et revue de l’option exacte. La politique de migration append-only et les performances RDS restent à vérifier.

Commit suggéré : `perf: optimize non-null membership validation without changing semantics`.
