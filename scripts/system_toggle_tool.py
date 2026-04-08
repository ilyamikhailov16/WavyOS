"""Toggle selected Windows system states and shell pages."""

import subprocess
import time
import ctypes

import keyboard
import pyautogui
import pythoncom
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

from app_logging import get_logger
from config import settings

SYSTEM_TOGGLE_SETTINGS = settings.system_toggle
logger = get_logger(__name__)

import logging
logger.setLevel(logging.DEBUG)

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
$adapter = Get-NetAdapter | Where-Object { $_.PhysicalMediaType -eq 'Native 802.11' } | Select-Object -First 1
if (-not $adapter) { Write-Output "NoWiFi"; exit 0 }

$isOn = $adapter.Status -eq 'Up'
$target = if ($isOn) { 'disable' } else { 'enable' }

try {
    netsh interface set interface name="$($adapter.Name)" admin=$target 2>$null
    Start-Sleep -Milliseconds 3000
    $verify = Get-NetAdapter -Name $adapter.Name -ErrorAction SilentlyContinue
    $actualOn = $verify.Status -eq 'Up'
    Write-Output $(if ($actualOn) { "On" } else { "Off" })
} catch {
    Write-Output $(if ($isOn) { "On" } else { "Off" })
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
            new_state = "on" if "On" in output else "off"
            logger.info("Wi-Fi toggled. New state: %s", new_state)
            # ℹ️ Информационное примечание о возможном поведении плитки на некоторых сборках Win 11
            if new_state == "off":
                logger.debug("Note: On some Windows 11 builds, the Wi-Fi tile may disappear from Quick Settings after programmatic toggle. To restore: Settings → Network & Internet → Wi-Fi → toggle On.")
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
$ErrorActionPreference = 'Stop'

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class NativeMethods {
    [DllImport("ole32.dll")] public static extern int CoInitialize(IntPtr pv);
    [DllImport("ole32.dll")] public static extern void CoUninitialize();
    [DllImport("ole32.dll")] public static extern uint CoCreateInstance(Guid clsid, IntPtr pv, uint ctx, Guid iid, out IntPtr ppv);
}
[UnmanagedFunctionPointer(CallingConvention.StdCall)] public delegate int GetSystemRadioStateDelegate(IntPtr cg, out int ie, out int se, out int p3);
[UnmanagedFunctionPointer(CallingConvention.StdCall)] public delegate int SetSystemRadioStateDelegate(IntPtr ptr, int state);
[UnmanagedFunctionPointer(CallingConvention.StdCall)] public delegate int ReleaseDelegate(IntPtr ptr);
'@

$CLSID = '581333F6-28DB-41BE-BC7A-FF201F12F3F6'
$IID   = 'DB3AFBFB-08E6-46C6-AA70-BF9A34C30AB7'
$mrs   = [System.Runtime.InteropServices.Marshal]
$comPtr = [IntPtr]::Zero

try {
    $hr = [NativeMethods]::CoInitialize(0)
    if ($hr -ne 0 -and $hr -ne 1) { throw "CoInitialize failed" }

    $hr = [NativeMethods]::CoCreateInstance([Guid]::Parse($CLSID), [IntPtr]::Zero, 4, [Guid]::Parse($IID), [ref]$comPtr)
    if ($hr -ne 0) { throw "CoCreateInstance failed: 0x$($hr.ToString('X8'))" }

    $vtablePtr = $mrs::ReadIntPtr($comPtr)
    $vtable = [IntPtr[]]::new(8)
    $mrs::Copy($vtablePtr, $vtable, 0, $vtable.Length)

    $release = $mrs::GetDelegateForFunctionPointer($vtable[2], [ReleaseDelegate])

    $getState = $mrs::GetDelegateForFunctionPointer($vtable[5], [GetSystemRadioStateDelegate])
    $setState = $mrs::GetDelegateForFunctionPointer($vtable[6], [SetSystemRadioStateDelegate])

    $oldState, $p2, $p3 = 0, 0, 0
    $hr = $getState.Invoke($comPtr, [ref]$oldState, [ref]$p2, [ref]$p3)
    if ($hr -ne 0) { throw "GetState failed" }

    $newState = if ($oldState -eq 0) { 1 } else { 0 }
    $hr = $setState.Invoke($comPtr, $newState)
    if ($hr -ne 0) { throw "SetState failed" }

    $null = $release.Invoke($comPtr)
    Write-Output $(if ($newState -eq 1) { "Off" } else { "On" })

} catch {
    Write-Output "AccessDenied"
}
finally {
    [NativeMethods]::CoUninitialize()
}
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
            logger.warning("Airplane mode toggle requires administrator privileges.")
            return
        if result.returncode != 0 and err and "AccessDenied" not in err:
            logger.error("Airplane mode PowerShell call failed (%s): %s", result.returncode, err)
            return

        logger.info("Airplane mode toggled (COM). New state: %s", output.lower())

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
    if not(bool(ctypes.windll.shell32.IsUserAnAdmin())):
        logger.error("This script requires administrative privileges.")
    logger.info("IsAdmin: %s", bool(ctypes.windll.shell32.IsUserAnAdmin()))

    hotkeys()
