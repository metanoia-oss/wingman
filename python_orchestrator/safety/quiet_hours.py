"""Quiet hours enforcement."""

import logging
from datetime import datetime, time as dt_time
from typing import Optional

logger = logging.getLogger(__name__)


class QuietHoursChecker:
    """
    Enforces quiet hours during which the bot will not respond.
    Default: midnight (0:00) to 6:00 AM.
    """

    def __init__(
        self,
        start_hour: int = 0,
        end_hour: int = 6,
        enabled: bool = True
    ):
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.enabled = enabled

    def is_quiet_time(self, check_time: Optional[datetime] = None) -> bool:
        """
        Check if the given time falls within quiet hours.

        Args:
            check_time: Time to check (defaults to current time)

        Returns:
            True if currently in quiet hours
        """
        if not self.enabled:
            return False

        if check_time is None:
            check_time = datetime.now()

        current_hour = check_time.hour

        # Handle both same-day and overnight ranges
        if self.start_hour <= self.end_hour:
            # Same day range (e.g., 9 AM to 5 PM)
            is_quiet = self.start_hour <= current_hour < self.end_hour
        else:
            # Overnight range (e.g., 10 PM to 6 AM)
            is_quiet = current_hour >= self.start_hour or current_hour < self.end_hour

        if is_quiet:
            logger.debug(
                f"Quiet hours active: {self.start_hour}:00 - {self.end_hour}:00, "
                f"current hour: {current_hour}"
            )

        return is_quiet

    def get_end_time(self) -> dt_time:
        """Get the time when quiet hours end."""
        return dt_time(hour=self.end_hour)

    def set_hours(self, start: int, end: int) -> None:
        """Update quiet hours range."""
        if not (0 <= start <= 23 and 0 <= end <= 23):
            raise ValueError("Hours must be between 0 and 23")
        self.start_hour = start
        self.end_hour = end
        logger.info(f"Quiet hours updated: {start}:00 - {end}:00")

    def disable(self) -> None:
        """Disable quiet hours."""
        self.enabled = False
        logger.info("Quiet hours disabled")

    def enable(self) -> None:
        """Enable quiet hours."""
        self.enabled = True
        logger.info("Quiet hours enabled")
