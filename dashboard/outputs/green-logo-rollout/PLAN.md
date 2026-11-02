# Green logo rollout, original interface palette

Updated user direction: keep all production interface colours and typography; adopt only the green stadium logo on the site, GitHub and Vercel. The earlier no-commit/no-push instruction applied to the exploratory full-kit preview; the latest request adopts the logos across live services. Limit publication to this identity scope.

Expected before edits:
- Production CSS palette, Inter typography, chart colours and theme toggle colours remain byte-identical to the baseline files. No Sora font or navy/cyan trial CSS is adopted.
- Navbar keeps its emblem-only layout and size; footer uses the supplied horizontal green logo. Light and dark variants load correctly. Browser and mobile icons use the green mark.
- README banner, repository social preview and Vercel project avatar use the supplied green-kit imagery.
- Existing routes, data, season controls and player/match functionality remain.
- Port 3016 serves the source application with production styling; the isolated full-kit preview has been stopped.
- GitHub scope was confirmed as repository STATARENA only. Do not change the organization avatar.

Inputs: /Users/lemonnierhugo/Downloads/STATARENA_Brand_Kit_Green.zip; extracted official logos/icons/social images. Original green-kit preview remains outside the checkout. Root PNG icons are copied, not redrawn. Active logo assets live in public/branding/green; old kit files remain available for historical references.

Rerun from dashboard:
PATH=/Users/lemonnierhugo/.bun/bin:$PATH bun run build
PATH=/Users/lemonnierhugo/.bun/bin:$PATH PORT=3016 API_PORT=8776 PITCHAPI_API_KEY= bun scripts/dev.mjs --production

Browser: /?season=2026%2F2027&focus=europe&league=l_3FJFUl and /classement-joueurs . Check both themes, navbar/footer logo URLs and loaded images, palette values, favicon URLs, representative navigation/detail, and mobile overflow. Save screenshot and DOM results. After Git push, verify the production deployment's exact source SHA, public image bytes, GitHub README/social preview and Vercel avatar after reload.

Actual: local production build, desktop dark/light, mobile light, ranking navigation and player detail passed. The original theme was restored after testing. Six palette/font/chart files match their original hashes and upstream; all 53 supplied assets match their SHA-256 manifest. GitHub repository social preview matches the uploaded PNG byte for byte; Vercel project avatar persists after reload. The exact application commit is deployed READY on the canonical production alias; both public themes retain the original colours and nine assets match source bytes. See RESULTS.md and the saved JSON/screenshot evidence for inputs, rerun steps and outcomes.
