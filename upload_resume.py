
import json
import logging
from pathlib import Path
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_DIR / "naukri-upload.log",
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_config():
    with (ROOT / "config.json").open(
        encoding="utf-8"
    ) as file:
        return json.load(file)


def upload_resume():
    config = load_config()
    resume = Path(config["resume_path"])

    if not resume.is_file():
        raise FileNotFoundError(
            f"Resume not found: {resume}"
        )

    options = Options()
    options.add_argument(
        f"--user-data-dir={config['chrome_profile']}"
    )
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(config["profile_url"])

        wait = WebDriverWait(driver, 30)
        wait.until(
            lambda d: d.execute_script(
                "return document.readyState"
            ) in ("interactive", "complete")
        )

        # If login is required, stop rather than trying to
        # bypass Naukri's security checks.
        if "login" in driver.current_url.lower():
            raise RuntimeError(
                "Login required. Sign in manually and retry."
            )

        upload_input = wait.until(
            lambda d: d.find_element(
                By.ID, "attachCV"
            )
        )

        upload_input.send_keys(str(resume.resolve()))
        logger.info(
            "Selected resume file: %s",
            resume.name
        )

        # Allow the page to process the file selection.
        # File selection alone does not prove it was saved.
        driver.implicitly_wait(0)

        screenshot = LOG_DIR / (
            f"upload-{datetime.now():%Y%m%d-%H%M%S}.png"
        )
        driver.save_screenshot(str(screenshot))
        logger.info("Screenshot saved: %s", screenshot)

        logger.warning(
            "VERIFY REQUIRED: check Naukri's displayed "
            "resume filename and upload/save confirmation."
        )
        logger.info(
            "Current page: %s",
            driver.current_url
        )

        # Keep the browser open during the first test.
        input(
            "Verify the upload in Chrome. "
            "Press ENTER in this terminal to close Chrome..."
        )

    finally:
        driver.quit()


if __name__ == "__main__":
    upload_resume()
