
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException


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
POST_LOGIN_SETTLE_SECONDS = 10

# Enter credentials locally here. Do not commit real credentials.
NAUKRI_USERNAME = os.getenv("NAUKRI_EMAIL", "").strip()
NAUKRI_PASSWORD = os.getenv("NAUKRI_PASSWORD", "")


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


# 5. Inspect profile
def inspect_profile(driver):
    logger.info("Current URL: %s", driver.current_url)
    logger.info("Page title: %s", driver.title)

    logger.info(
        "Profile summary toggle completed and verified. "
        "No resume upload or other profile fields were changed."
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

    logger.info("Profile inspection complete.")


def complete_login(driver):
    if "login" not in driver.current_url.lower():
        return

    username = NAUKRI_USERNAME
    password = NAUKRI_PASSWORD
    if not username or not password:
        raise RuntimeError(
            "Naukri login is required, but NAUKRI_USERNAME or "
            "NAUKRI_PASSWORD is empty in update_naukri.py."
        )

    wait = WebDriverWait(driver, 30)
    try:
        username_field = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'input[placeholder="Enter Email ID / Username"]')
            )
        )
        password_field = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'input[placeholder="Enter Password"]')
            )
        )
    except TimeoutException as exc:
        raise RuntimeError(
            "Could not locate Naukri's standard login fields; "
            "the login page may have changed."
        ) from exc

    username_field.send_keys(username)
    password_field.send_keys(password)
    driver.find_element(
        By.XPATH, "//button[normalize-space()='Login']"
    ).click()

    try:
        wait.until(
            lambda browser: "login" not in browser.current_url.lower()
        )
    except TimeoutException as exc:
        raise RuntimeError(
            "Naukri did not complete sign-in. Check the configured "
            "credentials; the account may require additional "
            "verification such as OTP or CAPTCHA."
        ) from exc

    logger.info("Naukri sign-in completed.")


def toggle_terminal_period(text):
    content = text.rstrip()
    trailing_whitespace = text[len(content):]

    if content.endswith("."):
        return content[:-1] + trailing_whitespace, False

    return content + "." + trailing_whitespace, True


def toggle_profile_summary(driver):
    wait = WebDriverWait(driver, 30)
    summary_link = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//div[contains(@class, 'quickLink')]"
                "//span[translate(normalize-space(.), "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
                "'abcdefghijklmnopqrstuvwxyz')='profile summary']"
            )
        )
    )
    summary_link.click()

    wait.until(
        EC.invisibility_of_element_located(
            (By.CSS_SELECTOR, ".success-message-container")
        )
    )
    edit_button = wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, '[aria-label="Edit profile summary"]')
        )
    )
    edit_button.click()

    summary_field = wait.until(
        EC.visibility_of_element_located(
            (By.ID, "profileSummaryTxt")
        )
    )
    current_summary = summary_field.get_attribute("value") or ""
    updated_summary, added_period = toggle_terminal_period(
        current_summary
    )

    max_length = summary_field.get_attribute("maxlength")
    if max_length and len(updated_summary) > int(max_length):
        raise RuntimeError(
            "Profile Summary is at its maximum length; "
            "cannot append a full stop."
        )

    summary_field.clear()
    summary_field.send_keys(updated_summary)
    if summary_field.get_attribute("value") != updated_summary:
        raise RuntimeError(
            "The Profile Summary field did not accept the requested "
            "text; nothing was saved."
        )

    save_button = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[normalize-space()='Save']")
        )
    )
    save_button.click()
    try:
        wait.until(
            EC.invisibility_of_element_located(
                (By.ID, "profileSummaryTxt")
            )
        )
    except TimeoutException as exc:
        raise RuntimeError(
            "Naukri did not close the Profile Summary editor after "
            "Save; the change may not have been saved."
        ) from exc

    wait.until(
        EC.invisibility_of_element_located(
            (By.CSS_SELECTOR, ".success-message-container")
        )
    )
    edit_button = wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, '[aria-label="Edit profile summary"]')
        )
    )
    edit_button.click()
    saved_field = wait.until(
        EC.visibility_of_element_located(
            (By.ID, "profileSummaryTxt")
        )
    )
    if (saved_field.get_attribute("value") or "") != updated_summary:
        raise RuntimeError(
            "The saved Profile Summary did not match the requested "
            "toggle; verify it in Naukri before the next run."
        )

    action = "added" if added_period else "removed"
    logger.info(
        "Profile Summary saved and verified; terminal full stop %s.",
        action
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
        complete_login(driver)
        if "/mnjuser/profile" not in driver.current_url.lower():
            driver.get(config["profile_url"])
            WebDriverWait(driver, 30).until(
                lambda browser:
                    "/mnjuser/profile" in browser.current_url.lower()
                    and browser.execute_script(
                        "return document.readyState"
                    ) in ("interactive", "complete")
            )
        logger.info(
            "Waiting %d seconds for Naukri page rendering.",
            POST_LOGIN_SETTLE_SECONDS
        )
        time.sleep(POST_LOGIN_SETTLE_SECONDS)

        #Automation: toggle the profile summary and verify it
        toggle_profile_summary(driver)

        # Inspect the profile and take a screenshot for manual review
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
