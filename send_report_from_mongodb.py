import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict

from pymongo import MongoClient, DESCENDING
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError


class MongoReportFetcher:

    def __init__(self, mongo_uri: str, db_name: str = "production_db",
                 collection_name: str = "production_records"):
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.collection_name = collection_name
        self.client = None
        self.collection = None

    def connect(self) -> bool:
        try:
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command("ping")
            self.collection = self.client[self.db_name][self.collection_name]
            print(f"  ✅ Connected to MongoDB -> db='{self.db_name}', collection='{self.collection_name}'")
            return True
        except ServerSelectionTimeoutError:
            print("❌ MongoDB Error: Could not connect to server")
            return False
        except PyMongoError as e:
            print(f"❌ MongoDB Error: {str(e)}")
            return False

    def get_latest_report(self) -> Dict:
        try:
            doc = self.collection.find_one(sort=[("generated_at", DESCENDING)])
            if not doc:
                print("⚠️  No report document found in the collection.")
                return {}
            return doc
        except PyMongoError as e:
            print(f"❌ MongoDB Error: Failed to fetch report - {str(e)}")
            return {}

    def close(self) -> None:
        if self.client:
            self.client.close()


class EmailSender:

    def __init__(self, sender_email: str, sender_password: str, recipient_email: str):
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_email = recipient_email

    def send_link_email(self, manifest_url: str, doc: Dict) -> bool:
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            msg['Subject'] = f"Production Analysis Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

            html_content = self._create_link_email(manifest_url, doc)
            msg.attach(MIMEText(html_content, 'html'))

            print("\n📧 Sending link-only email...")
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            print(f"  ✅ Email sent successfully to {self.recipient_email}")
            return True

        except smtplib.SMTPAuthenticationError:
            print("❌ Email Error: Gmail credentials invalid")
            print("   Generate App Password: https://myaccount.google.com/apppasswords")
            return False
        except Exception as e:
            print(f"❌ Email Error: {str(e)}")
            return False

    def _create_link_email(self, manifest_url: str, doc: Dict) -> str:
        total_records = doc.get("total_records", "—")
        total_quantity = doc.get("total_quantity", 0)
        worksheet_name = doc.get("worksheet_name", "—")
        generated_at = doc.get("generated_at", "—")

        try:
            if isinstance(generated_at, datetime):
                generated_at = generated_at.strftime('%d %b %Y, %I:%M %p')
        except Exception:
            pass

        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Production Analysis Report</title>
        </head>
        <body style="margin:0; padding:0; background-color:#f5f5f5; font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
            <div style="max-width:560px; margin:0 auto; padding:40px 20px;">
                <div style="background:linear-gradient(135deg, #2c3e50 0%, #34495e 100%); color:#fff; padding:28px 30px; border-radius:8px 8px 0 0; text-align:center;">
                    <h1 style="margin:0; font-size:24px;">📊 Production Analysis Report</h1>
                    <p style="margin:8px 0 0; font-size:13px; opacity:.85;">Generated: {generated_at}</p>
                </div>
                <div style="background:#ffffff; padding:30px; border-radius:0 0 8px 8px; text-align:center;">
                    <p style="color:#333; font-size:15px; margin:0 0 20px;">
                        Latest production manifest is ready —
                        <strong>{total_records}</strong> records,
                        <strong>{total_quantity:,.0f}</strong> total units
                        (worksheet: {worksheet_name}).
                    </p>
                    <a href="{manifest_url}"
                       style="display:inline-block; background-color:#3498db; color:#ffffff; text-decoration:none;
                              font-weight:600; padding:14px 32px; border-radius:6px; font-size:15px;">
                        View Full Manifest →
                    </a>
                    <p style="margin:24px 0 0; font-size:12px; color:#999; word-break:break-all;">
                        Or copy this link: <a href="{manifest_url}" style="color:#3498db;">{manifest_url}</a>
                    </p>
                </div>
                <p style="text-align:center; color:#aaa; font-size:11px; margin-top:20px;">
                    This report was generated from MongoDB data.
                </p>
            </div>
        </body>
        </html>
        """
        return html


def main():
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    MONGO_DB = "production_db"
    MONGO_COLLECTION = "production_records"

    MANIFEST_URL = os.environ.get(
        "MANIFEST_URL",
        "https://rahilkhan789.github.io/Product_report/"
    )

    SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "rahilkhan784422@gmail.com")
    SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "")
    RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "krahil292@gmail.com")

    if not SENDER_PASSWORD:
        print("❌ Error: SENDER_PASSWORD environment variable is not set.")
        print("   Set it in PowerShell: $env:SENDER_PASSWORD='your-app-password'")
        return

    print("Step 1: Fetching latest report metadata from MongoDB...")
    fetcher = MongoReportFetcher(MONGO_URI, MONGO_DB, MONGO_COLLECTION)
    if not fetcher.connect():
        return

    doc = fetcher.get_latest_report()
    fetcher.close()

    if not doc:
        return

    print(f"  ✅ Latest report: {doc.get('total_records', 0)} records, "
          f"{doc.get('total_quantity', 0):,.0f} total qty")

    print("Step 2: Sending link-only email...")
    email_sender = EmailSender(SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL)
    email_sender.send_link_email(MANIFEST_URL, doc)


if __name__ == "__main__":
    main()
