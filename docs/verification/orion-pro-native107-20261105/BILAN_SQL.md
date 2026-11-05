# Qualification SQL 016 et 017

Commit suggéré : `feat: compile and qualify approved native match migrations`.

Le scénario complet a exécuté **29/29 cas** sur PostgreSQL18.6, sous rôles ordinaires, en **4.398 s** et **1537 appels SQL client**. Aucun appel cloud, source ou RDS. Le cluster possédé a été retiré. Le rapport donne les mesures de disque/preuves échantillonnées par cas, les SHA des inputs, les commandes et les logs.

| Schéma | Tables actives | Colonnes actives | FK actives |
| --- | ---: | ---: | ---: |
| 015 / base approuvée |94|1709|431|
| 016 / détails natifs |98|1823|447|
| 017 / six colonnes approuvées |98|1829|447|

Les179 anciennes lignes de fixture, l'OID/ACL de la vue et la représentation historique `0.8200000000000001` ont été préservés par016. La vue garde `double precision`, les faits natifs gardent les décimales exactes. D23 : l'ancien candidat refuse à tort une correction d'ordre sous un nouveau document ; le correctif conserve les quatre scalaires, insère zéro scalaire et refuse une référence du mauvais côté. D25–28 vérifient états `unrecorded/absent/null/value`, `false` et chaîne vide, refus SQL, rollback/no-op et non-downgrade de la publication.

Toutes les tentatives antérieures sont retenues : erreur type `period_rule`, transaction de fixture avec savepoint, famille métrique de fixture hors enum, deux collisions de profil de fixture, puis vrai RED de réutilisation de scalaires. Les sources anciennes et leurs résultats n'ont pas été réécrits.

Ce lot n'applique aucun changement réel016/017. Les lecteurs HTTP, le publisher natif, la compatibilité de la route existante des participations après changement du type PG et la couverture des données réelles restent des preuves séparées. Aucune latence ou économie de production n'est déduite du jeu local.
