import * as readline from 'readline';

export interface IPCMessage {
    type: string;
    data?: any;
}

export interface IPCCommand {
    action: string;
    payload?: any;
}

const NULL_CHAR = '\0';

/**
 * Send a message to Python via stdout using NULL-delimited JSON
 */
export function sendToPython(message: IPCMessage): void {
    const json = JSON.stringify(message);
    process.stdout.write(json + NULL_CHAR);
}

/**
 * Set up stdin listener for commands from Python
 */
export function setupStdinListener(onCommand: (cmd: IPCCommand) => void): void {
    let buffer = '';

    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk: string) => {
        buffer += chunk;

        // Process all complete messages (NULL-delimited)
        let nullIndex: number;
        while ((nullIndex = buffer.indexOf(NULL_CHAR)) !== -1) {
            const jsonStr = buffer.slice(0, nullIndex);
            buffer = buffer.slice(nullIndex + 1);

            if (jsonStr.trim()) {
                try {
                    const command = JSON.parse(jsonStr) as IPCCommand;
                    onCommand(command);
                } catch (err) {
                    sendToPython({
                        type: 'error',
                        data: { message: `Failed to parse command: ${err}` }
                    });
                }
            }
        }
    });

    process.stdin.on('end', () => {
        sendToPython({ type: 'stdin_closed' });
        process.exit(0);
    });
}

/**
 * Log a message (goes to stderr to not interfere with IPC)
 */
export function log(level: 'info' | 'warn' | 'error', message: string, data?: any): void {
    const logEntry = {
        timestamp: new Date().toISOString(),
        level,
        message,
        ...(data && { data })
    };
    process.stderr.write(JSON.stringify(logEntry) + '\n');
}
