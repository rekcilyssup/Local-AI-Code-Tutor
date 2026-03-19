import argparse
import json
import time

import browser_cookie3
import requests


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

	errors.append("Safari: skipped by default (macOS privacy-protected cookie store)")
	raise RuntimeError("; ".join(errors))


def fetch_real_leetcode_data(output_file: str = "submissions.json", limit: int = 100):
	print("Extracting cookies from local browsers...")

	try:
		cookie_jar, browser_used = _load_leetcode_cookies_from_supported_browsers()
		print(f"Using cookies from {browser_used}.")
	except Exception as exc:
		print("Failed to load cookies from supported browsers.")
		print("Make sure you are logged into LeetCode in Chrome/Brave/Firefox and close the browser before retrying.")
		print("If you need Safari, grant Full Disk Access to Terminal/VS Code and Python, then try again.")
		print(f"Error details: {exc}")
		return []

	csrf_token = None
	for cookie in cookie_jar:
		if cookie.name == "csrftoken":
			csrf_token = cookie.value

	if not csrf_token:
		print("Error: Could not find LeetCode CSRF token. Log into LeetCode on your browser first.")
		return []

	headers = {
		"Content-Type": "application/json",
		"x-csrftoken": csrf_token,
		"Referer": "https://leetcode.com/",
	}

	print("Fetching your recent submission history...")
	list_query = """
	query submissionList($offset: Int!, $limit: Int!) {
	  submissionList(offset: $offset, limit: $limit) {
		submissions { id title lang statusDisplay timestamp }
	  }
	}
	"""
	list_payload = {"query": list_query, "variables": {"offset": 0, "limit": limit}}

	response = requests.post(
		"https://leetcode.com/graphql",
		json=list_payload,
		headers=headers,
		cookies=cookie_jar,
		timeout=30,
	)
	response.raise_for_status()

	submissions = response.json().get("data", {}).get("submissionList", {}).get("submissions", [])
	if not submissions:
		print("No submissions found or auth failed.")
		return []

	print(f"Found {len(submissions)} submissions. Downloading code...")
	details_query = """
	query submissionDetails($submissionId: Int!) {
	  submissionDetails(submissionId: $submissionId) { code }
	}
	"""

	final_data = []
	for submission in submissions:
		submission_id = int(submission["id"])
		details_payload = {"query": details_query, "variables": {"submissionId": submission_id}}
		time.sleep(0.5)

		details_response = requests.post(
			"https://leetcode.com/graphql",
			json=details_payload,
			headers=headers,
			cookies=cookie_jar,
			timeout=30,
		)
		details_response.raise_for_status()
		code_data = details_response.json().get("data", {}).get("submissionDetails", {})

		if code_data and code_data.get("code"):
			submission["code"] = code_data["code"]
			final_data.append(submission)
			print(f"Downloaded: {submission['title']} ({submission['statusDisplay']})")

	with open(output_file, "w", encoding="utf-8") as file_handle:
		json.dump(final_data, file_handle, indent=2)

	print(f"Saved {len(final_data)} submissions to {output_file}")
	return final_data


def main():
	parser = argparse.ArgumentParser(description="Scrape LeetCode submissions to a local JSON file.")
	parser.add_argument("--output", default="submissions.json", help="Output JSON path")
	parser.add_argument("--limit", type=int, default=100, help="How many recent submissions to fetch")
	args = parser.parse_args()
	fetch_real_leetcode_data(output_file=args.output, limit=args.limit)


if __name__ == "__main__":
	main()
