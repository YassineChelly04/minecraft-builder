import os
import threading
import time


class ExecControl:
    """Pause/resume/stop switch for a running placement, shared between the
    /execute request thread (which loops over commands) and /execute_control
    (which flips the flags from the UI's Pause button). One placement runs at
    a time, so a single module-level instance is enough."""

    def __init__(self):
        self._resume = threading.Event()   # set = running, cleared = paused
        self._resume.set()
        self._stop = threading.Event()
        self.placed = 0
        self.total = 0

    def reset(self, total: int) -> None:
        self._resume.set()
        self._stop.clear()
        self.placed = 0
        self.total = total

    def pause(self) -> None:
        self._resume.clear()

    def resume(self) -> None:
        self._resume.set()

    def stop(self) -> None:
        self._stop.set()
        self._resume.set()   # unblock a paused loop so it can exit

    def proceed(self) -> bool:
        """Block while paused; return False once stopped."""
        self._resume.wait()
        return not self._stop.is_set()

    def status(self) -> dict:
        return {"paused": not self._resume.is_set(),
                "stopped": self._stop.is_set(),
                "placed": self.placed, "total": self.total}


CONTROL = ExecControl()


def rcon_available() -> bool:
    """RCON execution is enabled by setting RCON_PASSWORD (host/port optional).
    Same envs as a vanilla server.properties: enable-rcon=true, rcon.password=..."""
    return bool(os.environ.get("RCON_PASSWORD"))


def execute_via_rcon(commands: list[str]) -> int:
    """Send commands straight to the server over RCON — no window focus, no typing.
    Throughput is set by RCON_RATE (default 150 cmd/s, >10x keyboard placement).
    Returns the number of commands executed."""
    from execution.rcon_client import RconClient

    host = os.environ.get("RCON_HOST", "127.0.0.1")
    port = int(os.environ.get("RCON_PORT", "25575"))
    rate = int(os.environ.get("RCON_RATE", "150"))
    delay = 1.0 / max(1, rate)
    n = 0
    with RconClient(host, port, os.environ["RCON_PASSWORD"]) as rc:
        for cmd in commands:
            if not CONTROL.proceed():
                break
            rc.run(cmd)
            n += 1
            CONTROL.placed = n
            time.sleep(delay)
    return n


def execute_commands(commands: list[str], delay: float | None = None,
                     open_delay: float | None = None) -> int:
    """Type each command into Minecraft chat via keyboard automation.

    Keyboard placement is inherently one-command-at-a-time, so it can never be
    instant: even tuned, expect ~10-14 commands/second. For thousands of commands
    use the datapack export instead (it runs the whole build in-game in < 1s).

    Speed knobs (env-overridable for fast/slow machines):
      INPUT_OPEN_DELAY  pause after opening chat so it can grab focus  (default 0.015s)
      INPUT_DELAY       pause after sending a command                  (default 0.007s)
    Lower them for more speed; raise them if commands start getting dropped.

    The loop consults CONTROL before every command, so the UI's Pause/Stop
    buttons take effect within one keystroke cycle. Returns commands placed.

    Pressing 'T' opens chat; we wait briefly for it to focus, then select-all +
    backspace to wipe any leaked 't' keystroke before pasting (otherwise commands
    come out as 't/setblock ...'). That guard is what lets the delays stay short.
    """
    import pyautogui   # lazy: lets RCON-only/headless setups run without GUI libs
    import pyperclip

    if open_delay is None:
        open_delay = float(os.environ.get("INPUT_OPEN_DELAY", "0.015"))
    if delay is None:
        delay = float(os.environ.get("INPUT_DELAY", "0.007"))

    pyautogui.PAUSE = 0  # drop pyautogui's implicit per-action sleep; we pace manually
    n = 0
    for cmd in commands:
        if not CONTROL.proceed():        # honours the UI Pause/Stop buttons
            break
        pyautogui.press("t")             # open chat
        if open_delay:
            time.sleep(open_delay)       # let it focus
        pyautogui.hotkey("ctrl", "a")    # select any stray content (e.g. a leaked 't')
        pyautogui.press("backspace")     # clear it
        pyperclip.copy(cmd)
        pyautogui.hotkey("ctrl", "v")    # paste the command
        pyautogui.press("enter")
        n += 1
        CONTROL.placed = n
        if delay:
            time.sleep(delay)
    return n
