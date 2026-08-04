"""
MCP tools for loading and processing the Monthly Production Excel file.

All logic is delegated to the existing ExcelProcessor class in
production_analysis_mongodb.py - nothing is re-implemented here.
"""

import os
import logging
from typing import Dict

from production_analysis_mongodb import ExcelProcessor
from services.report_state import state_manager

logger = logging.getLogger(__name__)


def register(mcp):

    @mcp.tool()
    def process_excel(file_path: str, worksheet_name: str = "Monthly Production Detail") -> Dict:
        """
        Load and process a Monthly Production Excel file.

        Reuses the existing ExcelProcessor (workbook load, client header
        extraction with color-based priority detection, quantity
        processing). The resulting records are stored in shared state so
        that get_summary(), list_clients(), get_client_report(), and other
        report tools can use them without re-processing the file.

        Args:
            file_path: Absolute path to the .xlsx file.
            worksheet_name: Name of the worksheet to process.

        Returns:
            total_records, total_quantity, total_clients, worksheet_name -
            or an "error" key if processing failed.
        """
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        processor = ExcelProcessor(file_path=file_path, worksheet_name=worksheet_name)

        if not processor.load_workbook():
            return {"error": "Failed to load workbook. Check the file path and format."}

        if not processor.load_worksheet():
            available = ", ".join(processor.workbook.sheetnames) if processor.workbook else ""
            return {"error": f"Worksheet '{worksheet_name}' not found. Available: {available}"}

        if not processor.extract_client_headers():
            return {"error": "Failed to extract client headers."}

        if not processor.process_quantities():
            return {"error": "Failed to process quantities."}

        state_manager.set_report(processor.records, file_path, worksheet_name)

        total_qty = sum(r.quantity for r in processor.records)
        unique_clients = len({r.client_name for r in processor.records})

        logger.info("process_excel: %d records processed from '%s'", len(processor.records), file_path)

        return {
            "total_records": len(processor.records),
            "total_quantity": total_qty,
            "total_clients": unique_clients,
            "worksheet_name": worksheet_name,
        }
