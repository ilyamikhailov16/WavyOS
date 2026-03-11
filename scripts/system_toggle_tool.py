"""
system_toggle_tool.py

Скрипт для переключения системных состояний. Wi-Fi, Bluetooth, звук, airplane mode, уведомления
"""

import subprocess
import logging
import keyboard
import time
import pythoncom
import pyautogui

from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def toggle_mute():
    pythoncom.CoInitialize()
    try:
        speakers = AudioUtilities.GetSpeakers()
        volume = speakers.EndpointVolume.QueryInterface(IAudioEndpointVolume)
        current_mute = volume.GetMute()
        new_mute = not current_mute
        volume.SetMute(new_mute, None)
        status = "выключен (mute)" if new_mute else "включён"
        logger.info(f"[Звук] Переключено → {status}")
    except Exception as e:
        logger.error(f"[Звук] Ошибка: {e}")
    finally:
        pythoncom.CoUninitialize()


def toggle_wifi():
    ps_script = r"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
Function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}
[Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
Await ([Windows.Devices.Radios.Radio]::RequestAccessAsync()) ([Windows.Devices.Radios.RadioAccessStatus]) | Out-Null
$radios = Await ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
$wifi = $radios | ? { $_.Kind -eq 'WiFi' }
if ($wifi) {
    $current = $wifi.State
    if ($current -eq [Windows.Devices.Radios.RadioState]::On) {
        $newState = [Windows.Devices.Radios.RadioState]::Off
    } else {
        $newState = [Windows.Devices.Radios.RadioState]::On
    }
    Await ($wifi.SetStateAsync($newState)) ([Windows.Devices.Radios.RadioAccessStatus]) | Out-Null
    Write-Output $newState
} else {
    Write-Output "NoWiFi"
}
"""

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, encoding='cp1251', errors='replace', check=True
        )
        output = result.stdout.strip()
        if "NoWiFi" in output:
            logger.warning("[Wi-Fi] Радиомодуль не найден")
        else:
            status = "включён" if "On" in output else "выключен"
            logger.info(f"[Wi-Fi] Переключено → {status}")
    except subprocess.CalledProcessError as e:
        logger.error(f"[Wi-Fi] Ошибка PowerShell ({e.returncode}): {e.stderr.strip() or 'нет вывода'}")
        logger.info("Запусти от имени администратора! Если ошибка доступа — включи 'Разрешение на определение местоположения' в Параметры → Конфиденциальность → Расположение")
    except Exception as e:
        logger.error(f"[Wi-Fi] Общая ошибка: {e}")

def toggle_bluetooth():
    ps_script = r"""
if ((Get-Service bthserv).Status -eq 'Stopped') { Start-Service bthserv }
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
Function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}
[Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
Await ([Windows.Devices.Radios.Radio]::RequestAccessAsync()) ([Windows.Devices.Radios.RadioAccessStatus]) | Out-Null
$radios = Await ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
$bt = $radios | ? { $_.Kind -eq 'Bluetooth' }
if ($bt) {
    $current = $bt.State
    if ($current -eq [Windows.Devices.Radios.RadioState]::On) {
        $newState = [Windows.Devices.Radios.RadioState]::Off
    } else {
        $newState = [Windows.Devices.Radios.RadioState]::On
    }
    Await ($bt.SetStateAsync($newState)) ([Windows.Devices.Radios.RadioAccessStatus]) | Out-Null
    Write-Output $newState
} else {
    Write-Output "NoBluetooth"
}
"""

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, encoding='cp1251', errors='replace', check=True
        )
        output = result.stdout.strip()
        if "NoBluetooth" in output:
            logger.warning("[Bluetooth] Адаптер не найден")
        else:
            status = "включён" if "On" in output else "выключен"
            logger.info(f"[Bluetooth] Переключено → {status}")
    except Exception as e:
        logger.error(f"[Bluetooth] Ошибка: {e}")


def toggle_airplane_mode():
    ps_script = r"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]

function Await($asyncTask, $resultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($resultType)
    $netTask = $asTask.Invoke($null, @($asyncTask))
    $netTask.Wait(-1) | Out-Null
    return $netTask.Result
}

[Windows.Devices.Radios.Radio, Windows.System.Devices, ContentType=WindowsRuntime] | Out-Null

# Запрашиваем доступ
$access = Await ([Windows.Devices.Radios.Radio]::RequestAccessAsync()) ([Windows.Devices.Radios.RadioAccessStatus])

if ($access -ne 'Allowed') {
    Write-Output "AccessDenied"
    exit
}

$radios = Await ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])

# Определяем текущее состояние Airplane Mode
$anyRadioOn = $false
foreach ($radio in $radios) {
    if ($radio.Kind -ne 'Cellular' -and $radio.State -eq 'On') {
        $anyRadioOn = $true
        break
    }
}

$newState = if ($anyRadioOn) { 'Off' } else { 'On' }
$newRadioState = [Windows.Devices.Radios.RadioState]::$newState

# Переключаем все не-сотовые радио
foreach ($radio in $radios) {
    if ($radio.Kind -ne 'Cellular') {
        $result = Await ($radio.SetStateAsync($newRadioState)) ([Windows.Devices.Radios.RadioAccessStatus])
    }
}

Write-Output $newState
"""

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding='cp1251',
            errors='replace',
            timeout=15
        )

        output = result.stdout.strip()
        err = result.stderr.strip()

        if "AccessDenied" in output or "AccessDenied" in err:
            logger.warning("[Режим полёта] Требуется разрешение на локацию или доступ к радио")
            logger.info("Включи 'Разрешение на определение местоположения' → Параметры → Конфиденциальность и защита → Расположение (разово)")
            return

        if result.returncode != 0 or err:
            logger.error(f"[Режим полёта] PowerShell ошибка ({result.returncode}): {err or 'нет stderr'}")
            return

        status = "выключён" if output == "On" else "включён"
        logger.info(f"[Режим полёта] Переключено → {status}")

    except subprocess.TimeoutExpired:
        logger.error("[Режим полёта] PowerShell завис >15 сек")
    except Exception as e:
        logger.error(f"[Режим полёта] Ошибка запуска: {e}")

