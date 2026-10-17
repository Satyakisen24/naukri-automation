
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


# 1. Locate the project directory.
PROJECT_DIR = Path(__file__).resolve().parent.parent

# 2. Create the logs folder.
LOG_DIR = PROJECT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 3. Configure logging.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_DIR / "naukri.log",
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# 4. Read the configuration file.
def load_config():
    config_path = PROJECT_DIR / "config.json"

    with config_path.open("r", encoding="utf-8") as file:
        return json.load(file)


# 5. Open the Naukri profile.
def open_profile(config):
    chrome_profile = Path(config["chrome_profile"])
    chrome_profile.mkdir(parents=True, exist_ok=True)

    options = Options()
    options.add_argument(
        f"--user-data-dir={chrome_profile}"
    )
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)

    driver.get(config["profile_url"])

    # Wait until the browser reports that the page has loaded.
    WebDriverWait(driver, 30).until(
        lambda browser: browser.execute_script(
            "return document.readyState"
        ) in ("interactive", "complete")
    )

    return driver


# 6. Inspect the profile page.
def inspect_profile(driver):
    logger.info("Current URL: %s", driver.current_url)
    logger.info("Page title: %s", driver.title)

    body_text = driver.find_element(
        By.TAG_NAME, "body"
    ).text.lower()

    if "login" in driver.current_url.lower():
        logger.warning(
            "Login required. Sign in manually."
        )

    # Report upload controls without clicking them.
    file_inputs = driver.find_elements(
        By.CSS_SELECTOR, 'input[type="file"]'
    )

    logger.info(
        "File upload inputs found: %d",
        len(file_inputs)
    )

    screenshot_path = LOG_DIR / (
        f"profile-{datetime.now():%Y%m%d-%H%M%S}.png"
    )

    driver.save_screenshot(str(screenshot_path))
    logger.info("Screenshot saved: %s", screenshot_path)

    logger.info(
        "Inspection complete. Confirm the page and "
        "login status before enabling any updates."
    )


# 7. Main program.
def main():
    driver = None

    try:
        config = load_config()

        resume_path = Path(config["resume_path"])
        if not resume_path.is_file():
            raise FileNotFoundError(
                f"Resume not found: {resume_path}"
            )

        logger.info("Starting Naukri automation")

        driver = open_profile(config)
        time.sleep(3)

        inspect_profile(driver)

        logger.info(
            "Profile inspection completed; "
            "resume upload is not yet implemented."
        )

    except Exception:
        logger.exception("Automation failed")
        raise

    finally:
        # Keep the browser open for manual verification
        # unless you explicitly set NAUKRI_CLOSE_BROWSER=1.
        if driver and os.getenv(
            "NAUKRI_CLOSE_BROWSER", "0"
        ) == "1":
            driver.quit()
        elif driver:
            logger.info(
                "Browser left open for manual verification."
            )


if __name__ == "__main__":
    main()
