# Translation Layout Issues

Observed on Steam Local 1.7.0 / Remote 9.0 at 1920×1080 on 2026-11-13.

## Shortened in patch data

- Entering-king declaration HUD:
  - `Declaration Conditions` → `Declare`
  - player/opponent king labels → `King in camp`
  - player/opponent piece labels → `Pieces in camp`
  - `/10 pieces` counter suffix removed
- Character Bond page:
  - `Required Items` → `Items`
  - `Bond is shared across styles` → `Bond shared across styles`
  - `Gather the items to form a contract` → `Gather Items`
  - `Replay Animation` → `Replay`
  - `Send a Gift` → `Give Gift`
  - `Master-Disciple Contract` → two-line `Mentor / Contract`

## Runtime-generated labels

Some remaining Japanese labels, including the style tag, Bond heading, gift buttons,
story/voice reward counts, and contract status, are generated from string literals in
`global-metadata.dat` rather than from Unity asset bundles.

Do not patch `global-metadata.dat`. KIOU is an online game, and modifying executable
runtime metadata carries a greater integrity/moderation risk than the existing
data-only asset translation approach. Leave these labels untranslated unless the
developer explicitly supports localization modifications.
