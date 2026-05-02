import asyncio
import subprocess
from pathlib import Path
import time
from urllib.parse import quote_plus
import winreg

import psutil
import pyautogui
import win32con
import win32gui
import win32process
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app_logging import get_logger
from config import settings, _load_root_config


BROWSER_SETTINGS = settings.browser
PRESETS = BROWSER_SETTINGS.presets
PROCESS_NAMES = BROWSER_SETTINGS.process_names
DEFAULT_TIMEOUT_MS = BROWSER_SETTINGS.timeouts.default_timeout_ms
DEFAULT_WAIT_AFTER_MS = BROWSER_SETTINGS.timeouts.default_wait_after_ms
logger = get_logger(__name__)


def resolve_config(website_name: str, input_selector: str | None = None) -> tuple[str, str | None]:
    if BROWSER_SETTINGS.custom.search_preset:
        preset = PRESETS.get(BROWSER_SETTINGS.custom.search_preset)
        if preset:
            url = preset.url
            input_selector = input_selector or preset.input_selector
            return url, input_selector

    preset = PRESETS.get(website_name)
    if preset:
        url = preset.url
        input_selector = input_selector or preset.input_selector
    else:
        url = website_name if website_name.startswith("http") else f"https://{website_name}"
        
    return url, input_selector


def build_direct_search_url(website_name: str, query: str | None, input_selector: str | None, submit_selector: str | None) -> str | None:
    if not query:
        return None
    if input_selector or submit_selector:
        return None

    preset = PRESETS.get(website_name)
    search_url = preset.search_url if preset else None
    if not search_url:
        return None
    return search_url.format(query=quote_plus(query))


def get_windows_default_browser_progid() -> str | None:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            BROWSER_SETTINGS.registry.default_browser_progid_key,
        ) as key:
            progid, _ = winreg.QueryValueEx(key, "ProgId")
            return progid
    except OSError:
        return None


def find_custom_browser_executable(browser_name: str) -> Path | None:
    for path in BROWSER_SETTINGS.paths.for_browser(browser_name):
        if path.exists():
            return path
    return None


def map_progid_to_browser(progid: str) -> str | None:
    if progid in BROWSER_SETTINGS.registry.progid_to_browser:
        return BROWSER_SETTINGS.registry.progid_to_browser[progid]
    if progid.startswith("Opera"):
        return "opera"
    if "Yandex" in progid:
        return "yandex"
    return None


def find_running_browser_window(browser_key: str) -> int | None:
    process_names = PROCESS_NAMES.for_browser(browser_key)
    if not process_names:
        return None

    matching_pids = {
        proc.info["pid"]
        for proc in psutil.process_iter(["pid", "name"])
        if (proc.info.get("name") or "").lower() in process_names
    }
    if not matching_pids:
        return None

    found_hwnd: int | None = None

    def callback(hwnd: int, _: object) -> bool:
        nonlocal found_hwnd
        if found_hwnd is not None:
            return False
        if not win32gui.IsWindowVisible(hwnd):
            return True

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid not in matching_pids:
            return True

        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True

        found_hwnd = hwnd
        return False

    win32gui.EnumWindows(callback, None)
    return found_hwnd


def focus_existing_browser_window(hwnd: int) -> bool:
    try:
        if win32gui.IsIconic(hwnd):
            logger.info("The existing browser window is minimized. Restoring it before reuse.")
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.4)
        return True
    except Exception as exc:
        logger.warning("Could not focus the existing browser window: %s", exc)
        return False


def get_launch_command_for_browser(browser_key: str) -> list[str] | None:
    launch_command = BROWSER_SETTINGS.runtime.launch_command_for(browser_key)
    if launch_command:
        return launch_command
    if browser_key in {"opera", "yandex"}:
        executable_path = find_custom_browser_executable(browser_key)
        if executable_path:
            return [str(executable_path)]
    if browser_key == "chromium":
        return None
    return None


def open_url_in_existing_browser(browser_key: str, target_url: str) -> bool:
    hwnd = find_running_browser_window(browser_key)
    if hwnd is None:
        return False

    logger.info("An existing browser window was found. Requesting the browser to open a new URL.")
    launch_command = get_launch_command_for_browser(browser_key)

    try:
        if launch_command:
            subprocess.Popen([*launch_command, target_url])
            return True

        if focus_existing_browser_window(hwnd):
            pyautogui.hotkey("ctrl", "t")
            time.sleep(0.4)
            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.2)
            pyautogui.write(target_url, interval=0.01)
            pyautogui.press("enter")
            return True
    except Exception as exc:
        logger.warning("Could not open a URL in the existing browser window: %s", exc)

    return False


