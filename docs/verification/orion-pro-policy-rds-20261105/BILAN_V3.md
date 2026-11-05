# Bilan du lot — qualification locale de la politique RDS

Le préflight inclut les contraintes NOT NULL et les quatre contraintes de triggers, les propriétés/ACL/propriétaires natifs, les rôles et leurs appartenances. Les chemins de contrats et de marqueurs refusent les liens symboliques avant résolution. Le nouveau fichier d’authentification est explicite, privé et contrôlé par métadonnées sans lecture de contenu ; aucune dépendance au fichier ~/.pgpass. La transition SQL commune conserve exactement les instructions précédentes. Aucun nouveau mode d’écriture distant.

| Mesure | Prototype initial | Tentative v2 | Parcours corrigé v3 |
|---|---:|---:|---:|
| Contrôles réussis / échoués / non exécutés | 1 / 1 / 18 | 9 / 1 / 10 | 20 / 0 / 0 |
| Appels distants | 0 | 0 | 0 |

Les échecs restent archivés. Le premier était CREATE ROLE sur une connexion de setup en lecture seule ; le deuxième était la protection native55000 contre la corruption directe du journal. Le test corrigé prouve ce refus, puis utilise exclusivement le propriétaire de sa BDD jetable pour préparer les corruptions avant restauration du trigger et vérification. Une première commande relative a échoué avant tout démarrage ; sa correction en chemins absolus est documentée.

Parcours v3 : 27,013s ; pic de disque local mesuré116219904B. Une inspection comprend14SELECT/17instructions et2415643octets décodés, sous l’allocation4136960B et les plafonds16SELECT/20instructions/4MiB. Métadonnées retenues observées au plus6805924B. La transition change exactement une définition de fonction, conserve93relations natives plus le journal contrôlé séparément et les67séquences. Les nouveaux timestamps du journal égalent le début de transaction. Échec atomique, perte d’accusé de commit et reprise dans un processus neuf vérifiés. PG et son répertoire privé sont supprimés.

Le sous-parcours d’authentification passe14cas ; le seul cas d’UID différent reste non isolé, car macOS refuse le changement de propriétaire. Aucun accès DNS/driver/contenu pendant ces contrôles. Le label d’un cas du rapport vaut football.players_id_seq au lieu de sequence_state à cause d’une variable du harness ; ROOT_V3_REVIEW.json rapproche la position, les instructions exécutées et le refus natifSEQUENCE. Ce défaut d’étiquette ne doit pas être interprété comme un autre contrôle.

Ces chiffres qualifient les gardes et la transition locale. Ils ne mesurent ni un gain de latence RDS ni le fonctionnement de l’authentification RDS réelle. Aucun sport réel importé, aucune migration distante014 appliquée, aucun collecteur activé. L’inspection native RDS et son acceptation restent à faire.

Rerun exact : champ command du result.json lié dans ROOT_V3_REVIEW.json, avec ses inputs archivés et dépendances hachées. Les allocations v1/v2/v3 consommées ne sont jamais réinitialisées ; une nouvelle exécution demande une allocation distincte ROOT. Résultats attendus : les20cas, les93relations natives et le journal, les67séquences, les trois verrous, les limites inchangées et le cleanup effectif. Les preuves incluent les commandes PG, logs, contrats, sorties CLI et ressources.

Commit suggéré : `fix: qualify exact RDS policy metadata and private authentication`.
