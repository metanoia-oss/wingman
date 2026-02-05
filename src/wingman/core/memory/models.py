"""SQLite database models and operations."""

import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Represents a stored message."""

    id: int | None
    chat_id: str
    sender_id: str
    sender_name: str | None
    text: str
    timestamp: float
    is_self: bool = False
    platform: str = "whatsapp"


class MessageStore:
    """SQLite-based message storage."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self) -> None:
        """Create database and tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    sender_name TEXT,
                    text TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    is_self BOOLEAN DEFAULT 0,
                    platform TEXT DEFAULT 'whatsapp'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_chat
                ON messages(chat_id, timestamp DESC)
            """)
            # Add platform column if it doesn't exist (migration for existing DBs)
            try:
                conn.execute("SELECT platform FROM messages LIMIT 1")
            except Exception:
                conn.execute("ALTER TABLE messages ADD COLUMN platform TEXT DEFAULT 'whatsapp'")
                logger.info("Added platform column to messages table")
            conn.commit()
            logger.info(f"Database initialized: {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Get a database connection context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def store_message(self, message: Message) -> int:
        """
        Store a message in the database.

        Returns:
            The ID of the inserted message
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO messages (chat_id, sender_id, sender_name, text, timestamp, is_self, platform)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.chat_id,
                    message.sender_id,
                    message.sender_name,
                    message.text,
                    message.timestamp,
                    1 if message.is_self else 0,
                    message.platform,
                ),
            )
            conn.commit()
            msg_id = cursor.lastrowid
            logger.debug(
                f"Stored message {msg_id} in chat {message.chat_id} (platform={message.platform})"
            )
            return msg_id

    def get_recent_messages(self, chat_id: str, limit: int = 30) -> list[Message]:
        """
        Get recent messages from a chat.

        Args:
            chat_id: The chat to get messages from
            limit: Maximum number of messages to return

        Returns:
            List of messages, oldest first
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, chat_id, sender_id, sender_name, text, timestamp, is_self, platform
                FROM messages
                WHERE chat_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (chat_id, limit),
            )
            rows = cursor.fetchall()

        # Convert to Message objects and reverse for chronological order
        messages = [
            Message(
                id=row["id"],
                chat_id=row["chat_id"],
                sender_id=row["sender_id"],
                sender_name=row["sender_name"],
                text=row["text"],
                timestamp=row["timestamp"],
                is_self=bool(row["is_self"]),
                platform=row["platform"] or "whatsapp",
            )
            for row in reversed(rows)
        ]

        logger.debug(f"Retrieved {len(messages)} messages from {chat_id}")
        return messages

    def get_last_sender(self, chat_id: str) -> str | None:
        """
        Get the sender ID of the last message in a chat.

        Returns:
            Sender ID or None if chat is empty
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT sender_id, is_self
                FROM messages
                WHERE chat_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (chat_id,),
            )
            row = cursor.fetchone()

        if row:
            return "self" if row["is_self"] else row["sender_id"]
        return None

    def was_last_message_from_self(self, chat_id: str) -> bool:
        """Check if the last message in a chat was from the bot."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT is_self
                FROM messages
                WHERE chat_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (chat_id,),
            )
            row = cursor.fetchone()

        return bool(row and row["is_self"])

    def get_message_count(self, chat_id: str | None = None) -> int:
        """Get total message count, optionally filtered by chat."""
        with self._get_connection() as conn:
            if chat_id:
                cursor = conn.execute("SELECT COUNT(*) FROM messages WHERE chat_id = ?", (chat_id,))
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM messages")
            return cursor.fetchone()[0]

    def get_recent_chats(self, limit: int = 20) -> list[dict]:
        """Get recently active chats with their last message."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT chat_id, sender_name, text, timestamp, is_self, platform,
                       COUNT(*) as message_count
                FROM messages
                WHERE id IN (
                    SELECT MAX(id) FROM messages GROUP BY chat_id
                )
                GROUP BY chat_id
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()

        return [
            {
                "chat_id": row["chat_id"],
                "last_sender": row["sender_name"] or ("Bot" if row["is_self"] else "Unknown"),
                "last_message": row["text"][:80] if row["text"] else "",
                "timestamp": row["timestamp"],
                "platform": row["platform"] or "whatsapp",
            }
            for row in rows
        ]

    def get_stats(self) -> dict:
        """Get overall message statistics."""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            sent = conn.execute("SELECT COUNT(*) FROM messages WHERE is_self = 1").fetchone()[0]
            received = total - sent
            chats = conn.execute("SELECT COUNT(DISTINCT chat_id) FROM messages").fetchone()[0]

            # Recent activity (last 24h)
            import time

            day_ago = time.time() - 86400
            recent = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE timestamp > ?", (day_ago,)
            ).fetchone()[0]

        return {
            "total_messages": total,
            "sent": sent,
            "received": received,
            "active_chats": chats,
            "messages_last_24h": recent,
        }

    def get_recent_activity(self, limit: int = 20) -> list[dict]:
        """Get recent bot activity (sent messages)."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT chat_id, sender_name, text, timestamp, platform
                FROM messages
                WHERE is_self = 1
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()

        return [
            {
                "chat_id": row["chat_id"],
                "text": row["text"][:80] if row["text"] else "",
                "timestamp": row["timestamp"],
                "platform": row["platform"] or "whatsapp",
            }
            for row in rows
        ]

    def cleanup_old_messages(self, days: int = 30) -> int:
        """
        Delete messages older than specified days.

        Returns:
            Number of deleted messages
        """
        import time

        cutoff = time.time() - (days * 24 * 60 * 60)

        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM messages WHERE timestamp < ?", (cutoff,))
            conn.commit()
            deleted = cursor.rowcount

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old messages")
        return deleted
