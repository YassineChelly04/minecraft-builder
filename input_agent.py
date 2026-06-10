import time
import pyautogui
import pyperclip


def execute_commands(commands: list[str], delay: float = 0.06,
                     open_delay: float = 0.1) -> None:
    """Type each command into Minecraft chat via keyboard automation.

    NOTE: this is inherently slow (~4-5 commands/second). For more than a few
    hundred commands use the datapack export instead (instant in-game).

    Pressing 'T' opens chat; we wait briefly for it to focus, then select-all +
    backspace to wipe any leaked 't' keystroke before pasting (otherwise commands
    come out as 't/setblock ...'). The clear guard lets the delays stay short.
    """
    pyautogui.PAUSE = 0.02  # trim pyautogui's default 0.1s between every action
    for cmd in commands:
        pyautogui.press("t")             # open chat
        time.sleep(open_delay)           # let it focus
        pyautogui.hotkey("ctrl", "a")    # select any stray content (e.g. a leaked 't')
        pyautogui.press("backspace")     # clear it
        pyperclip.copy(cmd)
        pyautogui.hotkey("ctrl", "v")    # paste the command
        pyautogui.press("enter")
        time.sleep(delay)
