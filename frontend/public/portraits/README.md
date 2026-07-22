# Nikke portrait icons

Portrait icons for every engine-supported Nikke, used by the deck-builder
palette UI. The builder logic does not depend on these — they are a presentation
layer only, with a chip fallback when a slug has no portrait.

## Source

- **Origin:** [lootandwaifus.com](https://lootandwaifus.com) — the project's
  primary character-data source (see `docs/` / memory).
- **How the paths were found:** each collected character page
  (`data/lootandwaifus/char_<slug>.html`) embeds the exact CDN path in its
  `data-default-src` attribute. We read that path rather than constructing a URL,
  then download the asset locally so the frontend never hotlinks a CDN that can
  404 or rotate.
- Assets are the game's character resource renders (`mi_c<id>_00_s.*`), served as
  PNG or WebP depending on the character.

## Files

- `manifest.json` — `{ slug: filename }` map plus source metadata. This is the
  contract the frontend consumes: look up a slug, prefix with `/portraits/`.
- `mi_c*.png|webp`, plus a few banner-named assets (e.g. `0cindi.webp`) — the
  downloaded icons. Engine build-variants that share one character (e.g.
  `bready-lingering` / `bready-recommended`) point at the same file.

## Regenerating

    python scripts/download_portraits.py           # fetch missing + rewrite manifest
    python scripts/download_portraits.py --force    # re-download everything
    python scripts/download_portraits.py --dry-run  # show the plan only

Re-run after encoding new Nikkes (the registry grows) or after re-collecting
lootandwaifus HTML. In a worktree, run `python scripts/sync_worktree_data.py`
first — `data/` is gitignored, so the source HTML is absent until synced.
