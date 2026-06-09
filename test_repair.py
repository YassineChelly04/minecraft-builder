"""Quick correctness checks for the repair layer. Run: python test_repair.py"""
from repair import repair_commands
from validator import validate_commands


def check(name, commands, expect_dropped=0):
    clean, report = repair_commands(commands)
    valid, errors = validate_commands(clean)
    dropped = sum(1 for r in report if r.startswith("dropped"))
    ok = valid and dropped == expect_dropped
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        print("   clean:", clean)
        print("   errors:", errors)
        print("   report:", report)
    return ok


results = []

# 1. Hallucinated block names get corrected, not dropped.
results.append(check("synonym correction", [
    "/fill 0 64 0 5 64 5 minecraft:wood_planks",
    "/setblock 2 65 2 minecraft:glass_block",
    "/fill 0 65 0 5 68 0 minecraft:stone_brick",
]))

# 2. Unknown wood prefix falls back to oak.
results.append(check("family fallback", [
    "/fill 0 64 0 3 64 3 minecraft:pine_planks",
    "/setblock 1 65 1 minecraft:redwood_stairs",
]))

# 3. Near-miss spelling fixed by fuzzy match.
results.append(check("fuzzy match", [
    "/fill 0 64 0 3 64 3 minecraft:cobbleston",
    "/fill 0 64 0 3 64 3 minecraft:sea_lantren",
]))

# 4. Invalid state on a plain cube is stripped (would otherwise be a parse error).
results.append(check("strip bogus state", [
    "/fill 0 64 0 3 64 3 minecraft:stone[facing=north]",
]))

# 5. Valid state on stairs is kept.
clean, _ = repair_commands(["/setblock 1 65 1 minecraft:oak_stairs[facing=east]"])
keep_ok = clean == ["/setblock 1 65 1 minecraft:oak_stairs[facing=east]"]
print(f"[{'PASS' if keep_ok else 'FAIL'}] keep valid stairs state -> {clean}")
results.append(keep_ok)

# 6. Oversized fill is split into engine-legal chunks.
clean, report = repair_commands(["/fill 0 64 0 99 99 99 minecraft:stone"])
valid, _ = validate_commands(clean)
split_ok = valid and len(clean) > 1
print(f"[{'PASS' if split_ok else 'FAIL'}] split oversized fill -> {len(clean)} chunks, valid={valid}")
results.append(split_ok)

# 7. Truly unfixable garbage is dropped, rest survives.
results.append(check("drop unfixable, keep rest", [
    "/fill 0 64 0 3 64 3 minecraft:zzqqxx_nonsense_block",
    "/setblock 1 65 1 minecraft:stone",
], expect_dropped=1))

# 8. Missing minecraft: prefix is added.
results.append(check("add missing prefix", [
    "/fill 0 64 0 3 64 3 oak_planks",
]))

print(f"\n{sum(results)}/{len(results)} groups passed")
exit(0 if all(results) else 1)
