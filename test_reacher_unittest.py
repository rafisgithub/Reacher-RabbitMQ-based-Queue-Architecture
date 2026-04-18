import unittest
import requests
import os
import csv

class TestReacherAPIIntegration(unittest.TestCase):
    API_URL = "http://localhost:8080/v1/check_email"
    DOCUMENTS_DIR = "documents"

    def test_01_api_health(self):
        """Test if the Reacher API is up and responding to basic requests."""
        payload = {"to_email": "test@google.com"}
        try:
            response = requests.post(self.API_URL, json=payload, timeout=10)
            self.assertEqual(response.status_code, 200, "API is not returning a 200 status code.")
        except requests.exceptions.ConnectionError:
            self.fail("Could not connect to the Reacher API. Is the Docker container running?")

    def test_02_proxy_is_used(self):
        """Verify that the proxy settings from the .env file are actually being applied."""
        payload = {"to_email": "support@google.com"}
        response = requests.post(self.API_URL, json=payload, timeout=15)
        data = response.json()
        
        # safely extract proxy data
        verif = data.get("debug", {}).get("smtp", {}).get("verif_method", {}).get("verif_method", {})
        proxy_used = verif.get("proxy")

        self.assertIsNotNone(proxy_used, "Proxy is null! The Reacher API is not using the proxy.")
        self.assertIn("1081", proxy_used, "Proxy does not match the expected port 1081.")

    def test_03_extracted_emails_structure(self):
        """Test a small sample of emails from the documents folder to ensure proper validation response."""
        if not os.path.exists(self.DOCUMENTS_DIR):
            self.skipTest(f"Directory {self.DOCUMENTS_DIR} not found.")

        # Grab up to 3 emails from the first CSV found
        sample_emails = []
        for filename in os.listdir(self.DOCUMENTS_DIR):
            if filename.endswith(".csv"):
                filepath = os.path.join(self.DOCUMENTS_DIR, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        email = row.get("email", "").strip()
                        if email and email not in sample_emails:
                            sample_emails.append(email)
                        if len(sample_emails) >= 3:
                            break
            if sample_emails:
                break
                
        if not sample_emails:
            self.skipTest("No emails found in the documents CSVs.")

        # Test the extracted emails
        for email in sample_emails:
            with self.subTest(email=email):
                response = requests.post(self.API_URL, json={"to_email": email}, timeout=15)
                self.assertEqual(response.status_code, 200)
                
                data = response.json()
                self.assertIn("is_reachable", data, "Response missing 'is_reachable' key")
                self.assertIn("smtp", data, "Response missing 'smtp' block")

if __name__ == "__main__":
    unittest.main(verbosity=2)
