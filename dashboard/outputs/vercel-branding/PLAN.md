# Vercel branding verification

Expected before mutation: same project ID and Git integration, name statarena-analytics, official STATARENA dark app symbol replaces the old lime Orion avatar in settings and project overview. Public canonical URL and site favicon remain available. No duplicate project or re-import.

Target: Vercel team team_IYt7KqupdSTtMuQuMvNa9wiJ; project prj_DhaqrVkH3Gi4uysT7IRsm9fB2bjR. Initial name statarena. Canonical URL https://statarena-analytics.vercel.app.

Input asset: dashboard/frontend/public/android-chrome-512.png, existing supplied logo, inspected before upload. No image generation or logo modification.

Readback rerun: use the Vercel get_project tool for the project ID and team above; open its General settings, inspect Project Name and Avatar, reload, return to team overview and inspect the tile. HTTP check: curl -I https://statarena-analytics.vercel.app/ and curl -I https://statarena-analytics.vercel.app/favicon.ico . Compare returned public icon bytes against the repository file if needed.

Actual: passed. The connector changed only the project name to statarena-analytics. Uploaded the official PNG in Avatar > Upload project avatar > Set Avatar. After reloading General settings, the name persisted and the new avatar loaded. The team overview tile shows that name, canonical domain and new logo; the duplicate import suggestion was dismissed. The canonical home page, ICO, SVG and manifest all returned 200; icon/manifest bytes exactly match the local files.

Evidence: project-readback.json, browser-evidence.json, public-checks.json and project-tile.jpg. General-settings screenshot remains local at /tmp/statarena-vercel-brand-settings.jpg. The first project-tile capture showed the hover menu over the avatar; after moving focus to the search field, the final capture displays the actual logo. An initial text locator matched three occurrences of the project name; checks were scoped to the unique canonical-domain link. No application source or data was changed; no application build or browser application E2E was run for this settings-only task.
