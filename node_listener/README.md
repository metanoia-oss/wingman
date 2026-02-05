# wingman-ai (Node.js Listener)

WhatsApp listener component for [Wingman AI](https://github.com/metanoia-oss/wingman) - an AI-powered personal chat agent.

This package connects to WhatsApp Web using the [Baileys](https://github.com/WhiskeySockets/Baileys) library and communicates with the Wingman Python orchestrator via IPC.

## Installation

This package is typically installed automatically by the Wingman CLI:

```bash
pip install wingman-ai
wingman init
```

For manual installation:

```bash
npm install wingman-ai
```

## Usage

This package is designed to be used as a subprocess managed by the Wingman Python orchestrator. It communicates via stdin/stdout using JSON messages.

### Standalone Usage

```bash
# Build
npm run build

# Run (requires auth_state directory)
npm start
```

### Message Protocol

The listener communicates with the orchestrator using newline-delimited JSON:

**Incoming (to orchestrator):**
```json
{
  "type": "message",
  "chat": "1234567890@s.whatsapp.net",
  "sender": "1234567890@s.whatsapp.net",
  "text": "Hello!",
  "isGroup": false,
  "timestamp": 1699999999,
  "messageId": "ABC123"
}
```

**Outgoing (from orchestrator):**
```json
{
  "type": "send",
  "chat": "1234567890@s.whatsapp.net",
  "text": "Hi there!"
}
```

### Events

- `qr` - QR code for authentication
- `connected` - Successfully connected to WhatsApp
- `disconnected` - Disconnected from WhatsApp
- `message` - New message received

## Requirements

- Node.js 18+
- WhatsApp account

## Related

- [wingman-ai on PyPI](https://pypi.org/project/wingman-ai/) - Main Wingman package
- [Wingman GitHub](https://github.com/metanoia-oss/wingman) - Full documentation

## License

MIT
