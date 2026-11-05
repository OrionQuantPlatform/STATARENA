# Disponibilité du déploiement — 5 novembre 2026

**13/13 contrôles réussis**, dont le rattachement des deux domaines Vercel au déploiement de production attendu et 12 opérations HTTP. Aucun déploiement ni paramètre n'a été modifié.

| Origine | GET manifeste | HEAD | GET avec le même ETag |
|---|---:|---:|---:|
| statarena-analytics.vercel.app | 200,161 009 octets | 200,0 octet | 304,0 octet |
| orion-football-ranking.vercel.app | 200,161 009 octets | 200,0 octet | 304,0 octet |
| API CloudFront AWS | 200,37 095 octets | 200,0 octet | 304,0 octet |

Sur chacune de ces paires observées, la réponse conditionnelle évite **100 % du corps** du manifeste ; les en-têtes réseau ne sont pas compris. Les trois routes health répondent aussi200. Ensemble : **359 249 octets de corps reçus**, **6,070 s** pour l'exécution séquentielle. Ce contrôle ponctuel ne mesure ni p95 ni temps SQL, et ne démontre aucun nouveau gain de calcul serveur.

Le déploiement Vercel est `dpl_VZuf4rdjRcoX21SknjbgFXKn8GDB`, état READY/production, région cle1, code `74ea3f76de622315cb3df787c3c748bc73357e60`. Les deux alias pointent exactement vers lui. [Lecture du contrôle Vercel](VERCEL_CONTROL.json).

Les deux manifestes Vercel ont le même ETag. Celui d'AWS est différent : le frontend conserve sa passerelle transitoire et AWS sert encore l'ancien modèle relationnel, avec Pro désactivé. Cette disponibilité ne vaut **pas** validation d'un parcours frontend→nouvelles tables RDS. La bascule reste conditionnée à l'acceptation complète des données et du backend.

[Résultat et mesures par requête](runs/20261105T021606360687Z/result.json). Le [protocole](PROTOCOL.md) et les entrées exactes sont archivés dans le run. Commande de reproduction :

```sh
python3 docs/verification/orion-deployment-readback-20261105/verify_public.py
```

Les corps JSON sont lus en RAM puis abandonnés ; seules empreintes et métadonnées sont conservées. Aucune session DB, ressource temporaire, credential ou source brute n'a été créée par ce contrôle.

Commit suggéré : `test: verify deployed frontend aliases and public API availability`.
