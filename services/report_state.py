"""
In-memory state shared across MCP tool calls.

MCP tools are individually invoked, stateless function calls - there is no
built-in way for `get_summary()` to know what `process_excel()` produced a
moment ago. This module holds that bridge: a single, process-wide store of
the most recently processed report (records + source metadata), so that any
tool can read it without re-processing the Excel file.

This is intentionally simple (a module-level singleton, not a database) -
if the server process restarts, the in-memory state is lost. That is fine
for this use case: `process_excel()` is expected to be called again at the
start of a new session, and long-term persistence is MongoDB's job
(handled separately by mongo_tools.py).
"""

import logging
import threading
from dataclasses import dataclass, field
from typing import List, Optional

from production_analysis_mongodb import ProductionRecord

logger = logging.getLogger(__name__)


@dataclass
class ReportState:
    file_path: Optional[str] = None
    worksheet_name: Optional[str] = None
    records: List[ProductionRecord] = field(default_factory=list)

    def is_loaded(self) -> bool:
        return bool(self.records)


class ReportStateManager:
    """
    Thread-safe singleton wrapper around ReportState.

    Usage:
        from services.report_state import state_manager

        state_manager.set_report(records, file_path, worksheet_name)
        current = state_manager.get_report()
    """

    _instance: Optional["ReportStateManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ReportStateManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._state = ReportState()
                cls._instance._state_lock = threading.Lock()
            return cls._instance

    def set_report(self, records: List[ProductionRecord], file_path: str, worksheet_name: str) -> None:
        with self._state_lock:
            self._state = ReportState(
                file_path=file_path,
                worksheet_name=worksheet_name,
                records=records,
            )
        logger.info(
            "Report state updated: %d records from '%s' (worksheet: %s)",
            len(records), file_path, worksheet_name,
        )

    def get_report(self) -> ReportState:
        with self._state_lock:
            return self._state

    def clear(self) -> None:
        with self._state_lock:
            self._state = ReportState()
        logger.info("Report state cleared.")


# Single shared instance imported by all tool modules.
state_manager = ReportStateManager()
