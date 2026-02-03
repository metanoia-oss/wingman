import { WAMessage, WASocket, proto } from '@whiskeysockets/baileys';
import { sendToPython, log } from './ipc';

export interface ProcessedMessage {
    messageId: string;
    chatId: string;
    senderId: string;
    senderName: string | null;
    text: string;
    timestamp: number;
    isGroup: boolean;
    isSelf: boolean;
    quotedMessage?: {
        text: string;
        senderId: string;
    };
}

/**
 * Extract text content from various message types
 */
function extractText(message: proto.IMessage | null | undefined): string | null {
    if (!message) return null;

    // Direct text message
    if (message.conversation) {
        return message.conversation;
    }

    // Extended text (with mentions, links, etc.)
    if (message.extendedTextMessage?.text) {
        return message.extendedTextMessage.text;
    }

    // Image/video with caption
    if (message.imageMessage?.caption) {
        return message.imageMessage.caption;
    }
    if (message.videoMessage?.caption) {
        return message.videoMessage.caption;
    }

    // Document with caption
    if (message.documentMessage?.caption) {
        return message.documentMessage.caption;
    }

    return null;
}

/**
 * Process incoming WhatsApp message
 */
export function processMessage(
    msg: WAMessage,
    sock: WASocket
): ProcessedMessage | null {
    try {
        const key = msg.key;
        if (!key || !key.remoteJid) {
            return null;
        }

        const chatId = key.remoteJid;
        const isGroup = chatId.endsWith('@g.us');
        const isSelf = key.fromMe || false;

        // Get sender ID
        let senderId: string;
        if (isGroup) {
            senderId = key.participant || chatId;
        } else {
            senderId = isSelf ? (sock.user?.id || 'self') : chatId;
        }

        // Extract text
        const text = extractText(msg.message);
        if (!text) {
            return null; // Skip non-text messages
        }

        // Get sender name
        const senderName = msg.pushName || null;

        // Get timestamp
        const timestamp = msg.messageTimestamp
            ? (typeof msg.messageTimestamp === 'number'
                ? msg.messageTimestamp
                : Number(msg.messageTimestamp))
            : Date.now() / 1000;

        // Check for quoted message
        let quotedMessage: ProcessedMessage['quotedMessage'];
        const contextInfo = msg.message?.extendedTextMessage?.contextInfo;
        if (contextInfo?.quotedMessage) {
            const quotedText = extractText(contextInfo.quotedMessage);
            if (quotedText) {
                quotedMessage = {
                    text: quotedText,
                    senderId: contextInfo.participant || ''
                };
            }
        }

        return {
            messageId: key.id || '',
            chatId,
            senderId,
            senderName,
            text,
            timestamp,
            isGroup,
            isSelf,
            quotedMessage
        };
    } catch (err) {
        log('error', 'Failed to process message', { error: String(err) });
        return null;
    }
}

/**
 * Handle incoming messages and emit to Python
 */
export function handleMessages(messages: WAMessage[], sock: WASocket): void {
    for (const msg of messages) {
        const processed = processMessage(msg, sock);
        if (processed) {
            sendToPython({
                type: 'message',
                data: processed
            });
        }
    }
}
