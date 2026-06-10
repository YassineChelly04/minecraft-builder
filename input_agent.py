import time
import pyautogui
import pyperclip


def execute_commands(commands: list[str], delay: float = 0.15,
                     open_delay: float = 0.2) -> None:
    """Type each command into Minecraft chat via keyboard automation.

    Pressing 'T' opens chat. We must wait for chat to actually open before
    pasting, otherwise the 't' keystroke leaks into the input box and every
    command comes out as 't/setblock ...'. As a belt-and-braces guard we also
    select-all + backspace to clear anything in the box before pasting.
    """
    for cmd in commands:
        pyautogui.press("t")             # open chat
        time.sleep(open_delay)           # let it fully open + focus
        pyautogui.hotkey("ctrl", "a")    # select any stray content (e.g. a leaked 't')
        pyautogui.press("backspace")     # clear it
        pyperclip.copy(cmd)
        pyautogui.hotkey("ctrl", "v")    # paste the command
        time.sleep(0.05)
        pyautogui.press("enter")
        time.sleep(delay)
