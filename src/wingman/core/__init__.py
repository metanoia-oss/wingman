"""Core orchestration module for Wingman."""

from .agent import MultiTransportAgent, WhatsAppAgent
from .ipc_handler import IPCCommand, IPCHandler, IPCMessage
from .message_processor import MessageProcessor
from .process_manager import NodeProcessManager

__all__ = [
    "MultiTransportAgent",
    "WhatsAppAgent",
    "NodeProcessManager",
    "IPCHandler",
    "IPCMessage",
    "IPCCommand",
    "MessageProcessor",
]
