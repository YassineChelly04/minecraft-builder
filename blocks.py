"""
Complete valid-block set for /fill and /setblock — Minecraft Java Edition 1.21.x
Only solid, reliably placeable blocks are included.
Gravity blocks (sand, gravel, concrete_powder) are included but agents are instructed not to use them in walls.
"""

VALID_BLOCKS = {

    # ── STONE & MASONRY ─────────────────────────────────────────
    "minecraft:stone", "minecraft:smooth_stone",
    "minecraft:granite", "minecraft:polished_granite",
    "minecraft:diorite", "minecraft:polished_diorite",
    "minecraft:andesite", "minecraft:polished_andesite",
    "minecraft:cobblestone", "minecraft:mossy_cobblestone",
    "minecraft:stone_bricks", "minecraft:mossy_stone_bricks",
    "minecraft:cracked_stone_bricks", "minecraft:chiseled_stone_bricks",
    "minecraft:infested_stone_bricks",
    "minecraft:deepslate", "minecraft:cobbled_deepslate",
    "minecraft:polished_deepslate", "minecraft:chiseled_deepslate",
    "minecraft:deepslate_bricks", "minecraft:cracked_deepslate_bricks",
    "minecraft:deepslate_tiles", "minecraft:cracked_deepslate_tiles",
    "minecraft:calcite", "minecraft:tuff",
    "minecraft:polished_tuff", "minecraft:tuff_bricks", "minecraft:chiseled_tuff",

    # ── SANDSTONE ────────────────────────────────────────────────
    "minecraft:sandstone", "minecraft:smooth_sandstone",
    "minecraft:cut_sandstone", "minecraft:chiseled_sandstone",
    "minecraft:red_sandstone", "minecraft:smooth_red_sandstone",
    "minecraft:cut_red_sandstone", "minecraft:chiseled_red_sandstone",

    # ── QUARTZ ───────────────────────────────────────────────────
    "minecraft:quartz_block", "minecraft:smooth_quartz",
    "minecraft:chiseled_quartz_block", "minecraft:quartz_pillar",
    "minecraft:quartz_bricks",

    # ── BRICKS ───────────────────────────────────────────────────
    "minecraft:bricks",
    "minecraft:mud_bricks",
    "minecraft:nether_bricks", "minecraft:red_nether_bricks",
    "minecraft:cracked_nether_bricks", "minecraft:chiseled_nether_bricks",
    "minecraft:end_stone_bricks",

    # ── NETHER & BASALT ──────────────────────────────────────────
    "minecraft:netherrack", "minecraft:soul_sand", "minecraft:soul_soil",
    "minecraft:basalt", "minecraft:polished_basalt", "minecraft:smooth_basalt",
    "minecraft:blackstone", "minecraft:polished_blackstone",
    "minecraft:chiseled_polished_blackstone",
    "minecraft:polished_blackstone_bricks",
    "minecraft:cracked_polished_blackstone_bricks",
    "minecraft:gilded_blackstone",
    "minecraft:magma_block",
    "minecraft:warped_nylium", "minecraft:crimson_nylium",

    # ── END ──────────────────────────────────────────────────────
    "minecraft:end_stone", "minecraft:end_stone_bricks",
    "minecraft:purpur_block", "minecraft:purpur_pillar",

    # ── PRISMARINE ───────────────────────────────────────────────
    "minecraft:prismarine", "minecraft:prismarine_bricks",
    "minecraft:dark_prismarine", "minecraft:sea_lantern",

    # ── COPPER ───────────────────────────────────────────────────
    "minecraft:copper_block",
    "minecraft:exposed_copper", "minecraft:weathered_copper", "minecraft:oxidized_copper",
    "minecraft:cut_copper",
    "minecraft:exposed_cut_copper", "minecraft:weathered_cut_copper", "minecraft:oxidized_cut_copper",
    "minecraft:waxed_copper_block", "minecraft:waxed_cut_copper",
    "minecraft:waxed_exposed_copper", "minecraft:waxed_weathered_copper",
    "minecraft:waxed_oxidized_copper",

    # ── CUT COPPER STAIRS ────────────────────────────────────────
    "minecraft:cut_copper_stairs",
    "minecraft:exposed_cut_copper_stairs",
    "minecraft:weathered_cut_copper_stairs",
    "minecraft:oxidized_cut_copper_stairs",
    "minecraft:waxed_cut_copper_stairs",
    "minecraft:waxed_exposed_cut_copper_stairs",
    "minecraft:waxed_weathered_cut_copper_stairs",
    "minecraft:waxed_oxidized_cut_copper_stairs",

    # ── CUT COPPER SLABS ─────────────────────────────────────────
    "minecraft:cut_copper_slab",
    "minecraft:exposed_cut_copper_slab",
    "minecraft:weathered_cut_copper_slab",
    "minecraft:oxidized_cut_copper_slab",
    "minecraft:waxed_cut_copper_slab",
    "minecraft:waxed_exposed_cut_copper_slab",
    "minecraft:waxed_weathered_cut_copper_slab",
    "minecraft:waxed_oxidized_cut_copper_slab",

    # ── METALS & GEMS ────────────────────────────────────────────
    "minecraft:iron_block", "minecraft:gold_block",
    "minecraft:diamond_block", "minecraft:emerald_block",
    "minecraft:lapis_block", "minecraft:coal_block",
    "minecraft:netherite_block",
    "minecraft:raw_iron_block", "minecraft:raw_copper_block", "minecraft:raw_gold_block",
    "minecraft:amethyst_block", "minecraft:budding_amethyst",

    # ── SPECIAL / MISC SOLID ─────────────────────────────────────
    "minecraft:air", "minecraft:bedrock", "minecraft:obsidian",
    "minecraft:crying_obsidian", "minecraft:ancient_debris",
    "minecraft:sponge", "minecraft:wet_sponge",
    "minecraft:hay_block", "minecraft:target",
    "minecraft:honey_block", "minecraft:honeycomb_block",

    # ── CONCRETE (16 colours) ────────────────────────────────────
    "minecraft:white_concrete", "minecraft:orange_concrete",
    "minecraft:magenta_concrete", "minecraft:light_blue_concrete",
    "minecraft:yellow_concrete", "minecraft:lime_concrete",
    "minecraft:pink_concrete", "minecraft:gray_concrete",
    "minecraft:light_gray_concrete", "minecraft:cyan_concrete",
    "minecraft:purple_concrete", "minecraft:blue_concrete",
    "minecraft:brown_concrete", "minecraft:green_concrete",
    "minecraft:red_concrete", "minecraft:black_concrete",

    # ── TERRACOTTA (17 — plain + 16 colours) ─────────────────────
    "minecraft:terracotta",
    "minecraft:white_terracotta", "minecraft:orange_terracotta",
    "minecraft:magenta_terracotta", "minecraft:light_blue_terracotta",
    "minecraft:yellow_terracotta", "minecraft:lime_terracotta",
    "minecraft:pink_terracotta", "minecraft:gray_terracotta",
    "minecraft:light_gray_terracotta", "minecraft:cyan_terracotta",
    "minecraft:purple_terracotta", "minecraft:blue_terracotta",
    "minecraft:brown_terracotta", "minecraft:green_terracotta",
    "minecraft:red_terracotta", "minecraft:black_terracotta",

    # ── WOOL (16 colours) ────────────────────────────────────────
    "minecraft:white_wool", "minecraft:orange_wool",
    "minecraft:magenta_wool", "minecraft:light_blue_wool",
    "minecraft:yellow_wool", "minecraft:lime_wool",
    "minecraft:pink_wool", "minecraft:gray_wool",
    "minecraft:light_gray_wool", "minecraft:cyan_wool",
    "minecraft:purple_wool", "minecraft:blue_wool",
    "minecraft:brown_wool", "minecraft:green_wool",
    "minecraft:red_wool", "minecraft:black_wool",

    # ── CARPET (16 colours) ──────────────────────────────────────
    "minecraft:white_carpet", "minecraft:orange_carpet",
    "minecraft:magenta_carpet", "minecraft:light_blue_carpet",
    "minecraft:yellow_carpet", "minecraft:lime_carpet",
    "minecraft:pink_carpet", "minecraft:gray_carpet",
    "minecraft:light_gray_carpet", "minecraft:cyan_carpet",
    "minecraft:purple_carpet", "minecraft:blue_carpet",
    "minecraft:brown_carpet", "minecraft:green_carpet",
    "minecraft:red_carpet", "minecraft:black_carpet",

    # ── GLASS ────────────────────────────────────────────────────
    "minecraft:glass", "minecraft:tinted_glass", "minecraft:glass_pane",
    "minecraft:white_stained_glass", "minecraft:orange_stained_glass",
    "minecraft:magenta_stained_glass", "minecraft:light_blue_stained_glass",
    "minecraft:yellow_stained_glass", "minecraft:lime_stained_glass",
    "minecraft:pink_stained_glass", "minecraft:gray_stained_glass",
    "minecraft:light_gray_stained_glass", "minecraft:cyan_stained_glass",
    "minecraft:purple_stained_glass", "minecraft:blue_stained_glass",
    "minecraft:brown_stained_glass", "minecraft:green_stained_glass",
    "minecraft:red_stained_glass", "minecraft:black_stained_glass",
    "minecraft:white_stained_glass_pane", "minecraft:orange_stained_glass_pane",
    "minecraft:magenta_stained_glass_pane", "minecraft:light_blue_stained_glass_pane",
    "minecraft:yellow_stained_glass_pane", "minecraft:lime_stained_glass_pane",
    "minecraft:pink_stained_glass_pane", "minecraft:gray_stained_glass_pane",
    "minecraft:light_gray_stained_glass_pane", "minecraft:cyan_stained_glass_pane",
    "minecraft:purple_stained_glass_pane", "minecraft:blue_stained_glass_pane",
    "minecraft:brown_stained_glass_pane", "minecraft:green_stained_glass_pane",
    "minecraft:red_stained_glass_pane", "minecraft:black_stained_glass_pane",

    # ── WOOD PLANKS ──────────────────────────────────────────────
    "minecraft:oak_planks", "minecraft:spruce_planks",
    "minecraft:birch_planks", "minecraft:jungle_planks",
    "minecraft:acacia_planks", "minecraft:dark_oak_planks",
    "minecraft:mangrove_planks", "minecraft:cherry_planks",
    "minecraft:bamboo_planks", "minecraft:crimson_planks",
    "minecraft:warped_planks",

    # ── LOGS ─────────────────────────────────────────────────────
    "minecraft:oak_log", "minecraft:spruce_log",
    "minecraft:birch_log", "minecraft:jungle_log",
    "minecraft:acacia_log", "minecraft:dark_oak_log",
    "minecraft:mangrove_log", "minecraft:cherry_log",
    "minecraft:stripped_oak_log", "minecraft:stripped_spruce_log",
    "minecraft:stripped_birch_log", "minecraft:stripped_jungle_log",
    "minecraft:stripped_acacia_log", "minecraft:stripped_dark_oak_log",
    "minecraft:stripped_mangrove_log", "minecraft:stripped_cherry_log",
    "minecraft:stripped_oak_wood", "minecraft:stripped_spruce_wood",
    "minecraft:stripped_birch_wood", "minecraft:stripped_jungle_wood",
    "minecraft:stripped_acacia_wood", "minecraft:stripped_dark_oak_wood",
    "minecraft:oak_wood", "minecraft:spruce_wood",
    "minecraft:birch_wood", "minecraft:jungle_wood",
    "minecraft:acacia_wood", "minecraft:dark_oak_wood",
    "minecraft:mangrove_wood", "minecraft:cherry_wood",
    "minecraft:crimson_stem", "minecraft:warped_stem",
    "minecraft:stripped_crimson_stem", "minecraft:stripped_warped_stem",

    # ── STAIRS (all variants) ────────────────────────────────────
    "minecraft:oak_stairs", "minecraft:spruce_stairs",
    "minecraft:birch_stairs", "minecraft:jungle_stairs",
    "minecraft:acacia_stairs", "minecraft:dark_oak_stairs",
    "minecraft:mangrove_stairs", "minecraft:cherry_stairs",
    "minecraft:bamboo_stairs", "minecraft:crimson_stairs",
    "minecraft:warped_stairs",
    "minecraft:stone_stairs", "minecraft:cobblestone_stairs",
    "minecraft:mossy_cobblestone_stairs",
    "minecraft:stone_brick_stairs", "minecraft:mossy_stone_brick_stairs",
    "minecraft:granite_stairs", "minecraft:polished_granite_stairs",
    "minecraft:diorite_stairs", "minecraft:polished_diorite_stairs",
    "minecraft:andesite_stairs", "minecraft:polished_andesite_stairs",
    "minecraft:sandstone_stairs", "minecraft:smooth_sandstone_stairs",
    "minecraft:red_sandstone_stairs", "minecraft:smooth_red_sandstone_stairs",
    "minecraft:quartz_stairs", "minecraft:smooth_quartz_stairs",
    "minecraft:nether_brick_stairs", "minecraft:red_nether_brick_stairs",
    "minecraft:purpur_stairs", "minecraft:end_stone_brick_stairs",
    "minecraft:prismarine_stairs", "minecraft:prismarine_brick_stairs",
    "minecraft:dark_prismarine_stairs",
    "minecraft:blackstone_stairs", "minecraft:polished_blackstone_stairs",
    "minecraft:polished_blackstone_brick_stairs",
    "minecraft:cobbled_deepslate_stairs", "minecraft:polished_deepslate_stairs",
    "minecraft:deepslate_brick_stairs", "minecraft:deepslate_tile_stairs",
    "minecraft:mud_brick_stairs",
    "minecraft:tuff_stairs", "minecraft:tuff_brick_stairs",
    "minecraft:polished_tuff_stairs",

    # ── SLABS (all variants) ─────────────────────────────────────
    "minecraft:oak_slab", "minecraft:spruce_slab",
    "minecraft:birch_slab", "minecraft:jungle_slab",
    "minecraft:acacia_slab", "minecraft:dark_oak_slab",
    "minecraft:mangrove_slab", "minecraft:cherry_slab",
    "minecraft:bamboo_slab", "minecraft:crimson_slab",
    "minecraft:warped_slab",
    "minecraft:stone_slab", "minecraft:smooth_stone_slab",
    "minecraft:cobblestone_slab",
    "minecraft:stone_brick_slab", "minecraft:mossy_stone_brick_slab",
    "minecraft:granite_slab", "minecraft:polished_granite_slab",
    "minecraft:diorite_slab", "minecraft:polished_diorite_slab",
    "minecraft:andesite_slab", "minecraft:polished_andesite_slab",
    "minecraft:sandstone_slab", "minecraft:smooth_sandstone_slab",
    "minecraft:red_sandstone_slab", "minecraft:smooth_red_sandstone_slab",
    "minecraft:quartz_slab", "minecraft:smooth_quartz_slab",
    "minecraft:nether_brick_slab", "minecraft:red_nether_brick_slab",
    "minecraft:purpur_slab", "minecraft:prismarine_slab",
    "minecraft:prismarine_brick_slab", "minecraft:dark_prismarine_slab",
    "minecraft:blackstone_slab", "minecraft:polished_blackstone_slab",
    "minecraft:polished_blackstone_brick_slab",
    "minecraft:cobbled_deepslate_slab", "minecraft:polished_deepslate_slab",
    "minecraft:deepslate_brick_slab", "minecraft:deepslate_tile_slab",
    "minecraft:mud_brick_slab",
    "minecraft:tuff_slab", "minecraft:tuff_brick_slab",
    "minecraft:polished_tuff_slab",
    "minecraft:petrified_oak_slab",

    # ── WALLS (all variants) ─────────────────────────────────────
    "minecraft:cobblestone_wall", "minecraft:mossy_cobblestone_wall",
    "minecraft:stone_brick_wall", "minecraft:mossy_stone_brick_wall",
    "minecraft:brick_wall", "minecraft:granite_wall",
    "minecraft:diorite_wall", "minecraft:andesite_wall",
    "minecraft:sandstone_wall", "minecraft:red_sandstone_wall",
    "minecraft:nether_brick_wall", "minecraft:red_nether_brick_wall",
    "minecraft:end_stone_brick_wall", "minecraft:prismarine_wall",
    "minecraft:blackstone_wall", "minecraft:polished_blackstone_wall",
    "minecraft:polished_blackstone_brick_wall",
    "minecraft:cobbled_deepslate_wall", "minecraft:polished_deepslate_wall",
    "minecraft:deepslate_brick_wall", "minecraft:deepslate_tile_wall",
    "minecraft:mud_brick_wall",
    "minecraft:tuff_wall", "minecraft:tuff_brick_wall",
    "minecraft:polished_tuff_wall",

    # ── FENCES ───────────────────────────────────────────────────
    "minecraft:oak_fence", "minecraft:spruce_fence",
    "minecraft:birch_fence", "minecraft:jungle_fence",
    "minecraft:acacia_fence", "minecraft:dark_oak_fence",
    "minecraft:mangrove_fence", "minecraft:cherry_fence",
    "minecraft:bamboo_fence", "minecraft:crimson_fence",
    "minecraft:warped_fence", "minecraft:nether_brick_fence",
    "minecraft:iron_bars",

    # ── TRAPDOORS ────────────────────────────────────────────────
    "minecraft:oak_trapdoor", "minecraft:spruce_trapdoor",
    "minecraft:birch_trapdoor", "minecraft:jungle_trapdoor",
    "minecraft:acacia_trapdoor", "minecraft:dark_oak_trapdoor",
    "minecraft:mangrove_trapdoor", "minecraft:cherry_trapdoor",
    "minecraft:bamboo_trapdoor", "minecraft:crimson_trapdoor",
    "minecraft:warped_trapdoor", "minecraft:iron_trapdoor",

    # ── DOORS (lower half only — upper auto-generates) ───────────
    "minecraft:oak_door", "minecraft:spruce_door",
    "minecraft:birch_door", "minecraft:jungle_door",
    "minecraft:acacia_door", "minecraft:dark_oak_door",
    "minecraft:mangrove_door", "minecraft:cherry_door",
    "minecraft:bamboo_door", "minecraft:crimson_door",
    "minecraft:warped_door", "minecraft:iron_door",

    # ── LIGHTING ─────────────────────────────────────────────────
    "minecraft:glowstone", "minecraft:sea_lantern",
    "minecraft:shroomlight", "minecraft:redstone_lamp",
    "minecraft:lantern", "minecraft:soul_lantern",
    "minecraft:jack_o_lantern", "minecraft:magma_block",
    "minecraft:froglight",

    # ── BEDS (16 colours) ────────────────────────────────────────
    "minecraft:white_bed", "minecraft:orange_bed",
    "minecraft:magenta_bed", "minecraft:light_blue_bed",
    "minecraft:yellow_bed", "minecraft:lime_bed",
    "minecraft:pink_bed", "minecraft:gray_bed",
    "minecraft:light_gray_bed", "minecraft:cyan_bed",
    "minecraft:purple_bed", "minecraft:blue_bed",
    "minecraft:brown_bed", "minecraft:green_bed",
    "minecraft:red_bed", "minecraft:black_bed",

    # ── PRESSURE PLATES ──────────────────────────────────────────
    "minecraft:oak_pressure_plate", "minecraft:spruce_pressure_plate",
    "minecraft:birch_pressure_plate", "minecraft:jungle_pressure_plate",
    "minecraft:acacia_pressure_plate", "minecraft:dark_oak_pressure_plate",
    "minecraft:mangrove_pressure_plate", "minecraft:cherry_pressure_plate",
    "minecraft:bamboo_pressure_plate", "minecraft:crimson_pressure_plate",
    "minecraft:warped_pressure_plate",
    "minecraft:stone_pressure_plate",
    "minecraft:polished_blackstone_pressure_plate",

    # ── FUNCTIONAL BLOCKS ────────────────────────────────────────
    "minecraft:crafting_table", "minecraft:furnace",
    "minecraft:blast_furnace", "minecraft:smoker",
    "minecraft:chest", "minecraft:trapped_chest",
    "minecraft:ender_chest", "minecraft:barrel",
    "minecraft:bookshelf", "minecraft:chiseled_bookshelf",
    "minecraft:lectern", "minecraft:enchanting_table",
    "minecraft:anvil", "minecraft:chipped_anvil", "minecraft:damaged_anvil",
    "minecraft:grindstone", "minecraft:smithing_table",
    "minecraft:stonecutter", "minecraft:cartography_table",
    "minecraft:fletching_table", "minecraft:loom",
    "minecraft:composter", "minecraft:cauldron",
    "minecraft:brewing_stand", "minecraft:beacon",
    "minecraft:conduit", "minecraft:jukebox",
    "minecraft:note_block",

    # ── FIRE & COOKING ───────────────────────────────────────────
    "minecraft:campfire", "minecraft:soul_campfire",

    # ── REDSTONE / MECHANICAL ────────────────────────────────────
    "minecraft:hopper", "minecraft:dropper", "minecraft:dispenser",
    "minecraft:observer", "minecraft:piston", "minecraft:sticky_piston",
    "minecraft:redstone_block", "minecraft:target",
    "minecraft:tnt",

    # ── NATURE / GROUND ──────────────────────────────────────────
    "minecraft:dirt", "minecraft:coarse_dirt", "minecraft:rooted_dirt",
    "minecraft:grass_block", "minecraft:podzol", "minecraft:mycelium",
    "minecraft:farmland", "minecraft:mud", "minecraft:packed_mud",
    "minecraft:clay", "minecraft:gravel",
    "minecraft:sand", "minecraft:red_sand",
    "minecraft:snow_block", "minecraft:ice",
    "minecraft:packed_ice", "minecraft:blue_ice",

    # ── STRIPPED WOOD (interior panelling) ───────────────────────
    "minecraft:stripped_oak_log", "minecraft:stripped_spruce_log",
    "minecraft:stripped_birch_log", "minecraft:stripped_jungle_log",
    "minecraft:stripped_acacia_log", "minecraft:stripped_dark_oak_log",
    "minecraft:stripped_mangrove_log", "minecraft:stripped_cherry_log",
    "minecraft:stripped_oak_wood", "minecraft:stripped_spruce_wood",
    "minecraft:stripped_birch_wood", "minecraft:stripped_acacia_wood",
    "minecraft:stripped_dark_oak_wood",
}
