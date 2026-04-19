import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor

# API Endpoint
API_URL = "http://localhost:8080/v1/check_email"

import os

# Load emails directly from the extracted_emails.txt file
emails_to_test = []
extracted_file_path = "extracted_emails.txt"

if os.path.exists(extracted_file_path):
    with open(extracted_file_path, "r", encoding="utf-8") as f:
        emails_to_test = [line.strip() for line in f if line.strip()]
    print(f"Loaded {len(emails_to_test)} emails from {extracted_file_path}.")
else:
    print(f"File {extracted_file_path} not found.")

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
        # Reacher can take a few seconds per email, adding a timeout
        response = requests.post(API_URL, json=payload, timeout=60)
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
                "smtp_error": data.get("smtp", {}).get("error"),
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

def run_concurrent_batch(emails, concurrency):
    """Run a batch of email verifications with the given concurrency level."""
    print(f"\n{'='*55}")
    print(f"  Concurrency: {concurrency} | Emails: {len(emails)}")
    print(f"{'='*55}")

    completed = 0
    results = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(check_email, email): email for email in emails}
        for future in futures:
            result = future.result()
            results.append(result)
            completed += 1
            status = result.get("is_reachable", result.get("status", "?"))
            color = (
                "\033[92m" if status == "safe" else
                "\033[93m" if status == "risky" else
                "\033[91m" if status in ("invalid", "exception") else
                "\033[90m"
            )
            print(f"  [{completed:>3}/{len(emails)}] {result['email']:<45} {color}{status}\033[0m")

    elapsed = time.time() - start_time

    success   = sum(1 for r in results if r.get("status") == "success")
    errors    = sum(1 for r in results if r.get("status") != "success")
    reachable = {k: sum(1 for r in results if r.get("is_reachable") == k)
                 for k in ("safe", "risky", "invalid", "unknown")}
    durations = [r["duration_secs"] for r in results if r.get("duration_secs") is not None]
    avg_dur   = sum(durations) / len(durations) if durations else 0

    print(f"\n  --- Results (concurrency={concurrency}) ---")
    print(f"  Total time  : {elapsed:.2f}s")
    print(f"  Throughput  : {len(emails)/elapsed:.2f} req/s")
    print(f"  Avg duration: {avg_dur:.2f}s per email")
    print(f"  Success     : {success}  |  Errors: {errors}")
    print(f"  safe={reachable['safe']}  risky={reachable['risky']}  "
          f"invalid={reachable['invalid']}  unknown={reachable['unknown']}")

    return {
        "concurrency": concurrency,
        "total_emails": len(emails),
        "total_time_secs": round(elapsed, 3),
        "throughput_req_per_sec": round(len(emails) / elapsed, 3),
        "avg_duration_secs": round(avg_dur, 3),
        "success": success,
        "errors": errors,
        "reachability": reachable,
        "results": results,
    }


def run_load_test():
    if not emails_to_test:
        print("No emails to test.")
        return

    all_output = {}

    # --- 50 concurrent ---
    batch_50 = (emails_to_test * ((50 // len(emails_to_test)) + 1))[:50]
    all_output["concurrency_50"] = run_concurrent_batch(batch_50, concurrency=50)

    print("\n⏳ Cooling down 5 seconds before next batch...\n")
    time.sleep(5)

    # --- 100 concurrent ---
    batch_100 = (emails_to_test * ((100 // len(emails_to_test)) + 1))[:100]
    all_output["concurrency_100"] = run_concurrent_batch(batch_100, concurrency=100)

    # Save full output
    output_file = "reacher_load_test_results_test.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_output, f, indent=2, ensure_ascii=False)

    print(f"\n✅ All results saved to {output_file}")

    # Comparison table
    print(f"\n{'='*55}")
    print(f"  {'Metric':<30} {'50 conc':>10} {'100 conc':>10}")
    print(f"{'='*55}")
    for key, label in [
        ("total_time_secs",        "Total time (s)"),
        ("throughput_req_per_sec", "Throughput (req/s)"),
        ("avg_duration_secs",      "Avg duration (s)"),
        ("errors",                 "Errors"),
    ]:
        v50  = all_output["concurrency_50"][key]
        v100 = all_output["concurrency_100"][key]
        print(f"  {label:<30} {str(v50):>10} {str(v100):>10}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    run_load_test()
