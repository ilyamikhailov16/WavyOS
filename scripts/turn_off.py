import os
import sys
import time
import platform


def shutdown():
    """ Выключает пк """

    if sys.platform.startswith('win'):
        os.system("shutdown /s /t 0")
    elif sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
        os.system("shutdown now")
    else:
        print("Неподдерживаемая операционная система")


def shutdown_with_timer(minutes):
    """ Выключает пк через указанное количество минут """

    if minutes < 0:
        raise ValueError("Время не может быть отрицательным")

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
            print("Неподдерживаемая операционная система")
            return
    except KeyboardInterrupt:
        print("Выключение отменено пользователем")
        if system == "Windows":
            os.system("shutdown /a")
        sys.exit(0)
