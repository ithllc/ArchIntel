#!/usr/bin/env python3
"""
Gemini CLI Daily Quota Manager.

Tracks daily request counts and enforces a configurable threshold.
When the threshold is reached, requests are blocked and default responses are returned.

Usage:
    from quota_manager import GeminiQuotaManager

    quota = GeminiQuotaManager(daily_limit=250)

    if quota.can_make_request():
        # Make Gemini CLI call
        quota.record_request()
    else:
        # Return default response
        response = quota.get_fallback_response(query)

Configuration:
    Environment variables:
    - GEMINI_DAILY_LIMIT: Maximum requests per day (default: 250)
    - GEMINI_QUOTA_FILE: Path to quota tracking file (default: .gemini_quota.json)
"""

import json
import os
from datetime import datetime, date
from typing import Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger("gemini-quota")


class GeminiQuotaManager:
    """
    Manages daily quota for Gemini CLI requests.

    Attributes:
        daily_limit: Maximum requests allowed per day
        quota_file: Path to the JSON file storing quota data
    """

    def __init__(
        self,
        daily_limit: int = None,
        quota_file: str = None,
        location_id: str = "default"
    ):
        """
        Initialize the quota manager.

        Args:
            daily_limit: Max requests per day (default from env or 250)
            quota_file: Path to quota tracking file
            location_id: Identifier for this quota instance (e.g., "claude", "github")
        """
        self.daily_limit = daily_limit or int(os.environ.get("GEMINI_DAILY_LIMIT", "250"))
        self.location_id = location_id

        # Determine quota file path
        if quota_file:
            self.quota_file = Path(quota_file)
        else:
            default_path = os.environ.get(
                "GEMINI_QUOTA_FILE",
                str(Path(__file__).parent / f".gemini_quota_{location_id}.json")
            )
            self.quota_file = Path(default_path)

        # Ensure parent directory exists
        self.quota_file.parent.mkdir(parents=True, exist_ok=True)

        # Load or initialize quota data
        self._load_quota()

    def _load_quota(self) -> None:
        """Load quota data from file or initialize if not exists."""
        if self.quota_file.exists():
            try:
                with open(self.quota_file, 'r') as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._data = self._get_fresh_data()
        else:
            self._data = self._get_fresh_data()

        # Reset if it's a new day
        if self._data.get("date") != str(date.today()):
            self._data = self._get_fresh_data()
            self._save_quota()

    def _get_fresh_data(self) -> Dict[str, Any]:
        """Get fresh quota data for a new day."""
        return {
            "date": str(date.today()),
            "requests": 0,
            "limit": self.daily_limit,
            "location_id": self.location_id,
            "blocked_count": 0,
            "last_request": None,
            "history": []
        }

    def _save_quota(self) -> None:
        """Save quota data to file."""
        try:
            with open(self.quota_file, 'w') as f:
                json.dump(self._data, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save quota file: {e}")

    def can_make_request(self) -> bool:
        """
        Check if a request can be made within the daily quota.

        Returns:
            True if under quota limit, False if quota exceeded
        """
        # Reload to check for day change
        self._load_quota()
        return self._data["requests"] < self.daily_limit

    def record_request(self, query: str = None, success: bool = True) -> Dict[str, Any]:
        """
        Record a successful request against the quota.

        Args:
            query: The query that was made (optional, for logging)
            success: Whether the request was successful

        Returns:
            Current quota status
        """
        self._load_quota()

        self._data["requests"] += 1
        self._data["last_request"] = datetime.now().isoformat()

        # Keep last 10 requests in history for debugging
        if len(self._data.get("history", [])) >= 10:
            self._data["history"] = self._data["history"][-9:]

        self._data["history"].append({
            "timestamp": datetime.now().isoformat(),
            "query_preview": (query[:50] + "...") if query and len(query) > 50 else query,
            "success": success
        })

        self._save_quota()

        return self.get_status()

    def record_blocked(self) -> None:
        """Record a blocked request (quota exceeded)."""
        self._load_quota()
        self._data["blocked_count"] = self._data.get("blocked_count", 0) + 1
        self._save_quota()

    def get_status(self) -> Dict[str, Any]:
        """
        Get current quota status.

        Returns:
            Dictionary with quota information
        """
        self._load_quota()

        remaining = max(0, self.daily_limit - self._data["requests"])
        percentage_used = (self._data["requests"] / self.daily_limit) * 100

        return {
            "date": self._data["date"],
            "requests_made": self._data["requests"],
            "daily_limit": self.daily_limit,
            "remaining": remaining,
            "percentage_used": round(percentage_used, 1),
            "quota_exceeded": remaining == 0,
            "blocked_count": self._data.get("blocked_count", 0),
            "last_request": self._data.get("last_request"),
            "location_id": self.location_id
        }

    def get_remaining(self) -> int:
        """Get number of remaining requests for today."""
        self._load_quota()
        return max(0, self.daily_limit - self._data["requests"])

    def get_fallback_response(self, query: str) -> Dict[str, Any]:
        """
        Generate a fallback response when quota is exceeded.

        Args:
            query: The original query

        Returns:
            Fallback response dictionary
        """
        self.record_blocked()

        status = self.get_status()

        return {
            "error": "quota_exceeded",
            "message": f"Daily Gemini CLI quota exceeded ({status['daily_limit']} requests/day). "
                      f"Quota resets at midnight UTC.",
            "fallback": True,
            "quota_status": status,
            "recommendation": "Please use Claude's built-in capabilities for this request, "
                             "or wait until the quota resets tomorrow.",
            "query_received": query[:100] + "..." if len(query) > 100 else query
        }

    def reset_quota(self, confirm: bool = False) -> Dict[str, Any]:
        """
        Manually reset the quota (for admin use).

        Args:
            confirm: Must be True to actually reset

        Returns:
            Status after reset
        """
        if not confirm:
            return {"error": "Must set confirm=True to reset quota"}

        self._data = self._get_fresh_data()
        self._save_quota()

        logger.info(f"Quota manually reset for {self.location_id}")
        return self.get_status()


# Singleton instances for each location
_quota_instances: Dict[str, GeminiQuotaManager] = {}


def get_quota_manager(location_id: str = "default", daily_limit: int = 250) -> GeminiQuotaManager:
    """
    Get or create a quota manager instance for the specified location.

    Args:
        location_id: Identifier for this quota instance
        daily_limit: Maximum requests per day

    Returns:
        GeminiQuotaManager instance
    """
    if location_id not in _quota_instances:
        _quota_instances[location_id] = GeminiQuotaManager(
            daily_limit=daily_limit,
            location_id=location_id
        )
    return _quota_instances[location_id]


if __name__ == "__main__":
    # CLI for checking quota status
    import sys

    location = sys.argv[1] if len(sys.argv) > 1 else "default"
    quota = get_quota_manager(location)

    print(json.dumps(quota.get_status(), indent=2))