def resolve_browser_launch_options(
    browser: str, headed: bool
) -> tuple[str, dict[str, str | bool], str, str]:
    if browser == "chromium":
        logger.info("Browser selection: explicit Playwright Chromium.")
        return (
            "chromium",
            {"headless": not headed},
            BROWSER_SETTINGS.runtime.display_name_for("chromium"),
            "chromium",
        )
    if browser == "firefox":
        logger.info("Browser selection: explicit Playwright Firefox.")
        return (
            "firefox",
            {"headless": not headed},
            BROWSER_SETTINGS.runtime.display_name_for("firefox"),
            "firefox",
        )
    if browser == "webkit":
        logger.info("Browser selection: explicit Playwright WebKit.")
        return (
            "webkit",
            {"headless": not headed},
            BROWSER_SETTINGS.runtime.display_name_for("webkit"),
            "webkit",
        )
    if browser == "chrome":
        logger.info("Browser selection: explicit Google Chrome channel.")
        return (
            "chromium",
            {
                "headless": not headed,
                "channel": BROWSER_SETTINGS.runtime.playwright_channel_for("chrome"),
            },
            BROWSER_SETTINGS.runtime.display_name_for("chrome"),
            "chrome",
        )
    if browser == "edge":
        logger.info("Browser selection: explicit Microsoft Edge channel.")
        return (
            "chromium",
            {
                "headless": not headed,
                "channel": BROWSER_SETTINGS.runtime.playwright_channel_for("edge"),
            },
            BROWSER_SETTINGS.runtime.display_name_for("edge"),
            "edge",
        )
    if browser in {"opera", "yandex"}:
        executable_path = find_custom_browser_executable(browser)
        readable_name = BROWSER_SETTINGS.runtime.display_name_for(browser)
        if executable_path:
            logger.info("Browser selection: explicit %s executable.", readable_name)
            logger.info("Playwright will launch via executable: %s", executable_path)
            return (
                "chromium",
                {"headless": not headed, "executable_path": str(executable_path)},
                readable_name,
                browser,
            )
        logger.warning("%s executable was not found in the standard Windows paths.", readable_name)
        logger.warning("Fallback selected: Playwright Chromium will be used.")
        return "chromium", {"headless": not headed}, "Playwright Chromium", "chromium"

    if browser == "custom":
        custom_cfg = BROWSER_SETTINGS.custom
        executable_path = Path(custom_cfg.path).expanduser() if custom_cfg.path else None

        if executable_path and executable_path.exists():
            engine = custom_cfg.engine
            logger.info("Browser selection: custom %s-compatible browser", engine)
            logger.info("Executable: %s", executable_path)
            return (
                engine,
                {"headless": not headed, "executable_path": str(executable_path)},
                f"Custom Browser ({executable_path.name})",
                "custom",
            )
        else:
            logger.warning("Custom browser path invalid or empty: %s", executable_path)
            logger.warning("Fallback selected: Playwright Chromium will be used.")
            return "chromium", {"headless": not headed}, "Playwright Chromium", "chromium"

    progid = get_windows_default_browser_progid()
    if progid:
        browser_key = map_progid_to_browser(progid)
        if browser_key:
            readable_name = BROWSER_SETTINGS.runtime.display_name_for(browser_key)
            logger.info("Windows default browser detected: %s (%s)", readable_name, progid)

            if browser_key in {"edge", "chrome", "firefox"}:
                return resolve_browser_launch_options(browser=browser_key, headed=headed)

            executable_path = find_custom_browser_executable(browser_key)
            if executable_path:
                logger.info(
                    "Playwright will launch the installed %s browser via executable path.",
                    readable_name,
                )
                logger.info("Executable path: %s", executable_path)
                return (
                    "chromium",
                    {"headless": not headed, "executable_path": str(executable_path)},
                    readable_name,
                    browser_key,
                )

            logger.warning("%s is the Windows default browser, but its executable was not found.", readable_name)
            logger.warning(
                "Fallback selected: Playwright Chromium will be used instead of the system default browser."
            )
            return "chromium", {"headless": not headed}, "Playwright Chromium", "chromium"

        logger.warning(
            "Windows default browser '%s' is not mapped yet.", progid
        )
        logger.warning(
            "Fallback selected: Playwright Chromium will be used instead of the system default browser."
        )
    else:
        logger.warning(
            "Could not detect the Windows default browser."
        )
        logger.warning(
            "Fallback selected: Playwright Chromium will be used."
        )

    return "chromium", {"headless": not headed}, "Playwright Chromium", "chromium"


