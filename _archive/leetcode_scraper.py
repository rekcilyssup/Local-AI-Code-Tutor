import requests
import browser_cookie3
import json
import time


def _load_leetcode_cookies_from_supported_browsers():
    """Try browsers in a practical order and skip Safari's protected store by default."""
    browser_loaders = [
        ("Chrome", browser_cookie3.chrome),
        ("Brave", browser_cookie3.brave),
        ("Chromium", browser_cookie3.chromium),
        ("Firefox", browser_cookie3.firefox),
        ("Edge", browser_cookie3.edge),
        ("Opera", browser_cookie3.opera),
    ]

    errors = []
    for browser_name, loader in browser_loaders:
        try:
            cookie_jar = loader(domain_name="leetcode.com")
            if any(True for _ in cookie_jar):
                return cookie_jar, browser_name
            errors.append(f"{browser_name}: no leetcode.com cookies found")
        except Exception as exc:
            errors.append(f"{browser_name}: {exc}")

    # Safari cookies are often blocked by macOS privacy unless full disk access is granted.
    errors.append("Safari: skipped by default (macOS privacy-protected cookie store)")
    raise RuntimeError("; ".join(errors))

def fetch_real_leetcode_data():
    print("🕵️  Extracting cookies from local browsers...")
    
    try:
        cj, browser_used = _load_leetcode_cookies_from_supported_browsers()
        print(f"✅ Using cookies from {browser_used}.")
    except Exception as e:
        print("❌ Failed to load cookies from supported browsers.")
        print("   Make sure you are logged into LeetCode in Chrome/Brave/Firefox and close the browser before retrying.")
        print("   If you need Safari, grant Full Disk Access to Terminal/VS Code and Python, then try again.")
        print(f"   Error details: {e}")
        return
    
    csrf_token = None
    for cookie in cj:
        if cookie.name == 'csrftoken':
            csrf_token = cookie.value
            
    if not csrf_token:
        print("❌ Error: Could not find LeetCode CSRF token. Log into LeetCode on your browser first.")
        return

    # The master key to bypass the 403 Forbidden error
    headers = {
        "Content-Type": "application/json",
        "x-csrftoken": csrf_token,
        "Referer": "https://leetcode.com/"
    }
    
    print("📡 Fetching your recent submission history...")
    list_query = """
    query submissionList($offset: Int!, $limit: Int!) {
      submissionList(offset: $offset, limit: $limit) {
        submissions { id title lang statusDisplay timestamp }
      }
    }
    """
    # Grabbing your last 15 submissions
    list_payload = {"query": list_query, "variables": {"offset": 0, "limit": 15}}
    
    res = requests.post("https://leetcode.com/graphql", json=list_payload, headers=headers, cookies=cj)
    res.raise_for_status()
    
    submissions = res.json().get("data", {}).get("submissionList", {}).get("submissions", [])
    
    if not submissions:
        print("⚠️ No submissions found or auth failed.")
        return

    print(f"📥 Found {len(submissions)} submissions. Downloading the actual code...")
    details_query = """
    query submissionDetails($submissionId: Int!) {
      submissionDetails(submissionId: $submissionId) { code }
    }
    """
    
    final_data = []
    for sub in submissions:
        sub_id = int(sub['id'])
        details_payload = {"query": details_query, "variables": {"submissionId": sub_id}}
        
        # A tiny delay so LeetCode's servers don't rate-limit your IP
        time.sleep(0.5) 
        
        detail_res = requests.post("https://leetcode.com/graphql", json=details_payload, headers=headers, cookies=cj)
        code_data = detail_res.json().get("data", {}).get("submissionDetails", {})
        
        if code_data and code_data.get("code"):
            sub["code"] = code_data["code"]
            final_data.append(sub)
            print(f"   ✅ Downloaded: {sub['title']} ({sub['statusDisplay']})")

    # Overwrite your dummy data with the real stuff
    with open("submissions.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2)
        
    print(f"🎉 Successfully saved {len(final_data)} real submissions to submissions.json!")

if __name__ == "__main__":
    fetch_real_leetcode_data()