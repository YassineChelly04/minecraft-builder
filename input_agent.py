import time
import pyautogui
import pyperclip


def execute_commands(commands: list[str], delay: float = 0.4) -> None:
    for cmd in commands:
        pyautogui.press("t")
        time.sleep(0.15)
        pyperclip.copy(cmd)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.1)
        pyautogui.press("enter")
        time.sleep(delay)
