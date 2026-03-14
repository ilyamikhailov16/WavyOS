import argparse
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

from bootstrap import settings
from app_logging import get_logger

BROWSER_SETTINGS = settings.browser
PRESETS = BROWSER_SETTINGS.presets
PROCESS_NAMES = BROWSER_SETTINGS.process_names
DEFAULT_TIMEOUT_MS = BROWSER_SETTINGS.timeouts.default_timeout_ms
DEFAULT_WAIT_AFTER_MS = BROWSER_SETTINGS.timeouts.default_wait_after_ms
logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Open a website in a browser and perform a query with Playwright.",
    )
    parser.add_argument(
        "--engine",
        choices=PRESETS.names(),
        help="Use a built-in preset for a known search engine.",
    )
    parser.add_argument(
        "--url",
        help="Target URL. If omitted, the URL from --engine is used.",
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Text to enter into the target field.",
    )
    parser.add_argument(
        "--input-selector",
        help="CSS selector for the input field. Overrides preset selector.",
    )
    parser.add_argument(
        "--submit-selector",
        help="Optional CSS selector for a submit button. If omitted, Enter is pressed.",
    )
    parser.add_argument(
        "--browser",
        choices=BROWSER_SETTINGS.runtime.browser_choices,
        default="default",
        help="Browser to launch. 'default' resolves the Windows default browser.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the browser window instead of running headless.",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=DEFAULT_TIMEOUT_MS,
        help="Timeout for page actions in milliseconds.",
    )
    parser.add_argument(
        "--wait-after-ms",
        type=int,
        default=DEFAULT_WAIT_AFTER_MS,
        help="How long to wait after submitting the query.",
    )
    parser.add_argument(
        "--screenshot",
        help="Optional path to save a screenshot after submission.",
    )
    return parser


def resolve_config(args: argparse.Namespace) -> tuple[str, str]:
    preset = PRESETS.get(args.engine)
    url = args.url or (preset.url if preset else None)
    input_selector = args.input_selector or (preset.input_selector if preset else None)

    if not url:
        raise ValueError("Specify --url or use --engine with a built-in URL preset.")
    if not input_selector:
        raise ValueError(
            "Specify --input-selector or use --engine with a built-in selector preset."
        )

    return url, input_selector


