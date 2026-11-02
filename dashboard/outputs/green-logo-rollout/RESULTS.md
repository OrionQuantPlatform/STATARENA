# Logo-only rollout evidence

Setup: Bun 1.4.4 and the repository's installed Next.js, real local JSON data, API key deliberately empty. Initial build used upstream 58532e60; a second build and homepage smoke check used 69cf6cd0 after synchronizing competition/historical-season work. Final build ce4ad4b8 also includes upstream 516baaa2. The full-kit navy/cyan/Sora experiment stayed outside the checkout and its server was stopped.

## Reproduce the local run

From the repository's `dashboard` directory:

```sh
PATH=/Users/lemonnierhugo/.bun/bin:$PATH bun run build
PATH=/Users/lemonnierhugo/.bun/bin:$PATH PORT=3016 API_PORT=8776 PITCHAPI_API_KEY= bun scripts/dev.mjs --production
```

Open `http://127.0.0.1:3016/?season=2026%2F2027&focus=europe&league=l_3FJFUl`.

1. Check the navbar emblem and footer wordmark in dark and light themes. Their visible image URLs must be under `/branding/green/logos/svg/`, with both images fully loaded. Original widths are 30px and 156px.
2. Inspect body background and the root theme variables: dark `rgb(14,15,18)`, surface `#15171b`, accent `#3b8eff`; light `rgb(246,248,251)`, surface `#fff`, accent `#1d6fd6`. Heading font must remain STATARENA Inter. Chart fills must retain the theme's original blue.
3. Open Classement Ballon d’Or using navigation; verify the 30 ranks, then return to overview and open the first recent performance. Verify Achraf Hakimi's real match details and close the dialog.
4. At 390×844 in light mode, verify `document.documentElement.scrollWidth === innerWidth`, both logos loaded and the original palette retained. Restore dark mode and reset the viewport override.
5. Inspect browser console errors and favicon links. Expected: no errors; the favicon/manifest/share links reference the green imagery.

Actual: all checks passed. See `browser-evidence.json`, `after-sync.json`, `local-final.json`, `local-dark.jpg`, `local-light.jpg`, `mobile-light.jpg` and `local-final.jpg`. The browser evidence records two corrected automation locator attempts; neither changed application data. Build logs: `build.log`, `build-after-sync.log` and `build-final.log` (all exit 0; terminal carriage returns and trailing spaces normalized). These are focused branding checks, not a claim that every data route was retested.

## Source and HTTP checks

From the repository root, this reruns the exact delivery comparison used for `local-http.json` (replace the base URL with the canonical public site to repeat after deployment):

```sh
python3 - <<'PY'
from pathlib import Path
from urllib.request import urlopen
public=Path('dashboard/frontend/public')
base='http://127.0.0.1:3016'
paths=['/branding/green/logos/svg/statarena-symbol-dark.svg','/branding/green/logos/svg/statarena-symbol-light.svg','/branding/green/logos/svg/statarena-horizontal-dark.svg','/branding/green/logos/svg/statarena-horizontal-light.svg','/favicon.svg?brand=green','/favicon.ico?brand=green','/apple-touch-icon.png?brand=green','/og-image.png?brand=green','/site.webmanifest?brand=green']
for path in paths:
    with urlopen(base+path,timeout=20) as response:
        assert response.status==200
        assert response.read()==(public/path.split('?',1)[0].lstrip('/')).read_bytes(),path
print('9/9 image and metadata assets match source bytes')
PY
```

Actual: local 9/9 and production 9/9 passed, with a public homepage HTTP 200 containing the green logo/favicon metadata. See `local-http.json` and `production-http.json`. The six palette/font/chart source hashes in `palette-baseline.json` match both the worktree and upstream; `palette-check.json` records all true. Every one of the 53 supplied image files matches the SHA-256 manifest in `public/branding/green/manifest.json`.

## External identity

- GitHub: repository Settings → Social preview → Edit → Upload the supplied `github-social-preview-1280x640.png`. Reload and compare the delivered repository-images URL with the source image. Actual: HTTP 200 and identical PNG bytes, recorded in `github-social.json` and `github-social.jpg`. Scope confirmed as repository only; organization avatar untouched.
- Vercel: existing project `prj_DhaqrVkH3Gi4uysT7IRsm9fB2bjR`, General settings → Avatar → Upload `android-chrome-512.png` → Set Avatar. Reload. Actual: new green avatar loaded and persisted; project still named `statarena-analytics`. See `vercel-avatar.json` and `vercel-avatar.jpg`. No access, root-folder or environment settings changed.
- Production: Git deployment `dpl_3WmXiPnqDFCsXWk7zPr6YzsUw63h` reached READY for exact source SHA `ce4ad4b8feaebc103fc870cdda448cce82bc885a` and canonical alias `statarena-analytics.vercel.app`. See `production-deployment.json`. On that URL, both themes and visible green logo variants were verified with real homepage data; original Inter, backgrounds and chart colours match local. See `production-browser.json`, `production-light.jpg` and `production-dark.jpg`. One DOM click did not switch themes; the inspected native accessibility button switched and restored successfully. The original public light preference was restored.
