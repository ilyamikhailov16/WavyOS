import argparse
import asyncio
import logging
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright


logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


PRESETS = {
    "google": {
        "url": "https://www.google.com/",
        "input_selector": 'textarea[name="q"]',
    },
    "bing": {
        "url": "https://www.bing.com/",
        "input_selector": 'textarea[name="q"], input[name="q"]',
    },
    "duckduckgo": {
        "url": "https://duckduckgo.com/",
        "input_selector": 'textarea[name="q"], input[name="q"]',
    },
    "yandex": {
        "url": "https://ya.ru/",
        "input_selector": 'input[name="text"]',
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Open a website in a browser and perform a query with Playwright.",
    )
    parser.add_argument(
        "--engine",
        choices=sorted(PRESETS),
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
        choices=("chromium", "firefox", "webkit"),
        default="chromium",
        help="Browser engine to launch.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the browser window instead of running headless.",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=15000,
        help="Timeout for page actions in milliseconds.",
    )
    parser.add_argument(
        "--wait-after-ms",
        type=int,
        default=3000,
        help="How long to wait after submitting the query.",
    )
    parser.add_argument(
        "--screenshot",
        help="Optional path to save a screenshot after submission.",
    )
    return parser


def resolve_config(args: argparse.Namespace) -> tuple[str, str]:
    preset = PRESETS.get(args.engine, {})
    url = args.url or preset.get("url")
    input_selector = args.input_selector or preset.get("input_selector")

    if not url:
        raise ValueError("Specify --url or use --engine with a built-in URL preset.")
    if not input_selector:
        raise ValueError(
            "Specify --input-selector or use --engine with a built-in selector preset."
        )

    return url, input_selector


async def run_browser_task(args: argparse.Namespace) -> None:
    url, input_selector = resolve_config(args)

    async with async_playwright() as playwright:
        browser_type = getattr(playwright, args.browser)
        browser = await browser_type.launch(headless=not args.headed)

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
        return 1

    logger.info("Browser automation finished successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
