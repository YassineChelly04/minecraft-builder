# 26.2 block-id verification checklist

The 26.2 (cinnabar / sulfur) block ids in `knowledge/blocks_registry.py` are
**PROVISIONAL** — added from the upgrade spec before the 2026-06-16 release. They
are gated behind `TARGET_MC_VERSION = "26.2"` and are NOT in the default
(`1.21.9`) valid set, so they cannot reach a build until the version is bumped.

When 26.2 release notes are published, verify each id below against the official
block list and correct/remove any that differ. Do **not** guess additional ids.

- [ ] `cinnabar`
- [ ] `cinnabar_stairs`
- [ ] `cinnabar_slab`
- [ ] `cinnabar_wall`
- [ ] `polished_cinnabar`
- [ ] `polished_cinnabar_stairs`
- [ ] `polished_cinnabar_slab`
- [ ] `polished_cinnabar_wall`
- [ ] `cinnabar_bricks`
- [ ] `cinnabar_brick_stairs`
- [ ] `cinnabar_brick_slab`
- [ ] `cinnabar_brick_wall`
- [ ] `chiseled_cinnabar`

After verifying: update `BLOCKS_BY_VERSION["26.2"]`, remove the PROVISIONAL note,
and confirm the `volcanic_works` palette still validates at import.
