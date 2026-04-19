import json
import time
import requests

API_URL = "http://localhost:8080/v1/check_email"
EMAILS_FILE = "extracted_emails.txt"
OUTPUT_FILE = "verification_results.json"

PAYLOAD_DEFAULTS = {
    "hello_name": "proxy4smtp.com",
    "from_email": "postmaster@proxy4smtp.com",
}

COLORS = {
    "safe": "\033[92m",
    "risky": "\033[93m",
    "invalid": "\033[91m",
    "unknown": "\033[90m",
    "error": "\033[95m",
    "reset": "\033[0m",
}


def color(text, status):
    c = COLORS.get(status, COLORS["reset"])
    return f"{c}{text}{COLORS['reset']}"


def check_email(session, email):
    payload = {**PAYLOAD_DEFAULTS, "to_email": email}
    response = session.post(API_URL, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def main():
    with open(EMAILS_FILE, "r") as f:
        emails = [line.strip() for line in f if line.strip()]

    total = len(emails)
    results = []
    summary = {"safe": 0, "risky": 0, "invalid": 0, "unknown": 0, "error": 0}

    print(f"Verifying {total} emails via {API_URL}\n")

    with requests.Session() as session:
        for i, email in enumerate(emails, start=1):
            print(f"[{i}/{total}] {email} ... ", end="", flush=True)
            try:
                data = check_email(session, email)
                status = data.get("is_reachable", "unknown")
                summary[status] = summary.get(status, 0) + 1
                results.append(data)
                print(color(status, status))
            except Exception as e:
                summary["error"] += 1
                results.append({"input": email, "is_reachable": "error", "error": str(e)})
                print(color(f"ERROR: {e}", "error"))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*40}")
    print(f"Done. {total} emails checked.")
    print(f"Results saved to: {OUTPUT_FILE}")
    print(f"\n=== Summary ===")
    for status, count in summary.items():
        if count:
            print(f"  {color(f'{status:<10} {count}', status)}")


if __name__ == "__main__":
    main()
