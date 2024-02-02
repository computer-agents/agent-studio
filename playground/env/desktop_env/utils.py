import logging
import platform

if platform.system() == "Windows":
    import pygetwindow as gw
else:
    import subprocess


logger = logging.getLogger(__name__)


class WindowManager:
    def __init__(self):
        self.window = None

    def send_to_background(self):
        """Sends the current window to the background."""
        match platform.system():
            case "Linux":
                try:
                    self.window = (
                        subprocess.check_output(["xdotool", "getactivewindow"])
                        .strip()
                        .decode()
                    )
                    subprocess.run(["xdotool", "windowminimize", self.window])
                except subprocess.CalledProcessError:
                    raise RuntimeError(
                        "xdotool is required. Install it with `apt install xdotool`."
                    )
            case "Darwin":
                try:
                    # Get name of the frontmost application
                    get_name_script = (
                        'tell application "System Events" to get name of first '
                        "application process whose frontmost is true"
                    )
                    window_name = (
                        subprocess.check_output(["osascript", "-e", get_name_script])
                        .strip()
                        .decode()
                    )
                    if window_name == "Electron":
                        self.window = "Code"
                    elif window_name == "Terminal":
                        self.window = window_name
                    else:
                        # TODO: handle other window names
                        self.window = window_name
                        logger.warn(
                            f"Unsupported window name {window_name}. "
                            "There may be issues with the window."
                        )
                    # Minimize window
                    minimize_script = (
                        'tell application "System Events" to set visible of '
                        "first application process whose frontmost is true to false"
                    )
                    subprocess.run(["osascript", "-e", minimize_script])
                except subprocess.CalledProcessError:
                    raise RuntimeError(
                        "AppleScript failed to send window to background."
                    )
            case "Windows":
                try:
                    # TODO: find a way to get unique ID
                    fg_window = gw.getActiveWindow()
                    self.window = fg_window.title
                    fg_window.minimize()
                except Exception as e:
                    raise RuntimeError(f"Failed to send window to background: {e}")
            case _:
                raise RuntimeError(f"Unsupported OS {platform.system()}")

    def bring_to_front(self):
        """Brings the minimized window to the front."""
        if not self.window:
            logger.info("No minimized windows to restore.")
            return
        match platform.system():
            case "Linux":
                try:
                    subprocess.run(["xdotool", "windowactivate", self.window])
                except subprocess.CalledProcessError:
                    raise RuntimeError(
                        "xdotool is required. Install it with `apt install xdotool`."
                    )
            case "Darwin":
                try:
                    restore_script = f'tell application "{self.window}" to activate'
                    subprocess.run(["osascript", "-e", restore_script])
                except subprocess.CalledProcessError:
                    raise RuntimeError("AppleScript failed to bring window to front.")
            case "Windows":
                try:
                    # TODO: find a way to restore the window with unique ID
                    window = gw.getWindowsWithTitle(self.window)[0]
                    window.restore()
                except Exception as e:
                    raise RuntimeError(f"Failed to bring window to front: {e}")
            case _:
                raise RuntimeError(f"Unsupported OS {platform.system()}")
