import unittest
from unittest.mock import patch

from scripts import update_naukri


class FakeDriver:
    def __init__(self, current_url):
        self.current_url = current_url


class TestManualLogin(unittest.TestCase):

    def test_skips_prompt_when_not_on_login_page(self):
        driver = FakeDriver("https://www.naukri.com/mnjuser/profile")

        with patch.object(update_naukri, "IS_JENKINS", False):
            with patch("builtins.input") as prompt:
                update_naukri.complete_manual_login(driver)

        prompt.assert_not_called()

    def test_jenkins_reports_interactive_login_requirement(self):
        driver = FakeDriver("https://www.naukri.com/nlogin/login")

        with patch.object(update_naukri, "IS_JENKINS", True):
            with self.assertRaisesRegex(RuntimeError, "Jenkins"):
                update_naukri.complete_manual_login(driver)

    def test_desktop_waits_for_login_and_continues(self):
        driver = FakeDriver("https://www.naukri.com/nlogin/login")

        def finish_login(_prompt):
            driver.current_url = (
                "https://www.naukri.com/mnjuser/profile"
            )

        with patch.object(update_naukri, "IS_JENKINS", False):
            with patch("builtins.input", side_effect=finish_login):
                update_naukri.complete_manual_login(driver)

    def test_desktop_reports_login_not_completed(self):
        driver = FakeDriver("https://www.naukri.com/nlogin/login")

        with patch.object(update_naukri, "IS_JENKINS", False):
            with patch("builtins.input"):
                with self.assertRaisesRegex(RuntimeError, "still"):
                    update_naukri.complete_manual_login(driver)


if __name__ == "__main__":
    unittest.main()
