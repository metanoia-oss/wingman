import { createSocket, sendMessage, closeSocket } from './socket';
import { setupStdinListener, sendToPython, log, IPCCommand } from './ipc';

/**
 * Handle commands from Python orchestrator
 */
async function handleCommand(cmd: IPCCommand): Promise<void> {
    log('info', 'Received command', { action: cmd.action });

    switch (cmd.action) {
        case 'send_message':
            if (cmd.payload?.jid && cmd.payload?.text) {
                const success = await sendMessage(cmd.payload.jid, cmd.payload.text);
                sendToPython({
                    type: 'send_result',
                    data: {
                        success,
                        jid: cmd.payload.jid,
                        messageId: cmd.payload.messageId
                    }
                });
            } else {
                sendToPython({
                    type: 'error',
                    data: { message: 'send_message requires jid and text in payload' }
                });
            }
            break;

        case 'ping':
            sendToPython({ type: 'pong' });
            break;

        case 'shutdown':
            log('info', 'Shutdown requested');
            sendToPython({ type: 'shutting_down' });
            await closeSocket();
            process.exit(0);
            break;

        default:
            log('warn', 'Unknown command', { action: cmd.action });
            sendToPython({
                type: 'error',
                data: { message: `Unknown action: ${cmd.action}` }
            });
    }
}

/**
 * Main entry point
 */
async function main(): Promise<void> {
    log('info', 'Starting WhatsApp listener...');
    sendToPython({ type: 'starting' });

    // Set up stdin listener for commands from Python
    setupStdinListener(handleCommand);

    // Handle graceful shutdown
    process.on('SIGINT', async () => {
        log('info', 'SIGINT received, shutting down');
        sendToPython({ type: 'shutting_down' });
        await closeSocket();
        process.exit(0);
    });

    process.on('SIGTERM', async () => {
        log('info', 'SIGTERM received, shutting down');
        sendToPython({ type: 'shutting_down' });
        await closeSocket();
        process.exit(0);
    });

    // Handle uncaught errors
    process.on('uncaughtException', (err) => {
        log('error', 'Uncaught exception', { error: String(err), stack: err.stack });
        sendToPython({
            type: 'error',
            data: { message: `Uncaught exception: ${err.message}` }
        });
    });

    process.on('unhandledRejection', (reason) => {
        log('error', 'Unhandled rejection', { reason: String(reason) });
        sendToPython({
            type: 'error',
            data: { message: `Unhandled rejection: ${reason}` }
        });
    });

    try {
        await createSocket();
        log('info', 'Socket created, waiting for connection...');
    } catch (err) {
        log('error', 'Failed to create socket', { error: String(err) });
        sendToPython({
            type: 'error',
            data: { message: `Failed to create socket: ${err}` }
        });
        process.exit(1);
    }
}

main().catch((err) => {
    log('error', 'Fatal error in main', { error: String(err) });
    process.exit(1);
});
