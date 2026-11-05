# Proposition : six colonnes pour le détail natif du match

Commit suggéré : `docs: review missing native match core fields`.

**À valider. Aucun modèle, SQL ou service n’est modifié par cette proposition.**
Le modèle 107 déjà approuvé reste figé au SHA256
`f516804f6e2381b5e55763860b6470127b88a567006973afa79c0a9f5f0d9ae3`.

Les diagnostics retenus sur deux matchs montrent trois champs effectivement
présents que le modèle 107 ne sait pas conserver comme observations natives :
`data.referee` (2 chaînes), `data.has_playoff` (2 booléens) et
`data.league.image_url` (2 chaînes). Il ne s’agit pas d’anticiper de nouveaux
champs : les trois existent déjà dans la réponse et le modèle relationnel
historique. La [matrice complète](../orion-pro-match-readers-20261105/CORE_MOMENTUM_FIELD_MATRIX.json)
relie les 20 chemins du détail match et les 3 chemins du momentum aux
destinations typées, aux lacunes et aux consommateurs. Aucune nouvelle lecture
du fournisseur, d’une base source ou d’un corps de réponse n’a été faite.

`has_playoff` influe directement sur le regroupement du calendrier dans
[MatchdaySchedule.jsx](../../../dashboard/frontend/src/components/MatchdaySchedule.jsx#L35)
et [cup-worker-client.js](../../../dashboard/frontend/src/services/cup-worker-client.js#L56).
Le déduire d’un tour, d’une manche ou de l’absence d’un champ ferait perdre le
booléen réellement fourni. `referee` est un libellé source : aucun consommateur
direct n’a été trouvé dans le frontend actuel, mais le champ fait partie de la
réponse native existante. L’URL observée du championnat reste un fait natif
distinct de l’adresse de livraison de son image : un lien de média mutable ne
peut pas figer cette valeur historique.

Les six colonnes seraient ajoutées à l’observation existante
`football.match_observation_details`, dont le `source_record_id` fixe la
provenance. Aucune nouvelle ligne d’historique, identité d’arbitre, table ou
copie de corps source n’est proposée.

| Propriété native | Colonne de valeur | Type | Colonne d’état |
|---|---|---|---|
| `data.referee` | `source_referee_label` | `text` | `source_referee_state` |
| `data.has_playoff` | `source_has_playoff` | `boolean` | `source_has_playoff_state` |
| `data.league.image_url` | `source_league_image_url` | `text` | `source_league_image_url_state` |

Chaque colonne d’état est un `text` non nul, par défaut `unrecorded`. Les valeurs
autorisées et leur contrainte de paire sont les mêmes pour les trois propriétés :

| État | Valeur SQL autorisée | Effet dans une réponse native admise |
|---|---|---|
| `unrecorded` | `NULL` | Connaissance historique insuffisante ; pas de réponse annoncée complète |
| `absent` | `NULL` | Propriété omise |
| `null` | `NULL` | Propriété présente avec `null` |
| `value` | Non `NULL`, du type de la colonne | Valeur exacte ; `false` et `''` restent des valeurs |

Un CHECK par paire impose l’énumération et la cohérence valeur/état. Les valeurs
et leurs états sont immuables dans l’observation source. Une correction suit
les règles d’observation et de génération existantes ; un réimport identique
ne crée pas une nouvelle version. Les anciens enregistrements restent
`unrecorded` sans déduire une absence ou un `false`. Un type ou une structure
source non qualifié est refusé à l’admission native, avec une raison explicite.

| Mesure | 107 approuvé | Avec la proposition |
|---|---:|---:|
| Tables, dont 9 différées | 107 | 107 |
| Tables actives | 98 | 98 |
| Colonnes ajoutées depuis 103 | 114 | 120 |
| Colonnes totales / actives | 1 905 / 1 823 | 1 911 / 1 829 |
| Clés étrangères totales / actives | 466 / 447 | 466 / 447 |
| Nouvelles tables / JSONB / historiques indépendants | 0 dans cet ajout | 0 |

Après accord seulement, ROOT pourrait préparer une **migration 017 additive**,
distincte de 016, en conservant le modèle f516 et toutes ses preuves. Il faudra
d’abord écrire les cas de refus/acceptation, vérifier la migration et sa reprise
sur PostgreSQL possédé, la fermeture des anciens contrats, les nouveaux états
dans le corps HTTP et la dépendance de publication. Aucun changement de
production ou bascule ne découle de cette proposition.

Le momentum observé ne justifie pas cet ajout. Ses 188 points diagnostiqués
utilisent des minutes numériques à deux décimales au plus et de petits entiers
pour la valeur, avec l’ordre natif conservable dans `sample_index`. Leur
réconciliation reste à exécuter ; des états ou précisions hors de cette forme
qualifiée ne sont pas inventés. Les quatre familles approuvées de l’extension
107 avancent sans attendre la décision sur ces six colonnes.
