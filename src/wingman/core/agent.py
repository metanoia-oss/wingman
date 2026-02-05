"""Main agent entry point for the Python orchestrator."""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from wingman.config.registry import ContactRegistry, GroupRegistry
from wingman.config.settings import Settings

from .llm.client import LLMClient
from .memory.models import MessageStore
from .message_processor import MessageProcessor
from .policy import PolicyEvaluator
from .transports import (
    BaseTransport,
    IMessageTransport,
    MessageEvent,
    Platform,
    WhatsAppTransport,
)

logger = logging.getLogger(__name__)


def setup_logging(log_dir: Path) -> None:
    """Set up logging to file and console."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "agent.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stderr)],
    )

    # Reduce noise from some libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


class MultiTransportAgent:
    """
    Multi-transport agent that manages WhatsApp and iMessage.

    Shares MessageProcessor, registries, and LLM across all transports.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = MessageStore(settings.db_path)
        self.llm = LLMClient(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            max_tokens=settings.max_response_tokens,
            temperature=settings.temperature,
        )

        # Initialize config-driven registries
        self.contact_registry = ContactRegistry(settings.contacts_config)
        self.group_registry = GroupRegistry(settings.groups_config)
        self.policy_evaluator = PolicyEvaluator(
            settings.policies_config, bot_name=settings.bot_name
        )

        # Initialize message processor (transport-agnostic)
        self.processor = MessageProcessor(
            store=self.store,
            llm=self.llm,
            contact_registry=self.contact_registry,
            group_registry=self.group_registry,
            policy_evaluator=self.policy_evaluator,
            bot_name=settings.bot_name,
            max_replies_per_hour=settings.max_replies_per_hour,
            default_cooldown=settings.default_cooldown_seconds,
            quiet_start=settings.quiet_hours_start,
            quiet_end=settings.quiet_hours_end,
            context_window=settings.context_window_size,
        )

        # Set up message sender callback
        self.processor.set_sender(self._send_message)

        # Transports
        self.transports: dict[Platform, BaseTransport] = {}
        self._transport_tasks: list[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()

    async def _send_message(self, platform: str, chat_id: str, text: str) -> bool:
        """Route message to appropriate transport."""
        try:
            plat = Platform(platform)
            transport = self.transports.get(plat)
            if transport:
                return await transport.send_message(chat_id, text)
            else:
                logger.error(f"No transport for platform: {platform}")
                return False
        except ValueError:
            logger.error(f"Unknown platform: {platform}")
            return False

    async def _on_message(self, event: MessageEvent) -> None:
        """Handle incoming message from any transport."""
        # Convert MessageEvent to dict format expected by processor
        data = {
            "chatId": event.chat_id,
            "senderId": event.sender_id,
            "senderName": event.sender_name,
            "text": event.text,
            "timestamp": event.timestamp,
            "isGroup": event.is_group,
            "isSelf": event.is_self,
            "platform": event.platform.value,
            "quotedMessage": event.quoted_message,
        }
        await self.processor.process_message(data)

    async def start(self) -> None:
        """Start all configured transports."""
        logger.info("Starting Multi-Transport Agent...")
        logger.info(f"Bot name: {self.settings.bot_name}")
        logger.info(f"Model: {self.settings.openai_model}")

        # Initialize WhatsApp transport
        whatsapp = WhatsAppTransport(
            self.settings.node_dir, auth_state_dir=self.settings.auth_state_dir
        )
        whatsapp.set_message_handler(self._on_message)
        whatsapp.set_connected_handler(self._on_whatsapp_connected)
        self.transports[Platform.WHATSAPP] = whatsapp

        # Initialize iMessage transport if enabled
        if self.settings.imessage_enabled:
            imessage = IMessageTransport(poll_interval=self.settings.imessage_poll_interval)

            # Check if iMessage is available on this system
            if await imessage.check_availability():
                imessage.set_message_handler(self._on_message)
                self.transports[Platform.IMESSAGE] = imessage
                logger.info("iMessage transport initialized")
            else:
                logger.warning(
                    "iMessage not available. Ensure Full Disk Access is granted "
                    "and Messages.app is configured."
                )

        # Start all transports
        for platform, transport in self.transports.items():
            logger.info(f"Starting {platform.value} transport...")
            task = asyncio.create_task(
                self._run_transport(platform, transport), name=f"transport_{platform.value}"
            )
            self._transport_tasks.append(task)

        logger.info(f"Agent started with {len(self.transports)} transport(s)")

        # Wait for shutdown or all tasks to complete
        try:
            await asyncio.gather(*self._transport_tasks)
        except asyncio.CancelledError:
            logger.info("Transport tasks cancelled")

    async def _run_transport(self, platform: Platform, transport: BaseTransport) -> None:
        """Run a single transport, handling errors."""
        try:
            await transport.start()
        except Exception as e:
            logger.error(f"{platform.value} transport error: {e}")
            raise

    async def _on_whatsapp_connected(self, user_id: str) -> None:
        """Handle WhatsApp connection."""
        self.processor.set_self_id(user_id, "whatsapp")

    async def stop(self) -> None:
        """Stop all transports gracefully."""
        logger.info("Stopping agent...")

        # Stop all transports
        for platform, transport in self.transports.items():
            logger.info(f"Stopping {platform.value} transport...")
            try:
                await transport.stop()
            except Exception as e:
                logger.error(f"Error stopping {platform.value}: {e}")

        # Cancel transport tasks
        for task in self._transport_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        logger.info("Agent stopped.")

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        self._shutdown_event.set()


# Keep WhatsAppAgent for backward compatibility
class WhatsAppAgent(MultiTransportAgent):
    """
    Legacy WhatsApp-only agent.

    Deprecated: Use MultiTransportAgent instead.
    """

    def __init__(self, settings: Settings):
        # Disable iMessage for backward compatibility
        settings.imessage_enabled = False
        super().__init__(settings)


async def run_agent(settings: Settings | None = None) -> None:
    """Run the agent with provided settings."""
    # Load settings if not provided
    if settings is None:
        settings = Settings.load()

    # Set up logging
    setup_logging(settings.log_dir)

    # Validate settings
    errors = settings.validate()
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        sys.exit(1)

    # Create agent
    agent = MultiTransportAgent(settings)

    # Set up signal handlers
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Shutdown signal received")
        agent.request_shutdown()
        # Cancel all tasks
        for task in asyncio.all_tasks(loop):
            if task is not asyncio.current_task():
                task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # Run agent
    try:
        await agent.start()
    except asyncio.CancelledError:
        pass
    finally:
        await agent.stop()