def toggle_notifications():
    try:
        # Открываем страницу уведомлений
        subprocess.run(["start", "ms-settings:notifications"], shell=True)
        time.sleep(1.2)  # ждём открытия окна (на слабом ПК можно 1.5–2.0)

        # Нажимаем SPACE для переключения тумблера (если фокус на нём)
        pyautogui.press('space')
        time.sleep(0.3)

        # Закрываем окно настроек
        pyautogui.hotkey('alt', 'f4')

        logger.info("[Уведомления] Попытка переключения главного тумблера (SPACE)")

    except Exception as e:
        logger.error(f"[Уведомления] Ошибка: {e}")
        logger.info("Fallback: просто открываем настройки")
        subprocess.run(["start", "ms-settings:notifications"], shell=True)

def hotkeys():
    logger.info("=== РЕЖИМ ГОРЯЧИХ КЛАВИШ ===")
    logger.info("  Ctrl+Alt+M  →  звук")
    logger.info("  Ctrl+Alt+W  →  Wi-Fi")
    logger.info("  Ctrl+Alt+B  →  Bluetooth")
    logger.info("  Ctrl+Alt+A  →  режим полёта")
    logger.info("  Ctrl+Alt+N  →  уведомления")
    logger.info("  ESC  →  выход")
    logger.info("----------------------------")

    keyboard.add_hotkey("ctrl+alt+m", toggle_mute)
    keyboard.add_hotkey("ctrl+alt+w", toggle_wifi)
    keyboard.add_hotkey("ctrl+alt+b", toggle_bluetooth)
    keyboard.add_hotkey("ctrl+alt+a", toggle_airplane_mode)
    keyboard.add_hotkey("ctrl+alt+n", toggle_notifications)

    keyboard.wait("esc")
    logger.info("Выход...")


if __name__ == "__main__":
    hotkeys()