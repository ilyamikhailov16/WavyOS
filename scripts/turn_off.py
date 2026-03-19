import os
import sys
import time
import platform


def shutdown():
    """Shuts down the computer"""

    if sys.platform.startswith("win"):
        os.system("shutdown /s /t 0")
    elif sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
        os.system("shutdown now")
    else:
        print("Unsupported operating system")


def shutdown_with_timer(minutes):
    """Shuts down the computer after the specified number of minutes"""

    if minutes < 0:
        raise ValueError("Time cannot be negative")

    seconds = minutes * 60

    system = platform.system()

    try:
        time.sleep(seconds)

        if system == "Windows":
            os.system("shutdown /s /t 1")
        elif system == "Darwin":
            os.system("osascript -e 'tell app \"System Events\" to shut down'")
        elif system == "Linux":
            os.system("sudo shutdown now")
        else:
            print("Unsupported operating system")
            return
    except KeyboardInterrupt:
        print("Shutdown cancelled by user")
        if system == "Windows":
            os.system("shutdown /a")
        sys.exit(0)
