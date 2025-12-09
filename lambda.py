import os
import json
import re
import time
import hashlib
import logging
from urllib.parse import urlparse

import boto3
import botocore.exceptions
import requests

# ---------------------------------------------------
# Logging setup
# ---------------------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ---------------------------------------------------
# Environment / configuration
# ---------------------------------------------------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")
TABLE_NAME = os.getenv("TABLE_NAME", "travel-agent-leads-v1")

# Email to send the daily/summary report *to you*, not to leads
REPORT_EMAIL = os.getenv("REPORT_EMAIL")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

ses_client = boto3.client("ses")

# ---------------------------------------------------
# Travel search definitions (Pampanga + Subic only)
# ---------------------------------------------------
TRAVEL_QUERIES = [
    # --- ANGELES CITY / PAMPANGA ONLY ---
    '"apartment for rent" "Angeles City" "Pampanga" "long term" "Philippines" -airbnb -filetype:pdf',
    '"furnished condo for rent" "Angeles City" "monthly" "near Clark" "Pampanga" -airbnb -filetype:pdf',
    '"apartment for rent" "Mabalacat" "Pampanga" "long term" -airbnb -filetype:pdf',
    '"apartment for rent" "Clark Freeport" "Pampanga" "long term" -airbnb -filetype:pdf',

    # --- SUBIC / OLONGAPO ONLY ---
    '"apartment for rent" "Subic" "Zambales" "long term" "for rent" -airbnb -filetype:pdf',
    '"condo for rent" "Subic Bay Freeport Zone" "monthly" "furnished" -airbnb -filetype:pdf',
    '"apartment for rent" "Olongapo" "Subic" "furnished" "monthly" -airbnb -filetype:pdf',
    '"apartment for rent" "Olongapo City" "Zambales" "long term" -airbnb -filetype:pdf',
]

# Domains we never want (social OR academic/doc junk)
JUNK_DOMAINS = {
    # Social / general
    "facebook.com",
    "m.facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "tiktok.com",
    "pinterest.com",
    "youtube.com",
    "www.youtube.com",

    # Academic / document repositories
    "academia.edu",
    "evols.library.manoa.hawaii.edu",
    "researchgate.net",
    "scribd.com",
    "zenodo.org",
}

# File extensions to skip entirely
BAD_EXTENSIONS = [
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
]

# ---------------------------------------------------
# Helpers
# ---------------------------------------------------
def normalize_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)


def extract_emails(text: str):
    if not text:
        return []
    emails = set(EMAIL_REGEX.findall(text))
    return sorted(emails)


def google_search(query: str):
    if not GOOGLE_API_KEY or not GOOGLE_CX:
        logger.error("Missing GOOGLE_API_KEY or GOOGLE_CX.")
        return []

    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CX,
        "q": query,
        "num": 10,
    }
    try:
        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params=params,
            timeout=10,
        )
    except Exception as e:
        logger.error("Google search request failed: %s", e)
        return []

    if resp.status_code != 200:
        logger.error("Google search failed (%s): %s", resp.status_code, resp.text)
        return []

    data = resp.json()
    return data.get("items", [])


def make_lead_id(url: str, query: str) -> str:
    h = hashlib.sha256()
    h.update(url.encode("utf-8"))
    h.update(query.encode("utf-8"))
    return h.hexdigest()


def is_bad_filetype(url: str) -> bool:
    low = url.lower()
    return any(low.endswith(ext) for ext in BAD_EXTENSIONS)


def upsert_lead(item, query: str, agent_name: str = "travel_agent_v2_noheadless"):
    url = item.get("link")
    title = item.get("title", "")
    snippet = item.get("snippet", "")

    if not url:
        return None

    # Skip PDFs / Office docs
    if is_bad_filetype(url):
        logger.info("Skipping file-type URL (pdf/doc/etc): %s", url)
        return None

    domain = normalize_domain(url)
    if not domain:
        logger.info("Skipping item with invalid domain: %s", url)
        return None

    if domain in JUNK_DOMAINS:
        logger.info("Skipping junk/academic/social domain: %s (url=%s)", domain, url)
        return None

    # Emails from snippet (Google result) ONLY – no headless
    snippet_emails = extract_emails(snippet)
    page_emails = []
    all_emails = snippet_emails  # same list, kept for compatibility

    lead_id = make_lead_id(url, query)
    now_ts = int(time.time())

    item_to_save = {
        "id": lead_id,
        "url": url,
        "title": title,
        "snippet": snippet,
        "domain": domain,
        "source_query": query,
        "agent_name": agent_name,
        "emails": all_emails,
        "snippet_emails": snippet_emails,
        "page_emails": page_emails,
        "created_at": now_ts,
    }

    table.put_item(Item=item_to_save)
    logger.info(
        "Upserted lead %s for URL=%s (emails from snippet: %d)",
        lead_id,
        url,
        len(snippet_emails),
    )
    return item_to_save


def send_summary_email(leads, total_saved: int):
    """
    Send a simple summary email to REPORT_EMAIL using SES.
    We ONLY email you, not the leads.
    """
    if not REPORT_EMAIL:
        logger.warning("REPORT_EMAIL not set; skipping SES summary email.")
        return

    if not leads:
        logger.info("No leads collected; skipping summary email.")
        return

    lines = []
    lines.append(
        "Travel agent v2 (no headless, Pampanga + Subic only) just completed a run."
    )
    lines.append(f"Total records saved this run: {total_saved}")
    lines.append("")
    lines.append("Sample URLs from this run:")

    for lead in leads[:20]:
        url = lead.get("url", "N/A")
        title = lead.get("title", "").strip()
        emails = lead.get("emails", [])
        email_info = f" | emails: {', '.join(emails[:3])}" if emails else ""
        lines.append(f"- {title[:80]} ({url}){email_info}")

    body_text = "\n".join(lines)

    subject = "Travel Agent Report - Pampanga + Subic (v2, no headless)"

    try:
        response = ses_client.send_email(
            Source=REPORT_EMAIL,
            Destination={"ToAddresses": [REPORT_EMAIL]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": body_text, "Charset": "UTF-8"},
                },
            },
        )
        logger.info("SES summary email sent. MessageId=%s", response["MessageId"])
    except botocore.exceptions.ClientError as e:
        logger.error("Failed to send SES email: %s", e)
    except Exception as e:
        logger.error("Unexpected error sending SES email: %s", e)


# ---------------------------------------------------
# Lambda handler
# ---------------------------------------------------
def lambda_handler(event, context):
    logger.info("Travel agent v2 (no headless, Pampanga + Subic) scanning started.")
    total_saved = 0
    leads_this_run = []
    seen_urls = set()  # avoid saving duplicates in a single run

    for query in TRAVEL_QUERIES:
        items = google_search(query)
        logger.info(
            'Google search for "%s" returned %d items.',
            query,
            len(items),
        )
        for item in items:
            url = item.get("link")
            if not url:
                continue
            if url in seen_urls:
                logger.info("Skipping duplicate URL in this run: %s", url)
                continue
            seen_urls.add(url)

            lead = upsert_lead(item, query, agent_name="travel_agent_v2_noheadless")
            if lead:
                total_saved += 1
                leads_this_run.append(lead)

    logger.info(
        "Travel agent v2 (no headless, Pampanga + Subic) completed. Saved %d records.",
        total_saved,
    )

    # Send SES summary to you (if configured)
    send_summary_email(leads_this_run, total_saved)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Travel agent v2 (no headless, Pampanga + Subic) completed.",
                "saved": total_saved,
            }
        ),
    }