def build_direct_search_url(args: argparse.Namespace) -> str | None:
    if not args.engine:
        return None
    if args.input_selector or args.submit_selector:
        return None

    preset = PRESETS.get(args.engine)
    search_url = preset.search_url if preset else None
    if not search_url:
        return None
    return search_url.format(query=quote_plus(args.query))


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
    args: argparse.Namespace,
) -> tuple[str, dict[str, str | bool], str, str]:
    if args.browser == "chromium":
        logger.info("Browser selection: explicit Playwright Chromium.")
        return (
            "chromium",
            {"headless": not args.headed},
            BROWSER_SETTINGS.runtime.display_name_for("chromium"),
            "chromium",
        )
    if args.browser == "firefox":
        logger.info("Browser selection: explicit Playwright Firefox.")
        return (
            "firefox",
            {"headless": not args.headed},
            BROWSER_SETTINGS.runtime.display_name_for("firefox"),
            "firefox",
        )
    if args.browser == "webkit":
        logger.info("Browser selection: explicit Playwright WebKit.")
        return (
            "webkit",
            {"headless": not args.headed},
            BROWSER_SETTINGS.runtime.display_name_for("webkit"),
            "webkit",
        )
    if args.browser == "chrome":
        logger.info("Browser selection: explicit Google Chrome channel.")
        return (
            "chromium",
            {
                "headless": not args.headed,
                "channel": BROWSER_SETTINGS.runtime.playwright_channel_for("chrome"),
            },
            BROWSER_SETTINGS.runtime.display_name_for("chrome"),
            "chrome",
        )
    if args.browser == "edge":
        logger.info("Browser selection: explicit Microsoft Edge channel.")
        return (
            "chromium",
            {
                "headless": not args.headed,
                "channel": BROWSER_SETTINGS.runtime.playwright_channel_for("edge"),
            },
            BROWSER_SETTINGS.runtime.display_name_for("edge"),
            "edge",
        )
    if args.browser in {"opera", "yandex"}:
        executable_path = find_custom_browser_executable(args.browser)
        readable_name = BROWSER_SETTINGS.runtime.display_name_for(args.browser)
        if executable_path:
            logger.info("Browser selection: explicit %s executable.", readable_name)
            logger.info("Playwright will launch via executable: %s", executable_path)
            return (
                "chromium",
                {"headless": not args.headed, "executable_path": str(executable_path)},
                readable_name,
                args.browser,
            )
        logger.warning("%s executable was not found in the standard Windows paths.", readable_name)
        logger.warning("Fallback selected: Playwright Chromium will be used.")
        return "chromium", {"headless": not args.headed}, "Playwright Chromium", "chromium"

    progid = get_windows_default_browser_progid()
    if progid:
        browser_key = map_progid_to_browser(progid)
        if browser_key:
            readable_name = BROWSER_SETTINGS.runtime.display_name_for(browser_key)
            logger.info("Windows default browser detected: %s (%s)", readable_name, progid)

            if browser_key in {"edge", "chrome", "firefox"}:
                mapped_args = argparse.Namespace(browser=browser_key, headed=args.headed)
                return resolve_browser_launch_options(mapped_args)

            executable_path = find_custom_browser_executable(browser_key)
            if executable_path:
                logger.info(
                    "Playwright will launch the installed %s browser via executable path.",
                    readable_name,
                )
                logger.info("Executable path: %s", executable_path)
                return (
                    "chromium",
                    {"headless": not args.headed, "executable_path": str(executable_path)},
                    readable_name,
                    browser_key,
                )

            logger.warning("%s is the Windows default browser, but its executable was not found.", readable_name)
            logger.warning(
                "Fallback selected: Playwright Chromium will be used instead of the system default browser."
            )
            return "chromium", {"headless": not args.headed}, "Playwright Chromium", "chromium"

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

    return "chromium", {"headless": not args.headed}, "Playwright Chromium", "chromium"


async def run_browser_task(args: argparse.Namespace) -> None:
    url, input_selector = resolve_config(args)
    browser_name, launch_kwargs, browser_label, browser_key = resolve_browser_launch_options(args)
    direct_search_url = build_direct_search_url(args)

    if args.headed and PROCESS_NAMES.for_browser(browser_key):
        existing_tab_url = direct_search_url or url
        if direct_search_url or (args.url and not args.input_selector and not args.submit_selector):
            if open_url_in_existing_browser(browser_key, existing_tab_url):
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
        browser = await browser_type.launch(**launch_kwargs)

        try:
            page = await browser.new_page()
            page.set_default_timeout(args.timeout_ms)

            logger.info("Opening %s", url)
            await page.goto(url, wait_until="domcontentloaded")

            logger.info("Waiting for input: %s", input_selector)
            field = page.locator(input_selector).first
            await field.wait_for(state="visible")
            await field.click()
            await field.fill(args.query)

            if args.submit_selector:
                logger.info("Submitting via button: %s", args.submit_selector)
                submit_button = page.locator(args.submit_selector).first
                await submit_button.wait_for(state="visible")
                await submit_button.click()
            else:
                logger.info("Submitting via Enter")
                await field.press("Enter")

            if args.wait_after_ms > 0:
                await page.wait_for_timeout(args.wait_after_ms)

            if args.screenshot:
                screenshot_path = Path(args.screenshot)
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=str(screenshot_path), full_page=True)
                logger.info("Screenshot saved to %s", screenshot_path)
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "Timed out while interacting with the page. Check the selectors or increase --timeout-ms."
            ) from exc
        finally:
            await browser.close()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        asyncio.run(run_browser_task(args))
    except ValueError as exc:
        parser.error(str(exc))
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1
    except Exception as exc:
        logger.error("Browser automation failed: %s", exc)
        logger.info("If Playwright is not installed yet, run: pip install -r requirements.txt")
        logger.info("Then install a browser once: playwright install chromium")
        logger.info("If you use Firefox with --browser default, you may also need: playwright install firefox")
        return 1

    logger.info("Browser automation finished successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
