# Wingman

[![PyPI version](https://img.shields.io/pypi/v/wingman-ai)](https://pypi.org/project/wingman-ai/)
[![npm version](https://img.shields.io/npm/v/wingman-ai)](https://www.npmjs.com/package/wingman-ai)
[![CI](https://github.com/metanoia-oss/wingman/actions/workflows/ci.yml/badge.svg)](https://github.com/metanoia-oss/wingman/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

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

### Quick Install (Recommended)

```bash
pip install wingman-ai
```

Then run the interactive setup:

```bash
wingman init
```

The setup wizard will:
1. Check prerequisites (Python, Node.js, npm)
2. Configure your OpenAI API key
3. Set up bot personality and name
4. Configure safety settings
5. Install the WhatsApp listener

### Development Install

```bash
git clone https://github.com/metanoia-oss/wingman.git
cd wingman
pip install -e .
wingman init
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `wingman init` | Interactive setup wizard |
| `wingman auth` | Connect WhatsApp (scan QR code) |
| `wingman start` | Start bot as background daemon |
| `wingman start -f` | Start bot in foreground |
| `wingman stop` | Stop running bot |
| `wingman status` | Check if running |
| `wingman logs` | View/stream activity logs |
| `wingman config` | View or edit configuration |
| `wingman uninstall` | Remove Wingman and all data |

## Quick Start

```bash
# 1. Install
pip install wingman-ai

# 2. Run setup wizard
wingman init

# 3. Connect WhatsApp
wingman auth

# 4. Start the bot
wingman start

# 5. Check status
wingman status

# 6. View logs
wingman logs
```

## Running the Bot

### First Run: WhatsApp Authentication

After setup, connect WhatsApp by scanning a QR code:

```bash
wingman auth
```

1. A QR code will appear in the terminal
2. Open WhatsApp on your phone
3. Go to **Settings > Linked Devices > Link a Device**
4. Scan the QR code
5. Wait for "Connected!" message

### Start as Background Service

```bash
wingman start
```

This starts Wingman as a macOS launchd service that auto-restarts on crash.

### Run in Foreground

```bash
wingman start --foreground
```

Press `Ctrl+C` to stop.

### View Logs

```bash
# Stream logs in real-time
wingman logs

# Show last 100 lines without streaming
wingman logs --no-follow -n 100

# Show error logs
wingman logs --error
```

---

## Legacy Installation (Manual)

<details>
<summary>Click to expand manual installation steps</summary>

### Step 1: Clone the Repository

```bash
git clone https://github.com/metanoia-oss/wingman.git
cd wingman
```

### Step 2: Set Up Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
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
cp .env.example .env
nano .env  # Add your OPENAI_API_KEY
```

### Step 5: Configure Contacts & Policies

```bash
cp config/contacts.yaml.example config/contacts.yaml
cp config/groups.yaml.example config/groups.yaml
cp config/policies.yaml.example config/policies.yaml
```

### Run with Legacy Script

```bash
python run.py
```

</details>

## Configuration

### Config File (`~/.config/wingman/config.yaml`)

```yaml
bot:
  name: "Wingman"

openai:
  api_key: "sk-..."  # Or use OPENAI_API_KEY env var
  model: "gpt-4o"
  max_response_tokens: 150
  temperature: 0.8

personality:
  base_prompt: "You are Wingman, a witty and helpful assistant."
  default_tone: casual

safety:
  max_replies_per_hour: 30
  cooldown_seconds: 60
  quiet_hours:
    enabled: true
    start: 0
    end: 6
```

### Environment Variables (Legacy)

These are still supported for backward compatibility:

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
├── pyproject.toml            # Package configuration
├── README.md                 # This file
├── LICENSE                   # MIT License
│
├── src/wingman/              # Main Python package
│   ├── cli/                  # CLI commands (typer)
│   │   ├── main.py           # CLI entry point
│   │   ├── wizard.py         # Setup wizard
│   │   └── commands/         # Individual commands
│   ├── config/               # Configuration
│   │   ├── paths.py          # XDG path management
│   │   ├── settings.py       # Settings loader
│   │   ├── registry.py       # Contact/Group registries
│   │   └── personality.py    # Bot personality prompts
│   ├── core/                 # Core bot logic
│   │   ├── agent.py          # Main agent class
│   │   ├── process_manager.py # Node.js subprocess
│   │   ├── message_processor.py # Message handling
│   │   ├── llm/              # OpenAI integration
│   │   ├── memory/           # SQLite conversation storage
│   │   ├── safety/           # Rate limits, quiet hours
│   │   ├── policy/           # Policy evaluation
│   │   └── transports/       # WhatsApp & iMessage
│   ├── daemon/               # Background service management
│   └── installer/            # Node.js listener installer
│
├── node_listener/            # WhatsApp Web connection
│   ├── src/                  # TypeScript source
│   ├── package.json
│   └── tsconfig.json
│
└── config/                   # Example configs (legacy)
    ├── contacts.yaml.example
    ├── groups.yaml.example
    └── policies.yaml.example
```

### User Config Locations (XDG)

After running `wingman init`, config files are stored in:

```
~/.config/wingman/
├── config.yaml           # Main configuration
├── contacts.yaml         # Contact profiles
├── groups.yaml           # Group settings
├── policies.yaml         # Response policies
└── node_listener/        # Installed Node.js listener

~/.local/share/wingman/
├── conversations.db      # SQLite database
└── auth_state/           # WhatsApp credentials

~/.cache/wingman/
└── logs/                 # Log files
```

## Troubleshooting

### QR Code Won't Scan

- Make sure terminal is large enough to display the QR code
- Try reducing terminal font size
- Ensure good lighting when scanning

### Bot Not Responding

1. Check if daemon is running:
   ```bash
   wingman status
   ```

2. Check logs for errors:
   ```bash
   wingman logs --error
   ```

3. Verify OpenAI API key is valid:
   ```bash
   wingman config --show
   ```

4. Check policy rules - the contact may be set to `never` respond

### "WhatsApp Logged Out" Error

WhatsApp may log out linked devices periodically. Re-authenticate:

```bash
wingman stop
wingman auth
wingman start
```

### Config Changes Not Working

Config files auto-reload every 2 seconds. If changes aren't applying:
1. Check for YAML syntax errors:
   ```bash
   wingman config --show
   ```
2. Check the logs for reload messages:
   ```bash
   wingman logs

## Important Notes

- **Mac must stay logged in** - The daemon runs as a user agent. It won't run when logged out.
- **Screen lock is OK** - The bot continues running when the screen is locked.
- **Auto-restart** - If the bot crashes, launchd will automatically restart it.
- **Rate limiting** - Built-in rate limits prevent spam. Configure in `.env`.

## Uninstalling

To completely remove Wingman:

```bash
# Remove all Wingman data, config, and daemon
wingman uninstall

# Then remove the package
pip uninstall wingman-ai
```

Options:
- `wingman uninstall --keep-config` - Keep config files, only remove data
- `wingman uninstall --force` - Don't ask for confirmation

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Baileys](https://github.com/WhiskeySockets/Baileys) - WhatsApp Web API
- [OpenAI](https://openai.com/) - GPT models
