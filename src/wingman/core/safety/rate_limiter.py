"""Global rate limiting for bot replies."""

import time
import logging
from collections import deque
from typing import Deque

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Implements a sliding window rate limiter.
    Tracks replies in a 1-hour window and enforces max replies limit.
    """

    def __init__(self, max_replies_per_hour: int = 30):
        self.max_replies = max_replies_per_hour
        self.window_seconds = 3600  # 1 hour
        self._timestamps: Deque[float] = deque()

    def _cleanup_old_entries(self) -> None:
        """Remove timestamps older than the window."""
        cutoff = time.time() - self.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    def can_reply(self) -> bool:
        """Check if a reply is allowed within rate limits."""
        self._cleanup_old_entries()
        allowed = len(self._timestamps) < self.max_replies

        if not allowed:
            logger.warning(
                f"Rate limit reached: {len(self._timestamps)}/{self.max_replies} "
                f"replies in the last hour"
            )

        return allowed

    def record_reply(self) -> None:
        """Record that a reply was sent."""
        self._cleanup_old_entries()
        self._timestamps.append(time.time())
        logger.debug(
            f"Reply recorded: {len(self._timestamps)}/{self.max_replies} "
            f"in current window"
        )

    def get_remaining(self) -> int:
        """Get number of remaining allowed replies."""
        self._cleanup_old_entries()
        return max(0, self.max_replies - len(self._timestamps))

    def get_reset_time(self) -> float:
        """Get seconds until oldest reply expires from window."""
        if not self._timestamps:
            return 0
        oldest = self._timestamps[0]
        return max(0, (oldest + self.window_seconds) - time.time())
