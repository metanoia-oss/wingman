import makeWASocket, {
    DisconnectReason,
    useMultiFileAuthState,
    WASocket,
    ConnectionState,
    fetchLatestBaileysVersion
} from '@whiskeysockets/baileys';
import { Boom } from '@hapi/boom';
import * as qrcode from 'qrcode-terminal';
import * as path from 'path';
import * as fs from 'fs';
import { sendToPython, log } from './ipc';
import { handleMessages } from './messageHandler';
import pino from 'pino';

const AUTH_DIR = path.join(__dirname, '..', '..', 'auth_state');
const STARTUP_DELAY_FILE = path.join(__dirname, '..', '..', '.last_disconnect');

let sock: WASocket | null = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;
let isConnecting = false;  // Prevent concurrent connection attempts
const MIN_RESTART_DELAY_MS = 5000;  // Minimum time between sessions

/**
 * Close existing socket connection gracefully
 */
async function closeExistingSocket(): Promise<void> {
    if (sock) {
        log('info', 'Closing existing socket connection');
        try {
            sock.ev.removeAllListeners('connection.update');
            sock.ev.removeAllListeners('creds.update');
            sock.ev.removeAllListeners('messages.upsert');
            await sock.logout().catch(() => {});  // Ignore logout errors
            sock.end(undefined);
        } catch (err) {
            log('warn', 'Error closing socket', { error: String(err) });
        }
        sock = null;
        // Give WhatsApp servers time to register the disconnect
        await new Promise(resolve => setTimeout(resolve, 2000));
    }
}

/**
 * Check if we need to wait before connecting (to avoid 440 errors)
 */
async function enforceStartupDelay(): Promise<void> {
    try {
        if (fs.existsSync(STARTUP_DELAY_FILE)) {
            const lastDisconnect = parseInt(fs.readFileSync(STARTUP_DELAY_FILE, 'utf-8'), 10);
            const elapsed = Date.now() - lastDisconnect;
            const waitTime = MIN_RESTART_DELAY_MS - elapsed;

            if (waitTime > 0) {
                log('info', `Waiting ${waitTime}ms before connecting (anti-440 delay)`);
                await new Promise(resolve => setTimeout(resolve, waitTime));
            }
        }
    } catch (err) {
        // Ignore errors reading the file
    }
}

/**
 * Record disconnect time for anti-440 protection
 */
function recordDisconnectTime(): void {
    try {
        fs.writeFileSync(STARTUP_DELAY_FILE, Date.now().toString());
    } catch (err) {
        // Ignore errors writing the file
    }
}

/**
 * Create and initialize WhatsApp socket connection
 */
export async function createSocket(): Promise<WASocket> {
    // Prevent concurrent connection attempts
    if (isConnecting) {
        log('warn', 'Connection already in progress, skipping');
        return sock!;
    }

    isConnecting = true;

    try {
        // Wait if we disconnected recently (anti-440 protection)
        await enforceStartupDelay();

        // Close any existing connection first
        await closeExistingSocket();

        const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
        const { version } = await fetchLatestBaileysVersion();

        // Create silent logger for Baileys
        const logger = pino({ level: 'silent' });

        log('info', 'Creating socket with auth state', { authDir: AUTH_DIR });

        sock = makeWASocket({
            version,
            auth: state,
            logger,
            browser: ['WhatsApp Agent', 'Chrome', '120.0.0'],
            connectTimeoutMs: 60000,
            keepAliveIntervalMs: 30000,
            retryRequestDelayMs: 2000,
            markOnlineOnConnect: false,  // Don't mark online to reduce conflicts
            syncFullHistory: false,      // Don't sync history to reduce footprint
        });

        // Handle connection updates
        sock.ev.on('connection.update', (update: Partial<ConnectionState>) => {
            handleConnectionUpdate(update, saveCreds);
        });

        // Save credentials on update
        sock.ev.on('creds.update', saveCreds);

        // Handle incoming messages
        sock.ev.on('messages.upsert', async (m) => {
            if (m.type === 'notify' && sock) {
                handleMessages(m.messages, sock);
            }
        });

        return sock;
    } finally {
        isConnecting = false;
    }
}

/**
 * Handle connection state changes
 */
function handleConnectionUpdate(
    update: Partial<ConnectionState>,
    saveCreds: () => Promise<void>
): void {
    const { connection, lastDisconnect, qr } = update;

    // Display QR code for scanning
    if (qr) {
        log('info', 'QR Code received, display in terminal');
        process.stderr.write('\n=== Scan this QR code with WhatsApp ===\n\n');
        qrcode.generate(qr, { small: true }, (qrString) => {
            process.stderr.write(qrString + '\n');
        });
        sendToPython({ type: 'qr_code', data: { qr } });
    }

    if (connection === 'close') {
        const statusCode = (lastDisconnect?.error as Boom)?.output?.statusCode;
        const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

        log('warn', 'Connection closed', { statusCode, shouldReconnect });
        sendToPython({
            type: 'disconnected',
            data: { statusCode, shouldReconnect }
        });

        if (statusCode === DisconnectReason.loggedOut) {
            log('info', 'Logged out, reconnecting for new QR code...');
            sendToPython({ type: 'logged_out' });
            // Reconnect to get a new QR code
            setTimeout(() => {
                createSocket().catch((err) => {
                    log('error', 'Reconnection failed', { error: String(err) });
                });
            }, 2000);
        } else if (shouldReconnect && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
            log('info', `Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`);

            setTimeout(() => {
                createSocket().catch((err) => {
                    log('error', 'Reconnection failed', { error: String(err) });
                });
            }, delay);
        } else {
            log('error', 'Max reconnection attempts reached');
            sendToPython({ type: 'max_reconnect_reached' });
            process.exit(1);
        }
    } else if (connection === 'open') {
        reconnectAttempts = 0;
        log('info', 'Connection established');
        sendToPython({
            type: 'connected',
            data: { user: sock?.user }
        });
    }
}

/**
 * Send a text message
 */
export async function sendMessage(jid: string, text: string): Promise<boolean> {
    if (!sock) {
        log('error', 'Cannot send message: socket not initialized');
        return false;
    }

    try {
        await sock.sendMessage(jid, { text });
        log('info', 'Message sent', { jid, textLength: text.length });
        return true;
    } catch (err) {
        log('error', 'Failed to send message', { jid, error: String(err) });
        return false;
    }
}

/**
 * Get the current socket instance
 */
export function getSocket(): WASocket | null {
    return sock;
}

/**
 * Gracefully close the socket connection
 */
export async function closeSocket(): Promise<void> {
    if (sock) {
        log('info', 'Gracefully closing socket');
        try {
            sock.ev.removeAllListeners('connection.update');
            sock.ev.removeAllListeners('creds.update');
            sock.ev.removeAllListeners('messages.upsert');
            sock.end(undefined);
        } catch (err) {
            log('warn', 'Error during socket close', { error: String(err) });
        }
        sock = null;
        // Record disconnect time for anti-440 protection on next startup
        recordDisconnectTime();
    }
}
