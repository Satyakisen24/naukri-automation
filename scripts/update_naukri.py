
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


# 1. Project directories
PROJECT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 2. Logging
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

IS_JENKINS = bool(os.getenv("JENKINS_HOME"))


# 3. Read configuration
def load_config():
    config_path = PROJECT_DIR / "config.json"

    with config_path.open("r", encoding="utf-8") as file:
        return json.load(file)


# 4. Launch Chrome
def open_profile(config):
    profile_path = Path(config["chrome_profile"])

    if not profile_path.is_absolute():
        profile_path = PROJECT_DIR / profile_path

    profile_path.mkdir(parents=True, exist_ok=True)

    options = Options()
    options.add_argument(
        f"--user-data-dir={profile_path.resolve()}"
    )
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)

    try:
        driver.get(config["profile_url"])

        WebDriverWait(driver, 30).until(
            lambda browser: browser.execute_script(
                "return document.readyState"
            ) in ("interactive", "complete")
        )

        return driver

    except Exception:
        driver.quit()
        raise


# 5. Inspect profile without modifying it
def inspect_profile(driver):
    logger.info("Current URL: %s", driver.current_url)
    logger.info("Page title: %s", driver.title)

    logger.info(
        "Profile page detected. Review and update it manually."
    )

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
        "Inspection complete. No profile changes or uploads "
        "were performed."
    )


def complete_manual_login(driver):
    if "login" not in driver.current_url.lower():
        return

    if IS_JENKINS:
        raise RuntimeError(
            "Naukri requires an interactive sign-in, which Jenkins "
            "cannot complete. Run this script from a desktop "
            "PowerShell session and sign in manually."
        )

    logger.warning(
        "Naukri login required. Sign in manually in Chrome."
    )
    input(
        "Complete the Naukri sign-in in Chrome, then press ENTER "
        "to continue..."
    )

    if "login" in driver.current_url.lower():
        raise RuntimeError(
            "Naukri is still showing its login page. Complete "
            "the sign-in in Chrome and run the script again."
        )


# 6. Main program
def main():
    driver = None

    try:
        config = load_config()

        resume_path = Path(config["resume_path"])
        if not resume_path.is_absolute():
            resume_path = PROJECT_DIR / resume_path

        if not resume_path.is_file():
            raise FileNotFoundError(
                f"Resume not found: {resume_path}"
            )

        logger.info("Starting Naukri inspection")
        logger.info(
            "Execution mode: %s",
            "Jenkins" if IS_JENKINS else "Manual desktop"
        )

        driver = open_profile(config)
        time.sleep(3)

        complete_manual_login(driver)
        inspect_profile(driver)

        if IS_JENKINS:
            logger.info(
                "Jenkins inspection finished. "
                "Closing browser without interactive input."
            )
        else:
            logger.info(
                "You can now review and update your profile "
                "manually in Chrome."
            )
            input(
                "Press ENTER in this PowerShell window "
                "when you have finished your manual updates..."
            )

    except EOFError:
        logger.warning(
            "No interactive terminal available. "
            "Continuing to browser cleanup."
        )

    except Exception:
        logger.exception("Automation failed")
        raise

    finally:
        if driver is not None:
            try:
                driver.quit()
                logger.info("Chrome has been closed.")
            except Exception:
                logger.exception("Could not close Chrome cleanly")


if __name__ == "__main__":
    main()
