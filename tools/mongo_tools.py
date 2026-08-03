"""
MCP tools for MongoDB storage/retrieval and manifest/JSON generation.

Reuses MongoStorage and ExcelProcessor.save_manifest_html/save_json_file
from production_analysis_mongodb.py, and MongoReportFetcher from
send_report_from_mongodb.py. No storage or file-generation logic is
duplicated here.
"""

import os
import logging
from typing import Dict

from production_analysis_mongodb import ExcelProcessor, MongoStorage
from send_report_from_mongodb import MongoReportFetcher
from services.report_state import state_manager

logger = logging.getLogger(__name__)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.environ.get("MONGO_DB", "production_db")
MONGO_COLLECTION = os.environ.get("MONGO_COLLECTION", "production_records")


def register(mcp):

    @mcp.tool()
    def save_to_mongodb() -> Dict:
        """
        Save the currently loaded report's records to MongoDB as a single
        report document. Reuses MongoStorage.insert_records() with
        as_single_document=True, matching the existing pipeline's behavior.
        """
        state = state_manager.get_report()
        if not state.is_loaded():
            return {"error": "No report loaded. Call process_excel() first."}

        storage = MongoStorage(MONGO_URI, MONGO_DB, MONGO_COLLECTION)
        if not storage.connect():
            return {"error": "Could not connect to MongoDB. Check MONGO_URI."}

        try:
            success = storage.insert_records(
                state.records, state.file_path, state.worksheet_name,
                as_single_document=True,
            )
        finally:
            storage.close()

        if not success:
            return {"error": "Failed to insert records into MongoDB."}

        return {
            "status": "saved",
            "total_records": len(state.records),
            "db": MONGO_DB,
            "collection": MONGO_COLLECTION,
        }

    @mcp.tool()
    def latest_report() -> Dict:
        """
        Fetch the most recently saved report document from MongoDB.
        Reuses MongoReportFetcher.get_latest_report(). Reads directly from
        the database, so process_excel() does not need to be called first.
        """
        fetcher = MongoReportFetcher(MONGO_URI, MONGO_DB, MONGO_COLLECTION)
        if not fetcher.connect():
            return {"error": "Could not connect to MongoDB. Check MONGO_URI."}

        try:
            doc = fetcher.get_latest_report()
        finally:
            fetcher.close()

        if not doc:
            return {"error": "No report document found in MongoDB."}

        return {
            "generated_at": str(doc.get("generated_at", "")),
            "total_records": doc.get("total_records", 0),
            "total_quantity": doc.get("total_quantity", 0),
            "worksheet_name": doc.get("worksheet_name", ""),
            "file_path": doc.get("file_path", ""),
        }

    @mcp.tool()
    def generate_manifest(output_path: str = "production_manifest.html") -> Dict:
        """
        Generate the accordion-style HTML manifest for the currently loaded
        report. Reuses ExcelProcessor.save_manifest_html(), which fills
        manifest_template.html with the report data.

        Args:
            output_path: Where to write the generated manifest HTML file.
        """
        state = state_manager.get_report()
        if not state.is_loaded():
            return {"error": "No report loaded. Call process_excel() first."}

        processor = ExcelProcessor(file_path=state.file_path, worksheet_name=state.worksheet_name)
        processor.records = state.records

        if not processor.save_manifest_html(output_path):
            return {"error": "Failed to generate manifest HTML."}

        return {"status": "generated", "path": os.path.abspath(output_path)}

    @mcp.tool()
    def generate_json(output_path: str = "production_records.json") -> Dict:
        """
        Save the currently loaded report as a JSON file. Reuses
        ExcelProcessor.save_json_file().

        Args:
            output_path: Where to write the generated JSON file.
        """
        state = state_manager.get_report()
        if not state.is_loaded():
            return {"error": "No report loaded. Call process_excel() first."}

        processor = ExcelProcessor(file_path=state.file_path, worksheet_name=state.worksheet_name)
        processor.records = state.records

        if not processor.save_json_file(output_path):
            return {"error": "Failed to save JSON file."}

        return {"status": "saved", "path": os.path.abspath(output_path)}
