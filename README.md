# Wingman

An AI-powered personal chat agent that participates in conversations with configurable personality, tone adaptation based on contact relationships, and policy-driven response rules. Supports multiple platforms including WhatsApp and iMessage (with more coming). Built with OpenAI GPT models.

## Features

- **Personality-driven responses** - Configurable bot personality with witty, casual tone
- **Role-based tone adaptation** - Different tones for different relationships (partner, family, friends)
- **Policy-driven rules** - Fine-grained control over when to respond
- **Safety controls** - Rate limiting, cooldowns, quiet hours
- **Conversation memory** - Context-aware responses using message history
- **Hot-reload config** - Changes to contacts/groups apply without restart
- **Background daemon** - Runs as a macOS service with auto-restart

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      WhatsApp Web                           │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              Node.js Listener (Baileys)                     │
│              node_listener/                                 │
│  - Connects to WhatsApp Web                                 │
│  - Receives messages via WebSocket                          │
│  - Sends messages back                                      │
└─────────────────────────┬───────────────────────────────────┘
                          │ IPC (stdin/stdout)
┌─────────────────────────▼───────────────────────────────────┐
│              Python Orchestrator                            │
│              python_orchestrator/                           │
│  - Message processing & filtering                           │
│  - Config-driven identity (contacts.yaml, groups.yaml)      │
│  - Policy-based response rules (policies.yaml)              │
│  - Role-based tone adaptation                               │
│  - OpenAI GPT integration                                   │
│  - Conversation memory (SQLite)                             │
│  - Safety controls (rate limits, quiet hours, cooldowns)    │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

- **macOS** (tested on macOS, may work on Linux with modifications)
- **Python 3.10+**
- **Node.js 18+**
- **WhatsApp account** (on your phone)
- **OpenAI API key**

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/wingman.git
cd wingman
```

### Step 2: Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Build Node.js Listener

```bash
cd node_listener
npm install
npm run build
cd ..
```

### Step 4: Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit with your settings
nano .env  # or use any editor
```

**Required settings in `.env`:**

```env
# Required
OPENAI_API_KEY=sk-your-actual-api-key-here

# Optional (defaults shown)
OPENAI_MODEL=gpt-4o
BOT_NAME=Maximus
MAX_REPLIES_PER_HOUR=30
DEFAULT_COOLDOWN_SECONDS=60
QUIET_HOURS_START=0
QUIET_HOURS_END=6
CONTEXT_WINDOW_SIZE=30
MAX_RESPONSE_TOKENS=150
TEMPERATURE=0.8
```

### Step 5: Configure Contacts & Policies

```bash
# Copy example configs
cp config/contacts.yaml.example config/contacts.yaml
cp config/groups.yaml.example config/groups.yaml
cp config/policies.yaml.example config/policies.yaml

# Edit with your actual contact/group JIDs
nano config/contacts.yaml
nano config/groups.yaml
```

## Running the Bot

### First Run: WhatsApp Authentication

The first time you run the bot, you need to scan a QR code to link WhatsApp:

```bash
# Make sure venv is activated
source .venv/bin/activate

# Run interactively
python run.py
```

1. A QR code will appear in the terminal
2. Open WhatsApp on your phone
3. Go to **Settings > Linked Devices > Link a Device**
4. Scan the QR code
5. Wait for "WhatsApp connected" message
6. Test by sending a message to a group
7. Press `Ctrl+C` to stop

This creates authentication credentials in `auth_state/`.

### Manual Run (Foreground)

```bash
source .venv/bin/activate
python run.py
```

Press `Ctrl+C` to stop.

### Background Daemon (macOS)

Run the bot as a background service that auto-starts and auto-restarts.

```bash
# Install and start the daemon
./scripts/daemon.sh install
./scripts/daemon.sh start

# Check status
./scripts/daemon.sh status

# View logs
./scripts/daemon.sh logs

# Stop the daemon
./scripts/daemon.sh stop
```

#### Daemon Commands

| Command | Description |
|---------|-------------|
| `./scripts/daemon.sh start` | Start the daemon |
| `./scripts/daemon.sh stop` | Stop the daemon |
| `./scripts/daemon.sh restart` | Restart the daemon |
| `./scripts/daemon.sh status` | Check if running |
| `./scripts/daemon.sh logs` | Tail stdout log |
| `./scripts/daemon.sh logs-err` | Tail stderr log |
| `./scripts/daemon.sh interactive` | Run for QR scanning |
| `./scripts/daemon.sh uninstall` | Remove daemon completely |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (required) | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o` | Model to use (gpt-4o, gpt-4-turbo, gpt-3.5-turbo) |
| `BOT_NAME` | `Maximus` | Name the bot responds to |
| `MAX_REPLIES_PER_HOUR` | `30` | Rate limit for replies |
| `DEFAULT_COOLDOWN_SECONDS` | `60` | Minimum seconds between replies |
| `QUIET_HOURS_START` | `0` | Hour to start quiet mode (0-23) |
| `QUIET_HOURS_END` | `6` | Hour to end quiet mode (0-23) |
| `CONTEXT_WINDOW_SIZE` | `30` | Number of messages to include as context |
| `MAX_RESPONSE_TOKENS` | `150` | Maximum response length |
| `TEMPERATURE` | `0.8` | Creativity (0.0-1.0) |

### Contact Configuration (`config/contacts.yaml`)

Maps WhatsApp JIDs to contact profiles with roles and tone preferences.

```yaml
contacts:
  "+14155551234@s.whatsapp.net":
    name: "Partner"
    role: girlfriend      # girlfriend, sister, friend, family, colleague, unknown
    tone: affectionate    # loving, affectionate, friendly, casual, sarcastic, neutral
    allow_proactive: true
    cooldown_override: 30 # Custom cooldown (seconds)

