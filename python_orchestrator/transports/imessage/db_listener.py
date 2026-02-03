"""iMessage database listener for detecting new messages."""

import asyncio
import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Coroutine, List, Optional

logger = logging.getLogger(__name__)

# Apple epoch: seconds between Unix epoch (1970) and Apple epoch (2001)
APPLE_EPOCH_OFFSET = 978307200


@dataclass
class IMessageData:
    """Raw iMessage data from chat.db."""
    rowid: int
    text: str
    handle_id: str  # Phone number or email
    chat_id: str  # Chat identifier
    chat_name: Optional[str]  # Group name if available
    timestamp: float  # Unix timestamp
    is_from_me: bool
    is_group: bool


class IMessageDBListener:
    """
    Polls the iMessage chat.db database for new messages.

    Note: Requires Full Disk Access permission for the Python process.
    """

    # Default chat.db location
    DEFAULT_DB_PATH = Path.home() / "Library" / "Messages" / "chat.db"

    def __init__(
        self,
        db_path: Optional[Path] = None,
        poll_interval: float = 2.0,
    ):
        self._db_path = db_path or self.DEFAULT_DB_PATH
        self._poll_interval = poll_interval
        self._last_rowid = 0
        self._running = False
        self._message_callback: Optional[Callable[[IMessageData], Coroutine]] = None

    def set_message_callback(
        self,
        callback: Callable[[IMessageData], Coroutine]
    ) -> None:
        """Set the callback for new messages."""
        self._message_callback = callback

    async def start(self) -> None:
        """Start polling for new messages."""
        if not self._db_path.exists():
            raise FileNotFoundError(
                f"iMessage database not found: {self._db_path}\n"
                "Ensure Messages.app has been used and Full Disk Access is granted."
            )

        # Get the current max ROWID to start from
        self._last_rowid = self._get_max_rowid()
        logger.info(f"iMessage listener starting from ROWID {self._last_rowid}")

        self._running = True
        await self._poll_loop()

    async def stop(self) -> None:
        """Stop polling."""
        self._running = False
        logger.info("iMessage listener stopped")

    async def _poll_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                messages = self._fetch_new_messages()
                for msg in messages:
                    if self._message_callback:
                        await self._message_callback(msg)
                    self._last_rowid = max(self._last_rowid, msg.rowid)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    logger.debug("Database locked, will retry")
                else:
                    logger.error(f"Database error: {e}")
            except Exception as e:
                logger.error(f"Error polling iMessage database: {e}")

            await asyncio.sleep(self._poll_interval)

    def _get_connection(self) -> sqlite3.Connection:
        """Get a read-only connection to chat.db."""
        # Use URI for read-only access
        conn = sqlite3.connect(
            f"file:{self._db_path}?mode=ro",
            uri=True,
            timeout=5.0
        )
        conn.row_factory = sqlite3.Row
        return conn

    def _get_max_rowid(self) -> int:
        """Get the current maximum ROWID in the messages table."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT MAX(ROWID) FROM message")
                result = cursor.fetchone()
                return result[0] or 0
        except Exception as e:
            logger.error(f"Failed to get max ROWID: {e}")
            return 0

    def _fetch_new_messages(self) -> List[IMessageData]:
        """Fetch messages newer than last_rowid."""
        messages = []

        query = """
            SELECT
                m.ROWID,
                m.text,
                m.attributedBody,
                m.handle_id,
                m.date,
                m.is_from_me,
                h.id as handle_identifier,
                c.chat_identifier,
                c.display_name as chat_name,
                c.style as chat_style
            FROM message m
            LEFT JOIN handle h ON m.handle_id = h.ROWID
            LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
            LEFT JOIN chat c ON cmj.chat_id = c.ROWID
            WHERE m.ROWID > ?
            ORDER BY m.ROWID ASC
            LIMIT 50
        """

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(query, (self._last_rowid,))
                rows = cursor.fetchall()

                for row in rows:
                    # Extract text (handle Ventura+ attributedBody)
                    text = self._extract_text(row)
                    if not text:
                        continue  # Skip messages without text

                    # Convert Apple timestamp to Unix
                    apple_date = row['date']
                    if apple_date:
                        # Apple stores nanoseconds since 2001-01-01
                        unix_timestamp = (apple_date / 1e9) + APPLE_EPOCH_OFFSET
                    else:
                        unix_timestamp = time.time()

                    # Determine if group chat (style > 0 means group)
                    is_group = (row['chat_style'] or 0) > 43

                    msg = IMessageData(
                        rowid=row['ROWID'],
                        text=text,
                        handle_id=row['handle_identifier'] or '',
                        chat_id=row['chat_identifier'] or '',
                        chat_name=row['chat_name'],
                        timestamp=unix_timestamp,
                        is_from_me=bool(row['is_from_me']),
                        is_group=is_group,
                    )
                    messages.append(msg)

        except Exception as e:
            logger.error(f"Failed to fetch new messages: {e}")

        return messages

    def _extract_text(self, row: sqlite3.Row) -> Optional[str]:
        """
        Extract message text from a database row.

        Handles both:
        - Plain text in 'text' column (older macOS)
        - attributedBody blob (Ventura+)
        """
        # Try plain text first
        text = row['text']
        if text:
            return text.strip()

        # Try attributedBody (Ventura+ stores text as NSAttributedString blob)
        attributed_body = row['attributedBody']
        if attributed_body:
            try:
                return self._parse_attributed_body(attributed_body)
            except Exception as e:
                logger.debug(f"Failed to parse attributedBody: {e}")

        return None

    def _parse_attributed_body(self, blob: bytes) -> Optional[str]:
        """
        Parse NSAttributedString blob from attributedBody column.

        The blob contains a serialized NSAttributedString. The actual text
        is stored after a specific marker pattern.
        """
        try:
            # Look for the text content within the blob
            # The structure varies but text is typically after 'NSString' marker
            decoded = blob.decode('utf-8', errors='ignore')

            # Find the actual message text
            # Look for pattern: text follows certain markers
            markers = [
                'NSString',
                'NSMutableString',
            ]

            for marker in markers:
                if marker in decoded:
                    # Text typically follows the marker with some length info
                    idx = decoded.find(marker)
                    # Skip past marker and find readable text
                    remaining = decoded[idx + len(marker):]
                    # Extract printable characters
                    text = ''.join(c for c in remaining if c.isprintable() or c.isspace())
                    text = text.strip()
                    if text and len(text) > 1:
                        # Clean up any trailing garbage
                        # Text usually ends at first control sequence
                        for end_marker in ['\x00', '\x01', '\x02']:
                            if end_marker in text:
                                text = text.split(end_marker)[0]
                        return text.strip() if text.strip() else None

            # Alternative: try to find text between known delimiters
            # streamtyped data format
            if b'streamtyped' in blob:
                # Find text after the plist-like structure
                try:
                    # Look for readable text sequences
                    text_parts = []
                    current = []
                    for byte in blob:
                        if 32 <= byte <= 126:  # Printable ASCII
                            current.append(chr(byte))
                        else:
                            if len(current) > 3:  # Minimum word length
                                text_parts.append(''.join(current))
                            current = []
                    if current and len(current) > 3:
                        text_parts.append(''.join(current))

                    # Filter out known non-text strings
                    filtered = [
                        p for p in text_parts
                        if p not in ['streamtyped', 'NSMutableAttributedString',
                                    'NSAttributedString', 'NSString', 'NSDictionary']
                    ]
                    if filtered:
                        return ' '.join(filtered)
                except Exception:
                    pass

        except Exception as e:
            logger.debug(f"Error parsing attributed body: {e}")

        return None

    @property
    def is_running(self) -> bool:
        """Check if the listener is running."""
        return self._running
