"""Toggle selected Windows system states and shell pages."""

import subprocess
import time

import keyboard
import pyautogui
import pythoncom
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

from app_logging import get_logger
from config import settings

SYSTEM_TOGGLE_SETTINGS = settings.system_toggle
logger = get_logger(__name__)


def toggle_mute() -> None:
    pythoncom.CoInitialize()
    try:
        speakers = AudioUtilities.GetSpeakers()
        volume = speakers.EndpointVolume.QueryInterface(IAudioEndpointVolume)
        current_mute = volume.GetMute()
        new_mute = not current_mute
        volume.SetMute(new_mute, None)
        logger.info("Mute toggled. New state: %s", "muted" if new_mute else "unmuted")
    except Exception as exc:
        logger.error("Could not toggle mute: %s", exc)
    finally:
        pythoncom.CoUninitialize()


def toggle_wifi() -> None:
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
            capture_output=True,
            text=True,
            encoding="cp1251",
            errors="replace",
            check=True,
        )
        output = result.stdout.strip()
        if "NoWiFi" in output:
            logger.warning("Wi-Fi radio module was not found.")
        else:
            logger.info("Wi-Fi toggled. New state: %s", "on" if "On" in output else "off")
    except subprocess.CalledProcessError as exc:
        logger.error("Wi-Fi PowerShell call failed (%s): %s", exc.returncode, exc.stderr.strip() or "no output")
    except Exception as exc:
        logger.error("Could not toggle Wi-Fi: %s", exc)


def toggle_bluetooth() -> None:
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
            capture_output=True,
            text=True,
            encoding="cp1251",
            errors="replace",
            check=True,
        )
        output = result.stdout.strip()
        if "NoBluetooth" in output:
            logger.warning("Bluetooth adapter was not found.")
        else:
            logger.info("Bluetooth toggled. New state: %s", "on" if "On" in output else "off")
    except Exception as exc:
        logger.error("Could not toggle Bluetooth: %s", exc)


def toggle_airplane_mode() -> None:
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
$access = Await ([Windows.Devices.Radios.Radio]::RequestAccessAsync()) ([Windows.Devices.Radios.RadioAccessStatus])

if ($access -ne 'Allowed') {
    Write-Output "AccessDenied"
    exit
}

$radios = Await ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
$anyRadioOn = $false
foreach ($radio in $radios) {
    if ($radio.Kind -ne 'Cellular' -and $radio.State -eq 'On') {
        $anyRadioOn = $true
        break
    }
}

$newState = if ($anyRadioOn) { 'Off' } else { 'On' }
$newRadioState = [Windows.Devices.Radios.RadioState]::$newState
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
            encoding="cp1251",
            errors="replace",
            timeout=SYSTEM_TOGGLE_SETTINGS.ui.airplane_mode_timeout_seconds,
        )

        output = result.stdout.strip()
        err = result.stderr.strip()
        if "AccessDenied" in output or "AccessDenied" in err:
            logger.warning("Airplane mode toggle requires additional Windows radio/location access.")
            return
        if result.returncode != 0 or err:
            logger.error("Airplane mode PowerShell call failed (%s): %s", result.returncode, err or "no stderr")
            return

        logger.info("Airplane mode toggled. New state: %s", "off" if output == "On" else "on")
    except subprocess.TimeoutExpired:
        logger.error("Airplane mode PowerShell call timed out.")
    except Exception as exc:
        logger.error("Could not toggle airplane mode: %s", exc)


def toggle_notifications() -> None:
    try:
        subprocess.run(["start", SYSTEM_TOGGLE_SETTINGS.ui.notifications_uri], shell=True)
        time.sleep(SYSTEM_TOGGLE_SETTINGS.ui.open_delay_seconds)
        pyautogui.press("space")
        time.sleep(SYSTEM_TOGGLE_SETTINGS.ui.post_toggle_delay_seconds)
        pyautogui.hotkey("alt", "f4")
        logger.info("Notifications page was opened and the main toggle was triggered.")
    except Exception as exc:
        logger.error("Could not toggle notifications via UI automation: %s", exc)
        subprocess.run(["start", SYSTEM_TOGGLE_SETTINGS.ui.notifications_uri], shell=True)


def hotkeys() -> None:
    logger.info("Hotkey mode started.")
    keyboard.add_hotkey(SYSTEM_TOGGLE_SETTINGS.hotkeys.mute, toggle_mute)
    keyboard.add_hotkey(SYSTEM_TOGGLE_SETTINGS.hotkeys.wifi, toggle_wifi)
    keyboard.add_hotkey(SYSTEM_TOGGLE_SETTINGS.hotkeys.bluetooth, toggle_bluetooth)
    keyboard.add_hotkey(SYSTEM_TOGGLE_SETTINGS.hotkeys.airplane_mode, toggle_airplane_mode)
    keyboard.add_hotkey(SYSTEM_TOGGLE_SETTINGS.hotkeys.notifications, toggle_notifications)
    keyboard.wait(SYSTEM_TOGGLE_SETTINGS.hotkeys.exit)
    logger.info("Exiting hotkey mode.")


if __name__ == "__main__":
    hotkeys()
