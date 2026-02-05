"""iMessage sender using AppleScript."""

import asyncio
import logging

logger = logging.getLogger(__name__)


class IMessageSender:
    """
    Sends iMessages using AppleScript via osascript.

    Supports both direct messages and group chats.
    """

    def __init__(self):
        self._last_send_time = 0.0

    async def send_message(
        self,
        recipient: str,
        text: str,
        is_group: bool = False,
        chat_id: str | None = None,
    ) -> bool:
        """
        Send an iMessage.

        Args:
            recipient: Phone number, email, or chat identifier
            text: Message text to send
            is_group: Whether this is a group chat
            chat_id: Chat identifier for group messages

        Returns:
            True if send was successful
        """
        try:
            if is_group and chat_id:
                return await self._send_to_group(chat_id, text)
            else:
                return await self._send_to_individual(recipient, text)
        except Exception as e:
            logger.error(f"Failed to send iMessage: {e}")
            return False

    async def _send_to_individual(self, recipient: str, text: str) -> bool:
        """Send a direct message to an individual."""
        # Escape special characters for AppleScript
        escaped_text = self._escape_for_applescript(text)
        escaped_recipient = self._escape_for_applescript(recipient)

        script = f'''
            tell application "Messages"
                set targetService to 1st account whose service type = iMessage
                set targetBuddy to participant "{escaped_recipient}" of targetService
                send "{escaped_text}" to targetBuddy
            end tell
        '''

        return await self._run_applescript(script)

    async def _send_to_group(self, chat_id: str, text: str) -> bool:
        """Send a message to a group chat."""
        escaped_text = self._escape_for_applescript(text)
        escaped_chat_id = self._escape_for_applescript(chat_id)

        # Try to find the chat by its identifier
        script = f'''
            tell application "Messages"
                set targetChat to a reference to chat id "{escaped_chat_id}"
                send "{escaped_text}" to targetChat
            end tell
        '''

        success = await self._run_applescript(script)

        if not success:
            # Fallback: try finding by chat name
            logger.debug("Retrying with chat name lookup")
            script_fallback = f'''
                tell application "Messages"
                    set allChats to every chat
                    repeat with aChat in allChats
                        if id of aChat contains "{escaped_chat_id}" then
                            send "{escaped_text}" to aChat
                            return
                        end if
                    end repeat
                end tell
            '''
            success = await self._run_applescript(script_fallback)

        return success

    async def _run_applescript(self, script: str) -> bool:
        """Execute an AppleScript and return success status."""
        try:
            # Run osascript in a subprocess
            process = await asyncio.create_subprocess_exec(
                'osascript', '-e', script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=10.0
            )

            if process.returncode == 0:
                logger.debug("AppleScript executed successfully")
                return True
            else:
                error_msg = stderr.decode('utf-8').strip()
                logger.error(f"AppleScript error: {error_msg}")
                return False

        except asyncio.TimeoutError:
            logger.error("AppleScript timed out")
            return False
        except Exception as e:
            logger.error(f"Failed to execute AppleScript: {e}")
            return False

    def _escape_for_applescript(self, text: str) -> str:
        """
        Escape special characters for use in AppleScript strings.

        AppleScript uses backslash for escaping within double-quoted strings.
        """
        # Escape backslashes first, then quotes
        text = text.replace('\\', '\\\\')
        text = text.replace('"', '\\"')
        text = text.replace('\n', '\\n')
        text = text.replace('\r', '\\r')
        text = text.replace('\t', '\\t')
        return text

    async def check_messages_app(self) -> bool:
        """Check if Messages.app is available and accessible."""
        script = '''
            tell application "System Events"
                return exists application process "Messages"
            end tell
        '''

        try:
            process = await asyncio.create_subprocess_exec(
                'osascript', '-e', script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, _ = await process.communicate()
            result = stdout.decode('utf-8').strip().lower()
            return result == 'true'

        except Exception as e:
            logger.error(f"Failed to check Messages.app: {e}")
            return False
