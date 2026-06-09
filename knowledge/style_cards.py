"""
Style cards — ≤120 tokens of taste each, injected into agent prompts in place of
long skill-file prose. Format: positives, lighting rule, then 2–4 explicit AVOIDs
(negative guidance is disproportionately effective on weak models).
"""

STYLE_CARDS: dict[str, str] = {
    "medieval": ("Asymmetry ok. Heavy timber accents, banners, barrels outside. "
                 "Warm light only (lantern/torch/campfire). Inside: rugs, bookshelf "
                 "walls, a big hearth focal point. AVOID: concrete, sea lanterns, quartz, "
                 "glass blocks."),
    "modern": ("Symmetry and clean lines. Large glass, flat surfaces, low profile (slabs "
               "not stairs). Cool light (sea lantern, end rod). Monochrome rugs. "
               "AVOID: cobblestone, fences as legs, torches, mossy blocks."),
    "japanese": ("Calm symmetry, deep eaves, paper-screen glass, cherry/dark wood accents. "
                 "Warm lantern light. Tatami carpets, low furniture. "
                 "AVOID: concrete, bright colours, iron bars, clutter."),
    "cottage": ("Cozy and a little crooked. Oak/spruce timber, flower boxes, a chimney. "
                "Warm lantern light. Inside: hearth, rugs, small kitchen. "
                "AVOID: deepslate, quartz, sea lanterns, monochrome."),
    "desert": ("Flat or stepped roofs, thick sandstone, shaded arcades, small high windows. "
               "Warm lantern light. Terracotta and gold accents. "
               "AVOID: oak as primary, snow, dark wood, large glass walls."),
    "fantasy": ("Tall, slender, a little impossible. Purpur/end-stone/amethyst, glowing "
                "accents. Cool magical light (sea lantern, glowstone). "
                "AVOID: plain cobblestone facades, flat boxes, dirt, vanilla brick."),
    "industrial": ("Function over ornament. Brick and iron, pilaster rhythm, big shuttered "
                   "openings, exposed structure. Lantern/copper-bulb light. "
                   "AVOID: carpets, flowers, fancy trim, pastel colours."),
    "victorian": ("Ornate brick and ironwork, tall narrow windows, chimneys and stacks, "
                  "copper trim. Warm lantern light. "
                  "AVOID: concrete, sea lanterns, flat modern roofs, minimalism."),
    "industrial_victorian": ("Soot-stained brick, riveted iron, copper pipework and tall "
                             "smokestacks. Warm + copper-bulb light. Gritty, busy rooflines. "
                             "AVOID: pastel, carpets, quartz, clean modern glass."),
    "industrial_modern": ("Concrete, steel and glass, exposed ducting, flat parapets, strip "
                          "windows. Cool light (sea lantern, end rod). "
                          "AVOID: timber framing, lanterns everywhere, mossy/cracked blocks."),
    "ruins": ("Broken and overgrown. Cracked/mossy stone, gaps, glow lichen, partial roofs. "
              "Sparse warm light. AVOID: pristine blocks, concrete, full glazing, bright paint."),
    "viking": ("Long low halls, steep timber roofs, stone footings, shields and furs. "
               "Warm hearth light. AVOID: concrete, quartz, large glass, bright dyes."),
}

# Fallback when a style keyword has no card.
DEFAULT_CARD = STYLE_CARDS["cottage"]


def style_card(style: str) -> str:
    key = (style or "").lower()
    for kw, card in STYLE_CARDS.items():
        if kw in key:
            return card
    return DEFAULT_CARD
