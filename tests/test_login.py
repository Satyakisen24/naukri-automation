import unittest
from unittest.mock import patch

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from scripts import update_naukri


class FakeDriver:
    def __init__(self, current_url):
        self.current_url = current_url
        self.username_field = FakeElement()
        self.password_field = FakeElement()

    def find_element(self, by, selector):
        if by == "css selector" and "Email ID / Username" in selector:
            return self.username_field
        if by == "css selector" and "Enter Password" in selector:
            return self.password_field
        if by == "xpath" and "Login" in selector:
            return FakeElement(
                on_click=lambda: setattr(
                    self, "current_url",
                    "https://www.naukri.com/mnjuser/profile"
                )
            )
        raise AssertionError(f"Unexpected selector: {by} {selector}")


class FakeElement:
    def __init__(self, on_click=None):
        self.value = None
        self.on_click = on_click

    def send_keys(self, value):
        self.value = value

    def click(self):
        if self.on_click:
            self.on_click()


class FakeWait:
    def __init__(self, driver, _timeout):
        self.driver = driver

    def until(self, condition):
        result = condition(self.driver)
        if not result:
            raise TimeoutException()
        return result


class TestLogin(unittest.TestCase):

    def test_terminal_period_toggles_on_and_off(self):
        original = "A professional summary  "

        with_period, added = update_naukri.toggle_terminal_period(
            original
        )
        without_period, removed = update_naukri.toggle_terminal_period(
            with_period
        )

        self.assertEqual(with_period, "A professional summary.  ")
        self.assertTrue(added)
        self.assertEqual(without_period, original)
        self.assertFalse(removed)

    def test_terminal_period_removes_only_one_existing_period(self):
        result, added = update_naukri.toggle_terminal_period(
            "Already ends.."
        )

        self.assertEqual(result, "Already ends.")
        self.assertFalse(added)

    def test_profile_summary_toggle_saves_and_verifies_each_run(self):
        wait_patches = (
            patch.object(update_naukri, "WebDriverWait", FakeWait),
            patch.object(
                update_naukri.EC,
                "element_to_be_clickable",
                side_effect=lambda locator: (
                    lambda browser: browser.find_element(*locator)
                ),
            ),
            patch.object(
                update_naukri.EC,
                "visibility_of_element_located",
                side_effect=lambda locator: (
                    lambda browser: browser.find_element(*locator)
                ),
            ),
            patch.object(
                update_naukri.EC,
                "invisibility_of_element_located",
                side_effect=lambda locator: lambda browser: (
                    browser.wait_until_invisible(locator)
                ),
            ),
        )

        with wait_patches[0], wait_patches[1], wait_patches[2], wait_patches[3]:
            first_run = FakeSummaryDriver("Summary text")
            update_naukri.toggle_profile_summary(first_run)
            self.assertEqual(first_run.saved_summary, "Summary text.")

            next_run = FakeSummaryDriver(first_run.saved_summary)
            update_naukri.toggle_profile_summary(next_run)
            self.assertEqual(next_run.saved_summary, "Summary text")
            self.assertEqual(first_run.success_toast_waits, 2)
            self.assertEqual(next_run.success_toast_waits, 2)


class FakeSummaryField(FakeElement):
    def __init__(self, value):
        super().__init__()
        self.value = value
        self.max_length = "1000"

    def clear(self):
        self.value = ""

    def get_attribute(self, name):
        if name == "value":
            return self.value
        if name == "maxlength":
            return self.max_length
        return None

    def send_keys(self, value):
        self.value += value


class FakeSummaryDriver:
    def __init__(self, summary):
        self.saved_summary = summary
        self.summary_field = FakeSummaryField(summary)
        self.editor_open = False
        self.success_toast_visible = False
        self.success_toast_waits = 0

    def find_element(self, by, selector):
        if by == By.XPATH and "quickLink" in selector:
            return FakeElement()
        if by == By.CSS_SELECTOR and "Edit profile summary" in selector:
            return FakeElement(on_click=self.open_editor)
        if by == By.CSS_SELECTOR and ".success-message-container" in selector:
            return FakeElement() if self.success_toast_visible else None
        if by == By.ID and selector == "profileSummaryTxt":
            return self.summary_field if self.editor_open else None
        if by == By.XPATH and "Save" in selector:
            return FakeElement(on_click=self.save_summary)
        if by == By.XPATH and "CrossLayer" in selector:
            return FakeElement(on_click=self.close_editor)
        raise AssertionError(f"Unexpected selector: {by} {selector}")

    def open_editor(self):
        self.editor_open = True
        self.summary_field.value = self.saved_summary

    def save_summary(self):
        self.saved_summary = self.summary_field.value
        self.editor_open = False
        self.success_toast_visible = True

    def wait_until_invisible(self, locator):
        if locator == (By.CSS_SELECTOR, ".success-message-container"):
            self.success_toast_waits += 1
            self.success_toast_visible = False
            return True
        return self.find_element(*locator) is None

    def close_editor(self):
        self.editor_open = False


class TestLoginFlow(unittest.TestCase):

    def test_post_login_wait_is_ten_seconds(self):
        self.assertEqual(update_naukri.POST_LOGIN_SETTLE_SECONDS, 10)

    def test_skips_login_when_already_authenticated(self):
        driver = FakeDriver("https://www.naukri.com/mnjuser/profile")

        with patch.object(update_naukri, "WebDriverWait", FakeWait):
            update_naukri.complete_login(driver)

    def test_login_requires_both_credentials(self):
        driver = FakeDriver("https://www.naukri.com/nlogin/login")

        with patch.object(update_naukri, "NAUKRI_USERNAME", ""):
            with patch.object(update_naukri, "NAUKRI_PASSWORD", ""):
                with self.assertRaisesRegex(RuntimeError, "empty"):
                    update_naukri.complete_login(driver)

    def test_submits_configured_credentials(self):
        driver = FakeDriver("https://www.naukri.com/nlogin/login")

        with patch.object(
            update_naukri, "NAUKRI_USERNAME", "test@example.com"
        ):
            with patch.object(
                update_naukri, "NAUKRI_PASSWORD", "test-password"
            ):
                with patch.object(
                    update_naukri, "WebDriverWait", FakeWait
                ):
                    update_naukri.complete_login(driver)

        self.assertEqual(driver.username_field.value, "test@example.com")
        self.assertEqual(driver.password_field.value, "test-password")
        self.assertNotIn("login", driver.current_url)

    def test_reports_login_rejected_or_verification_required(self):
        driver = FakeDriver("https://www.naukri.com/nlogin/login")
        driver.find_element = lambda _by, _selector: FakeElement()

        with patch.object(
            update_naukri, "NAUKRI_USERNAME", "test@example.com"
        ):
            with patch.object(
                update_naukri, "NAUKRI_PASSWORD", "test-password"
            ):
                with patch.object(
                    update_naukri, "WebDriverWait", FakeWait
                ):
                    with self.assertRaisesRegex(
                        RuntimeError, "OTP or CAPTCHA"
                    ):
                        update_naukri.complete_login(driver)


if __name__ == "__main__":
    unittest.main()
