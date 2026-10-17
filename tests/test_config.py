
import json
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent


class TestNaukriConfig(unittest.TestCase):

    def test_config_file_exists(self):
        config_path = PROJECT_DIR / "config.json"
        self.assertTrue(config_path.is_file())

    def test_required_config_fields(self):
        config_path = PROJECT_DIR / "config.json"

        with config_path.open(encoding="utf-8") as file:
            config = json.load(file)

        self.assertIn("profile_url", config)
        self.assertIn("resume_path", config)
        self.assertIn("chrome_profile", config)

    def test_resume_exists(self):
        config_path = PROJECT_DIR / "config.json"

        with config_path.open(encoding="utf-8") as file:
            config = json.load(file)

        resume = Path(config["resume_path"])
        self.assertTrue(
            resume.is_file(),
            f"Resume not found: {resume}"
        )


if __name__ == "__main__":
    unittest.main()
