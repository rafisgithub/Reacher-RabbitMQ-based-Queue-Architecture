import requests
import json
import time
import os

API_URL = "http://localhost:8080/v1/check_email"
EMAILS_FILE = "extracted_emails.txt"
OUTPUT_FILE = "single_email_results.json"

PAYLOAD_DEFAULTS = {
    "hello_name": "proxy4smtp.com",
    "from_email": "postmaster@proxy4smtp.com",
}

COLORS = {
    "safe":    "\033[92m",
    "risky":   "\033[93m",
    "invalid": "\033[91m",
    "unknown": "\033[90m",
    "reset":   "\033[0m",
}

def color(text, status):
    return f"{COLORS.get(status, COLORS['reset'])}{text}{COLORS['reset']}"

def check_email(session, email):
    payload = {**PAYLOAD_DEFAULTS, "to_email": email}
    start = time.time()
    response = session.post(API_URL, json=payload, timeout=60)
    response.raise_for_status()
    elapsed = time.time() - start
    data = response.json()

    # Extract proxy used
    proxy_used = None
    try:
        verif = data.get("debug", {}).get("smtp", {}).get("verif_method", {}).get("verif_method", {})
        proxy_used = verif.get("proxy")
    except Exception:
        pass

    return {
        "email": email,
        "is_reachable": data.get("is_reachable"),
        "is_deliverable": data.get("smtp", {}).get("is_deliverable"),
        "smtp_error": data.get("smtp", {}).get("error"),
        "mx_records": data.get("mx", {}).get("records", []),
        "is_catch_all": data.get("smtp", {}).get("is_catch_all"),
        "is_disposable": data.get("misc", {}).get("is_disposable"),
        "proxy_used": proxy_used,
        "duration_secs": round(elapsed, 2),
        "backend": data.get("debug", {}).get("backend_name"),
    }

def main():
    if not os.path.exists(EMAILS_FILE):
        print(f"ERROR: {EMAILS_FILE} not found.")
        return

    with open(EMAILS_FILE, "r", encoding="utf-8") as f:
        emails = [line.strip() for line in f if line.strip()]

    total = len(emails)
    results = []
    summary = {"safe": 0, "risky": 0, "invalid": 0, "unknown": 0, "error": 0}
    total_duration = 0.0

    print(f"Verifying {total} emails one by one via {API_URL}\n")
    print(f"{'#':<5} {'Email':<45} {'Result':<10} {'Dur(s)':<8} {'Deliverable'}")
    print("-" * 85)

    with requests.Session() as session:
        for i, email in enumerate(emails, start=1):
            try:
                result = check_email(session, email)
                status = result["is_reachable"]
                summary[status] = summary.get(status, 0) + 1
                total_duration += result["duration_secs"]
                results.append(result)

                deliverable = "yes" if result["is_deliverable"] else ("no" if result["is_deliverable"] is False else "-")
                print(
                    f"[{i:>3}/{total}] "
                    f"{email:<45} "
                    f"{color(f'{status:<10}', status)} "
                    f"{result['duration_secs']:<8} "
                    f"{deliverable}"
                )
            except Exception as e:
                summary["error"] += 1
                results.append({"email": email, "is_reachable": "error", "error": str(e)})
                print(f"[{i:>3}/{total}] {email:<45} {color('ERROR', 'unknown')} {e}")

    print("\n" + "=" * 50)
    print(f"  Total emails  : {total}")
    print(f"  Total time    : {total_duration:.1f}s")
    print(f"  Avg per email : {total_duration / total:.2f}s")
    print(f"  safe={summary['safe']}  risky={summary['risky']}  "
          f"invalid={summary['invalid']}  unknown={summary['unknown']}  error={summary['error']}")
    print("=" * 50)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