defaults:
  role: unknown
  tone: neutral
  allow_proactive: false
```

**Available Tones:**

| Tone | Behavior |
|------|----------|
| `loving` | Deep affection and intimacy (for partners) |
| `affectionate` | Warm, caring, supportive |
| `friendly` | Playful teasing, sibling vibes |
| `casual` | Relaxed friend energy |
| `sarcastic` | Witty banter, dry humor |
| `neutral` | Polite, maintains boundaries |

### Group Configuration (`config/groups.yaml`)

Maps group JIDs to categories and reply policies.

```yaml
groups:
  "120363012345678901@g.us":
    name: "Family Chat"
    category: family    # family, friends, work, unknown
    reply_policy: always  # always, selective, never

defaults:
  category: unknown
  reply_policy: selective
```

**Reply Policies:**

| Policy | Behavior |
|--------|----------|
| `always` | Always respond to messages |
| `selective` | Only respond when @mentioned or replying to bot |
| `never` | Never respond in this chat |

### Policy Rules (`config/policies.yaml`)

Rules for determining when to respond. Evaluated in order; first match wins.

```yaml
rules:
  - name: "girlfriend_dm"
    conditions:
      is_dm: true
      role: girlfriend
    action: always

  - name: "unknown_dm"
    conditions:
      is_dm: true
      role: unknown
    action: never

  - name: "work_group"
    conditions:
      is_group: true
      group_category: work
    action: never

fallback:
  action: selective
```

**Available Conditions:**
- `is_dm: true/false` - Is this a direct message?
- `is_group: true/false` - Is this a group chat?
- `role: girlfriend/sister/friend/...` - Contact's role
- `group_category: family/friends/work/...` - Group's category
- `is_reply_to_bot: true/false` - Is this a reply to bot's message?

### Finding JIDs

To find contact and group JIDs:

1. Send a message to the contact/group
2. Check the logs:
   ```bash
   ./scripts/daemon.sh logs
   ```
3. Look for log entries like:
   ```
   Processing message: chat=+14155551234@s.whatsapp.net...
   Resolved: contact=Unknown (role=unknown, tone=neutral)
   ```

The `chat=` value is the JID you need.

## Project Structure

```
wingman/
├── run.py                    # Entry point
├── .env.example              # Example configuration
├── requirements.txt          # Python dependencies
├── LICENSE                   # MIT License
├── CONTRIBUTING.md           # Contribution guidelines
│
├── node_listener/            # WhatsApp Web connection
│   ├── src/                  # TypeScript source
│   └── package.json
│
├── python_orchestrator/      # Main bot logic
│   ├── main.py               # Orchestrator entry point
│   ├── ipc_handler.py        # Communication with Node.js
│   ├── message_processor.py  # Message handling
│   ├── process_manager.py    # Node.js process management
│   ├── llm/                  # OpenAI integration
│   ├── memory/               # Conversation storage (SQLite)
│   ├── safety/               # Rate limits, quiet hours
│   └── policy/               # Policy evaluation engine
│
├── config/                   # Configuration
│   ├── settings.py           # Environment settings
│   ├── personality.py        # Bot personality
│   ├── registry.py           # Contact/Group registries
│   ├── contacts.yaml.example # Example contacts config
│   ├── groups.yaml.example   # Example groups config
│   └── policies.yaml.example # Example policies config
│
├── scripts/
│   └── daemon.sh             # Daemon management script
│
├── auth_state/               # WhatsApp credentials (gitignored)
├── data/                     # SQLite database (gitignored)
└── logs/                     # Log files (gitignored)
```

## Troubleshooting

### QR Code Won't Scan

- Make sure terminal is large enough to display the QR code
- Try reducing terminal font size
- Ensure good lighting when scanning

### Bot Not Responding

1. Check if daemon is running:
   ```bash
   ./scripts/daemon.sh status
   ```

2. Check logs for errors:
   ```bash
   ./scripts/daemon.sh logs-err
   ```

3. Verify OpenAI API key is valid in `.env`

4. Check policy rules - the contact may be set to `never` respond

### "WhatsApp Logged Out" Error

WhatsApp may log out linked devices periodically. Re-authenticate:

```bash
./scripts/daemon.sh stop
./scripts/daemon.sh interactive
# Scan QR code again
# Ctrl+C after connected
./scripts/daemon.sh start
```

### Config Changes Not Working

Config files auto-reload every 2 seconds. If changes aren't applying:
1. Check for YAML syntax errors in your config files
2. Check the logs for reload messages

## Important Notes

- **Mac must stay logged in** - The daemon runs as a user agent. It won't run when logged out.
- **Screen lock is OK** - The bot continues running when the screen is locked.
- **Auto-restart** - If the bot crashes, launchd will automatically restart it.
- **Rate limiting** - Built-in rate limits prevent spam. Configure in `.env`.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Baileys](https://github.com/WhiskeySockets/Baileys) - WhatsApp Web API
- [OpenAI](https://openai.com/) - GPT models
