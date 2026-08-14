# Fonts — provenance & licensing

Self-hosted font files served by the app from `/fonts/` (SEC-9 / NFR-2: no font
CDN, no outbound requests at runtime). Declared in `src/theme/tokens.css` with
`font-display: swap`.

All three families are licensed under the **SIL Open Font License, Version 1.1**.
Each family's exact upstream license text ships next to the binaries:

| Family | Files | License file |
|---|---|---|
| Source Serif 4 | `source-serif-4-400.woff2`, `source-serif-4-400-italic.woff2`, `source-serif-4-600.woff2` | `LICENSE-source-serif-4.txt` |
| Inter | `inter-400.woff2`, `inter-500.woff2`, `inter-600.woff2`, `inter-700.woff2` | `LICENSE-inter.txt` |
| IBM Plex Mono | `ibm-plex-mono-400.woff2`, `ibm-plex-mono-500.woff2` | `LICENSE-ibm-plex-mono.txt` |

## Provenance

Downloaded at development time (2026-08-01) via the google-webfonts-helper API
(`gwfh.mranftl.com`), which repackages the Google Fonts releases; the woff2
binaries are unmodified from that source:

| Family | Package version | Subset | Weights / styles |
|---|---|---|---|
| Source Serif 4 | v14 (Google Fonts) | `latin` | 400, 400 italic, 600 |
| Inter | v20 (Google Fonts) | `latin` | 400, 500, 600, 700 |
| IBM Plex Mono | v20 (Google Fonts) | `latin` | 400, 500 |

Upstream projects:

- Source Serif 4 — https://github.com/adobe-fonts/source-serif
- Inter — https://github.com/rsms/inter
- IBM Plex Mono — https://github.com/IBM/plex

## Notes

- The subset is `latin` only (sufficient for the app's en/pt-BR UI). If the UI
  is ever localized to scripts outside latin (e.g. Cyrillic, Greek), re-export
  with the additional subsets and update the table above.
- IBM Plex Mono carries an OFL "Reserved Font Name" clause ("Plex"): relevant
  only to derivative font works, not to this unmodified redistribution.
- The OFL requires the license text to accompany the fonts — do not delete the
  `LICENSE-*.txt` files while any `.woff2` of that family remains here.
