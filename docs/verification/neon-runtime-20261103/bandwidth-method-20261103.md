# Mesure du transfert pendant la navigation

Le 3 novembre 2026, la session de test a reçu environ **15,9 Mo** pour les huit pages principales via les liens du site. L'ouverture complète de l'alias `/calendrier` a ajouté **13,9 Mo**. Total des neuf URL, documents compris : **29 766 650 octets, soit 0,0298 Go décimaux**. Les fichiers et réponses de football uniques représentaient environ 15,1 Mo encodés / 15,9 Mo décodés.

Il s'agit d'octets reçus par le navigateur, pas d'un compteur de facturation Neon. Les scripts/styles proviennent de Vercel ; les réponses du cache CDN évitent des lectures Neon, et le cache du serveur peut éviter un chargement SQL/S3 même sur un MISS CDN. Le compteur mensuel du projet ne permet pas d'attribuer exactement ce parcours pendant qu'un backfill tourne.

## Entrées et résultat attendu

- Origine : `https://statarena-analytics.vercel.app`.
- Saison courante `2026/2027`, périmètre `focus=all`, viewport normal du navigateur de test.
- Parcours : accueil, calendrier `/matchs`, joueurs, clubs, compétitions, archives, classement, méthode ; puis navigation complète vers `/calendrier`.
- Caches normaux conservés. Aucun défilement exhaustif des listes, aucune ouverture de chaque profil ou des autres saisons.
- Attendu : neuf pages visibles, métriques Resource Timing disponibles sans saturation du tampon, totaux en octets et distinction navigateur/Neon.
- Résultat : neuf pages chargées ; métriques et limites conservées dans `bandwidth-20261103.json`. Tampon initial : 167 ressources (<250), puis 357 (<10000) ; second document : 194 (<250).

## Reproduction exacte via CUA

Après initialisation de CUA, ouvrir l'origine dans un premier appel :

```js
let meterTab = await cua.createBrowserTab("iab", "https://statarena-analytics.vercel.app", {visible:false});
```

Dans un deuxième appel, installer la capture de développement. Le protocole CDP est nécessaire : l'évaluation DOM limitée de Playwright n'expose pas `performance`.

```js
let meterCdp = await meterTab.capabilities.get("cdp");
await meterCdp.send("Network.enable", {});
await meterCdp.send("Runtime.evaluate", {
  expression:"performance.setResourceTimingBufferSize(10000)",
  returnByValue:true
});
async function readTraffic() {
  const r = await meterCdp.send("Runtime.evaluate", {
    expression:"JSON.stringify({resources:performance.getEntriesByType('resource').map(e=>({url:e.name,transferBytes:e.transferSize,encodedBodyBytes:e.encodedBodySize,decodedBodyBytes:e.decodedBodySize,initiatorType:e.initiatorType})),navigation:performance.getEntriesByType('navigation').map(e=>({transferBytes:e.transferSize,encodedBodyBytes:e.encodedBodySize}))})",
    returnByValue:true
  });
  return JSON.parse(r.result.value);
}
```

Attendre le contenu visible de l'accueil et la disparition du message de chargement des autres compétitions, puis relever `await readTraffic()`. Cliquer les liens dans l'ordre ci-dessus avec `meterTab.playwright.getByRole('navigation',{name:'Navigation principale'}).getByRole('link',{name:'Calendrier',exact:true}).click()` pour le premier ; les trois suivants utilisent la même navigation. Le lien Archives est sur Compétitions ; le classement et la méthode sont dans le pied de page. Après chaque clic, attendre le titre de la page, lire `domSnapshot()`, laisser les requêtes enregistrées se terminer et relever `readTraffic()`. Les entrées restent cumulatives sur ces huit navigations clientes.

Avant la dernière navigation, conserver `let mainTraffic = await readTraffic()`. Puis :

```js
await meterTab.goto("https://statarena-analytics.vercel.app/calendrier?season=2026%2F2027&focus=all");
await meterTab.playwright.getByRole("heading",{name:"Calendrier",exact:true}).waitFor({state:"visible"});
await meterTab.playwright.getByText(/autres compétitions en cours de chargement/).waitFor({state:"hidden",timeoutMs:30000});
await meterTab.playwright.getByText("Chargement des données…",{exact:true}).waitFor({state:"hidden",timeoutMs:30000});
let aliasTraffic = await readTraffic();
const received = [...mainTraffic.resources,...aliasTraffic.resources,...mainTraffic.navigation,...aliasTraffic.navigation].reduce((n,e)=>n+e.transferBytes,0);
nodeRepl.write({receivedBytes:received,decimalGB:received/1e9});
await meterTab.close();
```

Les valeurs évoluent avec les données, la saison, le viewport et les caches. Ne pas présenter le poids du navigateur comme une mesure exacte de transfert facturé par Neon.

Commit proposé : `docs: measure site navigation transfer usage`.