async def open_in_browser(
    website_name: str,
    query: str | None = None,
    input_selector: str | None = None,
    submit_selector: str | None = None,
    browser: str = "default",
    headed: bool = True,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    wait_after_ms: int = DEFAULT_WAIT_AFTER_MS,
    screenshot: str | None = None,
) -> None:
    """
    Open a website in a browser and optionally perform a query using Playwright.
    
    :param website_name: Domain name or preset engine name (e.g., 'google', 'example.com')
    :param query: Optional text to enter into the target field.
    :param input_selector: Optional CSS selector for the input field. Overrides preset selector.
    :param submit_selector: Optional CSS selector for a submit button. If omitted, Enter is pressed.
    :param browser: Browser to launch. 'default' resolves the Windows default browser.
    :param headed: Whether to show the browser window (False for headless).
    :param timeout_ms: Timeout for page actions in milliseconds.
    :param wait_after_ms: How long to wait after submitting or loading.
    :param screenshot: Optional path to save a screenshot after completion.
    """
    if browser == "default":
        cfg_browser = _load_root_config().get("browser", {}).get("default_choice")
        if cfg_browser:
            browser = cfg_browser
            logger.info("Browser overridden by config.json: %s", browser)
    try:
        url, resolved_input_selector = resolve_config(website_name, input_selector)
        browser_name, launch_kwargs, browser_label, browser_key = resolve_browser_launch_options(browser, headed)
        direct_search_url = build_direct_search_url(website_name, query, input_selector, submit_selector)

        if headed and PROCESS_NAMES.for_browser(browser_key):
            target_url = direct_search_url or url
            if direct_search_url or not query:
                if open_url_in_existing_browser(browser_key, target_url):
                    logger.info("Opened a new tab in the existing %s window.", browser_label)
                    if direct_search_url:
                        logger.info("The query was sent through the URL directly.")
                    else:
                        logger.info("Opened the requested URL in a new tab without launching a new window.")
                    return

                logger.info(
                    "No reusable %s window was found, so a Playwright-managed window will be launched.",
                    browser_label,
                )
            else:
                logger.info(
                    "Existing-browser tab reuse is skipped because this scenario still needs page interaction."
                )

        async with async_playwright() as playwright:
            browser_type = getattr(playwright, browser_name)

            logger.info(
                "Launching browser via Playwright: %s (engine=%s)",
                browser_label,
                browser_name,
            )
            pw_browser = await browser_type.launch(**launch_kwargs)

            try:
                page = await pw_browser.new_page()
                page.set_default_timeout(timeout_ms)

                target_url = direct_search_url or url
                logger.info("Opening %s", target_url)
                await page.goto(target_url, wait_until="domcontentloaded")

                if query and not direct_search_url:
                    if resolved_input_selector:
                        logger.info("Waiting for input: %s", resolved_input_selector)
                        field = page.locator(resolved_input_selector).first
                        await field.wait_for(state="visible")
                        await field.click()
                        await field.fill(query)

                        if submit_selector:
                            logger.info("Submitting via button: %s", submit_selector)
                            submit_button = page.locator(submit_selector).first
                            await submit_button.wait_for(state="visible")
                            await submit_button.click()
                        else:
                            logger.info("Submitting via Enter")
                            await field.press("Enter")
                    else:
                        logger.warning("Query provided but no input selector resolved. Skipping query input.")

                if wait_after_ms > 0:
                    await page.wait_for_timeout(wait_after_ms)

                if screenshot:
                    screenshot_path = Path(screenshot)
                    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                    logger.info("Screenshot saved to %s", screenshot_path)
                    
            except PlaywrightTimeoutError as exc:
                raise RuntimeError(
                    "Timed out while interacting with the page. Check the selectors or increase timeout_ms."
                ) from exc
            finally:
                await pw_browser.close()
                
    except RuntimeError as exc:
        logger.error("%s", exc)
        raise
    except Exception as exc:
        logger.error("Browser automation failed: %s", exc)
        logger.info("If Playwright is not installed yet, run: pip install -r requirements.txt")
        logger.info("Then install a browser once: playwright install chromium")
        logger.info("If you use Firefox with browser='default', you may also need: playwright install firefox")
        raise
