# Complément au modèle — revue ROOT

Les détails observés ne peuvent pas tous être conservés par les103tables actuelles. La proposition ajoute trois structures typées de statistiques (période, groupe, item) et une structure de totaux H2H. Elles appartiennent aux observations déjà versionnées ; aucune table `_history`, nouveau registre générique de valeurs ni corps brut n’est ajouté.

| Définition du modèle | Approuvé | Proposé |
|---|---:|---:|
| Tables, dont neuf différées |103|107|
| Tables actives |94|98|
| Colonnes |1791|1905|
| Clés étrangères |450|466|
| Colonnes JSONB |51|51|

Les114colonnes ajoutées comprennent65champs sur sept tables existantes et49sur les quatre enfants. Les quatre remplacements de colonnes et deux remplacements de CHECK sont explicites. Ils préservent les différences absent/null/zéro/chaîne vide, les libellés/source `standard`, les noms réellement observés, l’ordre et les totaux fournis ; ils ne reconstituent pas des valeurs déjà perdues.

La [vue autonome](NATIVE_MODEL_REVIEW.html) montre les ajouts, le dictionnaire114champs et le catalogue interrogeable107tables avec leurs colonnes, clés et contraintes. ROOT a relu les raisons, structures et preuves de cohorte, vérifié34hashes et inspecté la capture mobile. Les11contrôles navigateur passent avec zéro requête externe. Il s’agit du document de revue : **aucun SQL n’est compilé/exécuté, aucune modification du schéma RDS n’est appliquée**. Les sept nouvelles règles intertables attendent leurs E2E avant implémentation. Les96chemins diagnostiqués sur deux matchs ne prouvent pas une couverture complète de toutes les sources.

UX : préserver les détails effectivement fournis, y compris listes vides et noms observés. DX : réutiliser profils/valeurs existants avec un contexte exact, au prix de nouveaux contrôles et parfois de nouvelles observations membres lors d’une correction. AX : relations et états natifs inspectables directement en SQL. Aucun gain de latence, de stockage ou de coût n’est encore mesuré pour ce complément.

L’accord initial portait sur103tables. Conformément à la demande de validation du modèle avant réorganisation, son extension attend une validation explicite ; les travaux indépendants de contrôle et transfert local continuent. Le candidat JSON conserve ses métadonnées de planning103comme base documentaire ; son adoption devra recalculer ces compteurs et enregistrer l’accord sur la structure107, sans réécrire012/013.

Commit proposé : `docs: propose typed native match detail amendments with cohort proofs`.
