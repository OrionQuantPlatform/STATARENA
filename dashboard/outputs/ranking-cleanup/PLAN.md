# Ranking page cleanup E2E contract

Scope: centre the ranking heading, remove its season subtitle and the introductory sentence, remove the calibration banner and method footnote, remove the footer MIT link. Latest refinement: podium cards reuse the shared card primitive (neutral surface, uniform thin border, standard corner radius), including mobile. Remove the Le Ballon d’Or STATARENA subheading too. Preserve all 30 empty positions, season selection, method steps, shared navigation and themes. The repository LICENSE file is outside this display-only change.

Expected before implementation:
- Classement joueurs heading centred at desktop and mobile widths.
- No Saison YYYY/YYYY text beneath the heading, no Les 30 meilleurs joueurs intro, no calibration banner, no method footnote and no footer Licence MIT link.
- Three podium items + 27 other rows; no names or scores invented.
- Podium edges equal 1px neutral borders, the shared card radius; no coloured top or left strip on mobile.
- Season buttons update the selected season/URL; light/dark controls remain usable.
- Other pages retain their season subtitle and footer navigation.

Setup/rerun from dashboard:

```sh
PATH=/Users/lemonnierhugo/.bun/bin:$PATH bun run build
PATH=/Users/lemonnierhugo/.bun/bin:$PATH PORT=3015 API_PORT=8775 bun start
```

Browser input: http://127.0.0.1:3015/classement-joueurs?season=2026%2F2027&focus=all&league=l_3FJFUl . Inspect at 954x1031 and 390x844 in both themes; change season to 2025/2026, visit Données & méthode through footer navigation and confirm season context remains. Save actual observations, screenshots and build output here after verification. No unit tests needed for these display edits.

Actual: passed. See browser-evidence.json and the light/dark desktop/mobile screenshots. All 30 positions remain empty, heading centre differs by less than 0.01px from the viewport centre, cards reuse .card with 1px uniform borders, 12px radius and matching neutral backgrounds. No removed copy/nodes or footer MIT link remain. Season selection updates the URL; Données & méthode retains Saison 2025/2026. Build and formatting checks passed; no browser console errors observed. One initial theme locator used a pre-hydration label; after inspecting the current state both themes passed. Only display code was changed; no provider calls or data writes.

Remote integration: while verifying, origin/main gained 41b2e500 renaming the page/navigation to Classement Ballon d’Or. The final changes were rebased onto it without conflicts; preserve that title and rerun the final title/viewport check after rebuilding. Earlier screenshots document the pre-rename checks; final captures are refreshed after integration.

Final integration result: the rebuilt heading Classement Ballon d’Or is centred to within 0.01px at 954px and exactly centred at 390px; no document overflow. Final desktop-light.jpg and mobile-light.jpg include that rename. Dark-theme captures and the footer capture record the earlier fully checked presentation before the text-only rename. A formatting check initially requested wrapping one Layout expression; Prettier corrected it before the final rebuild and all checked source files then passed. No unit tests were added.
