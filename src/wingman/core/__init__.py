"""Core orchestration module for Wingman."""

from .agent import MultiTransportAgent, WhatsAppAgent
from .process_manager import NodeProcessManager
from .ipc_handler import IPCHandler, IPCMessage, IPCCommand
from .message_processor import MessageProcessor

__all__ = [
    "MultiTransportAgent",
    "WhatsAppAgent",
    "NodeProcessManager",
    "IPCHandler",
    "IPCMessage",
    "IPCCommand",
    "MessageProcessor",
]
