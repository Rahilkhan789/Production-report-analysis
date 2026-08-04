"""
MCP tools for loading and processing the Monthly Production Excel file.
"""

import os
import logging
import tempfile
from typing import Dict

import requests

from production_analysis_mongodb import ExcelProcessor
from services.report_state import state_manager

logger = logging.getLogger(__name__)


def register(mcp):

    @mcp.tool()
    def process_excel(
        file_path: str,
        worksheet_name: str = "Monthly Production Detail",
    ) -> Dict:

        # ----------------------------
        # HTTP / HTTPS URL support
        # ----------------------------
        if file_path.startswith("http://") or file_path.startswith("https://"):

            response = requests.get(file_path)

            if response.status_code != 200:
                return {
                    "error": f"Unable to download file ({response.status_code})"
                }

            temp = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".xlsx"
            )

            temp.write(response.content)
            temp.close()

            file_path = temp.name

        # ----------------------------
        # Local file support
        # ----------------------------
        elif not os.path.exists(file_path):

            return {
                "error": f"File not found: {file_path}"
            }

        # ----------------------------
        # Existing processing logic
        # ----------------------------

        processor = ExcelProcessor(
            file_path=file_path,
            worksheet_name=worksheet_name
        )

        if not processor.load_workbook():
            return {
                "error": "Failed to load workbook. Check the file path and format."
            }

        if not processor.load_worksheet():
            available = (
                ", ".join(processor.workbook.sheetnames)
                if processor.workbook
                else ""
            )

            return {
                "error": f"Worksheet '{worksheet_name}' not found. Available: {available}"
            }

        if not processor.extract_client_headers():
            return {
                "error": "Failed to extract client headers."
            }

        if not processor.process_quantities():
            return {
                "error": "Failed to process quantities."
            }

        state_manager.set_report(
            processor.records,
            file_path,
            worksheet_name
        )

        total_qty = sum(r.quantity for r in processor.records)

        unique_clients = len(
            {
                r.client_name
                for r in processor.records
            }
        )

        logger.info(
            "process_excel: %d records processed from '%s'",
            len(processor.records),
            file_path
        )

        return {
            "total_records": len(processor.records),
            "total_quantity": total_qty,
            "total_clients": unique_clients,
            "worksheet_name": worksheet_name,
        }