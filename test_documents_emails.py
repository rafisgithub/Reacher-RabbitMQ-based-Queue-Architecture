import os
import csv
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor

# Configuration
DOCUMENTS_DIR = "documents"
API_URL = "http://localhost:8080/v1/check_email"
OUTPUT_EMAILS_FILE = "extracted_emails.txt"
OUTPUT_RESULTS_FILE = "documents_test_results.json"

def extract_emails_from_csvs(directory):
    emails = set()
    print(f"📂 Scanning directory '{directory}' for CSV files...")
    
    if not os.path.exists(directory):
        print(f"❌ Directory '{directory}' not found!")
        return list(emails)

    for filename in os.listdir(directory):
        if filename.endswith(".csv"):
            filepath = os.path.join(directory, filename)
            print(f"  Looking inside {filename}...")
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        email = row.get("email", "").strip()
                        if email:
                            emails.add(email)
            except Exception as e:
                print(f"  ⚠️ Could not read {filename}: {e}")

    return list(emails)

def save_extracted_emails(emails, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        for email in emails:
            f.write(email + "\n")
    print(f"✅ Saved {len(emails)} unique emails to {output_file}")


def check_email(email):
    """
    Sends a payload to the reacher service.
    """
    payload = {
        "to_email": email,
        "hello_name": "proxy4smtp.com",
        "from_email": "postmaster@proxy4smtp.com"
    }
    try:
        response = requests.post(API_URL, json=payload, timeout=20)
        if response.status_code == 200:
            data = response.json()
            
            # Check the debug section to see if a proxy was used
            proxy_used = None
            try:
                verif = data.get("debug", {}).get("smtp", {}).get("verif_method", {}).get("verif_method", {})
                proxy_used = verif.get("proxy")
            except Exception:
                pass

            return {
                "email": email,
                "status": "success",
                "is_reachable": data.get("is_reachable"),
                "is_deliverable": data.get("smtp", {}).get("is_deliverable"),
                "proxy_used": proxy_used,
                "duration_secs": data.get("debug", {}).get("duration", {}).get("secs")
            }
        else:
            return {
                "email": email,
                "status": f"failed_http_{response.status_code}",
                "error": response.text
            }
    except requests.exceptions.RequestException as e:
        return {
            "email": email,
            "status": "exception",
            "error": str(e)
        }

def run_load_test(emails_to_test):
    if not emails_to_test:
        print("No emails to test!")
        return

    print(f"\n🚀 Starting test for {len(emails_to_test)} extracted emails against Reacher API...")
    start_time = time.time()
    
    results = []
    # Using ThreadPoolExecutor to run requests concurrently (10 at a time).
    with ThreadPoolExecutor(max_workers=10) as executor:
        for i, result in enumerate(executor.map(check_email, emails_to_test)):
            results.append(result)
            if (i + 1) % 100 == 0 or (i + 1) == len(emails_to_test):
                print(f"🔄 Processed {i + 1}/{len(emails_to_test)} emails...")

    end_time = time.time()
    total_time = end_time - start_time
    print(f"🎉 Testing completed! Took {total_time:.2f} seconds.")

    # Save results
    with open(OUTPUT_RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
        
    print(f"📄 Detailed results saved to {OUTPUT_RESULTS_FILE}")

    # Print summary
    success_count = sum(1 for r in results if r["status"] == "success")
    deliverable_count = sum(1 for r in results if r.get("is_deliverable"))
    print(f"\n📊 Summary:")
    print(f"   - Successful API Calls: {success_count}/{len(results)}")
    print(f"   - Deliverable Emails Found: {deliverable_count}")


if __name__ == "__main__":
    # 1. Extract emails from all CSVs
    unique_emails = extract_emails_from_csvs(DOCUMENTS_DIR)
    
    # 2. Save them to a text file
    save_extracted_emails(unique_emails, OUTPUT_EMAILS_FILE)
    
    # 3. Test them in the Reacher API
    run_load_test(unique_emails)
