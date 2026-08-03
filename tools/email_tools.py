"""
MCP tools for sending report emails.

There are two distinct EmailSender classes in the existing codebase with
different behavior:
  - production_analysis_mongodb.EmailSender: sends the full HTML report
    (data table, priority breakdown, top clients), optionally with an
    attachment.
  - send_report_from_mongodb.EmailSender: sends a lightweight email
    containing only a link to the live hosted manifest.

Both are imported and aliased here to avoid the naming collision, and
neither is reimplemented.
"""

import os
import logging
from typing import Dict, Optional

from production_analysis_mongodb import EmailSender as FullReportEmailSender
from send_report_from_mongodb import EmailSender as LinkEmailSender, MongoReportFetcher
from services.report_state import state_manager

logger = logging.getLogger(__name__)

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "")
MANIFEST_URL = os.environ.get("MANIFEST_URL", "")

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.environ.get("MONGO_DB", "production_db")
MONGO_COLLECTION = os.environ.get("MONGO_COLLECTION", "production_records")


def _check_email_config() -> Optional[Dict]:
    if not (SENDER_EMAIL and SENDER_PASSWORD and RECIPIENT_EMAIL):
        return {
            "error": (
                "Email is not configured. Set SENDER_EMAIL, SENDER_PASSWORD, "
                "and RECIPIENT_EMAIL environment variables."
            )
        }
    return None


def register(mcp):

    @mcp.tool()
    def send_email(manifest_path: Optional[str] = "production_manifest.html") -> Dict:
        """
        Send the full HTML report (data table, priority breakdown, top
        clients) as an email for the currently loaded report. Reuses
        EmailSender.send_report() from production_analysis_mongodb.py.

        Args:
            manifest_path: Optional path to a manifest HTML file to attach,
                if it exists on disk.
        """
        err = _check_email_config()
        if err:
            return err

        state = state_manager.get_report()
        if not state.is_loaded():
            return {"error": "No report loaded. Call process_excel() first."}

        sender = FullReportEmailSender(SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL)
        attachment = manifest_path if manifest_path and os.path.exists(manifest_path) else None

        success = sender.send_report(
            state.records, state.file_path, state.worksheet_name,
            attachment_path=attachment,
        )

        if not success:
            return {"error": "Failed to send email. Check server logs and Gmail App Password."}

        return {"status": "sent", "recipient": RECIPIENT_EMAIL, "attachment": attachment}

    @mcp.tool()
    def send_manifest_link() -> Dict:
        """
        Send a lightweight email containing only a link to the live hosted
        manifest - no attachment, no data table. Reuses
        EmailSender.send_link_email() from send_report_from_mongodb.py.

        Pulls the latest report metadata (record count, quantity,
        worksheet) directly from MongoDB, so process_excel() does not need
        to be called first - only save_to_mongodb() needs to have run at
        some point.
        """
        err = _check_email_config()
        if err:
            return err

        if not MANIFEST_URL:
            return {"error": "MANIFEST_URL environment variable is not set."}

        fetcher = MongoReportFetcher(MONGO_URI, MONGO_DB, MONGO_COLLECTION)
        if not fetcher.connect():
            return {"error": "Could not connect to MongoDB. Check MONGO_URI."}

        try:
            doc = fetcher.get_latest_report()
        finally:
            fetcher.close()

        if not doc:
            return {"error": "No report document found in MongoDB. Call save_to_mongodb() first."}

        sender = LinkEmailSender(SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL)
        success = sender.send_link_email(MANIFEST_URL, doc)

        if not success:
            return {"error": "Failed to send email. Check server logs and Gmail App Password."}

        return {"status": "sent", "recipient": RECIPIENT_EMAIL, "manifest_url": MANIFEST_URL}
