from blocks import VALID_BLOCKS

MAX_FILL_VOLUME = 32768


def validate_commands(commands: list[str]) -> tuple[bool, list[str]]:
    errors = []
    for i, cmd in enumerate(commands):
        parts = cmd.strip().split()
        if not parts:
            continue
        if parts[0] == "/fill":
            errors.extend(_check_fill(i + 1, parts))
        elif parts[0] == "/setblock":
            errors.extend(_check_setblock(i + 1, parts))
        else:
            errors.append(f"Line {i+1}: Unknown command '{parts[0]}'")
    return len(errors) == 0, errors


def _check_fill(line: int, parts: list[str]) -> list[str]:
    errors = []
    if len(parts) < 8:
        return [f"Line {line}: /fill requires 7 args — got {len(parts) - 1}"]
    try:
        x1, y1, z1 = int(parts[1]), int(parts[2]), int(parts[3])
        x2, y2, z2 = int(parts[4]), int(parts[5]), int(parts[6])
    except ValueError:
        return [f"Line {line}: coordinates must be integers"]

    block = parts[7]

    if y1 < 0 or y2 < 0:
        errors.append(f"Line {line}: Y coordinate below 0 (y1={y1}, y2={y2})")

    volume = abs(x2 - x1 + 1) * abs(y2 - y1 + 1) * abs(z2 - z1 + 1)
    if volume > MAX_FILL_VOLUME:
        errors.append(f"Line {line}: fill volume {volume} exceeds {MAX_FILL_VOLUME}-block limit")

    if not _block_known(block):
        errors.append(f"Line {line}: unknown block '{block}'")

    return errors


def _check_setblock(line: int, parts: list[str]) -> list[str]:
    errors = []
    if len(parts) < 5:
        return [f"Line {line}: /setblock requires 4 args — got {len(parts) - 1}"]
    try:
        _, y, _ = int(parts[1]), int(parts[2]), int(parts[3])
    except ValueError:
        return [f"Line {line}: coordinates must be integers"]

    block = parts[4]

    if y < 0:
        errors.append(f"Line {line}: Y coordinate below 0 (y={y})")

    if not _block_known(block):
        errors.append(f"Line {line}: unknown block '{block}'")

    return errors


def _block_known(block: str) -> bool:
    base = block.split("[")[0]
    return base in VALID_BLOCKS
