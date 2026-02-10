# Wingman

[![PyPI version](https://img.shields.io/pypi/v/wingman-ai)](https://pypi.org/project/wingman-ai/)
[![npm version](https://img.shields.io/npm/v/wingman-ai)](https://www.npmjs.com/package/wingman-ai)
[![CI](https://github.com/metanoia-oss/wingman/actions/workflows/ci.yml/badge.svg)](https://github.com/metanoia-oss/wingman/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An AI-powered personal chat agent for WhatsApp and iMessage. Wingman replies to messages on your behalf with a configurable personality, adapts tone based on who you're talking to, and follows policy rules you define.

## Quick Start

```bash
# Install
pip install wingman-ai

# Run setup wizard
wingman init

# Connect WhatsApp (scan QR code)
wingman auth

# Launch interactive console
wingman console
```

That's it. The console gives you full control over the bot.

## Features

- **Personality-driven responses** - Define how your bot talks (witty, formal, casual)
- **Tone adaptation** - Different tones for different people (loving for partner, casual for friends)
- **Policy rules** - Control when to respond (always reply to family, never to work groups)
- **Safety controls** - Rate limiting, cooldowns, quiet hours
- **Conversation memory** - Context-aware responses using message history
- **Interactive console** - Manage everything from a REPL with slash commands
- **Background daemon** - Runs as a service with auto-restart

## The Console

The interactive console is the main way to manage Wingman. Launch it with:

```bash
wingman console
```

You'll get a REPL where you can control the bot, manage contacts, configure policies, and more:

```
Wingman Console v1.1.2

> /help
  Wingman Console v1.1.2

  Help & Navigation
    /help                Show all commands or help for one
    /quit                Exit the console

  Bot Control
    /start               Start the bot
    /stop                Stop the bot
    /restart             Restart the bot
    /status              Show bot status, uptime, transports
    /pause               Temporarily pause bot responses
    /resume              Resume bot after pause
    /logs                View bot activity logs

  Configuration
    /config              View or modify configuration

  Contact Management
    /contacts            Manage contacts

  Group Management
    /groups              Manage groups

  Policy Management
    /policies            Manage response policies

  Messaging
    /send                Send a message via the bot
    /chats               List recent chats
    /history             View chat history

  Stats
    /stats               Overall bot statistics
    /activity            Recent bot activity

  Type /help <command> for details
```

### Getting Help

```bash
# Show all commands
/help

# Show help for a specific command
/help contacts

# Show help for a subcommand
/help contacts add
```

### Managing Contacts

```bash
# List all contacts
/contacts list

# Filter by role
/contacts list --role friend

# Add a contact (interactive mode)
/contacts add

# Add a contact with flags
/contacts add +1234567890@s.whatsapp.net --name John --role friend --tone casual

# Edit a contact
/contacts edit John --tone sarcastic

# Show contact details
/contacts show John

# Remove a contact
/contacts remove John
```

**Roles:** `friend`, `family`, `work`, `unknown`

**Tones:** `loving`, `affectionate`, `friendly`, `casual`, `sarcastic`, `neutral`

### Managing Groups

```bash
# List all groups
/groups list

# Add a group (interactive mode)
/groups add

# Add with flags
/groups add 123456@g.us --name "Family Chat" --category family --policy always

# Edit a group
/groups edit "Family Chat" --policy never

# Remove a group
/groups remove "Family Chat"
```

**Categories:** `family`, `friends`, `work`, `community`, `unknown`

**Policies:** `always`, `selective`, `never`

### Managing Policies

Policies determine when the bot responds. Rules are evaluated in order; first match wins.

```bash
# List all rules
/policies list

# Add a rule
/policies add family_always --condition role=family --action always
/policies add work_never --condition is_group=true,group_category=work --action never

# Remove a rule
/policies remove work_never

# Reorder a rule (move to position 0 = highest priority)
/policies move family_always 0

# Test how a message would be handled
/policies test +1234@s.whatsapp.net --text "hello"

# View/set fallback action
/policies fallback
/policies fallback selective
```

**Actions:** `always` (always respond), `selective` (only when mentioned), `never` (ignore)

### Bot Control

```bash
# Start the bot
/start

# Start in foreground (see output directly)
/start --foreground

# Stop the bot
/stop

# Check status
/status

# Pause for 30 minutes
/pause 30m

# Pause for 2 hours
/pause 2h

# Resume
/resume

# View logs
/logs
/logs -n 100
/logs --follow
```

### Sending Messages

```bash
# Send a message
/send John Hey, what's up?

# Send using JID
/send +1234567890@s.whatsapp.net Hello!
```

### Viewing History

```bash
# List recent chats
/chats

# View chat history
/history John
/history John -n 50
```

### Configuration

```bash
# Show all config
/config show

# Show a section
/config show openai

# Set a value
/config set openai.model gpt-4-turbo
/config set safety.rate_limit 20

# Open in editor
/config edit

# Force reload
/config reload
```

## CLI Commands

For quick operations outside the console:

| Command | Description |
|---------|-------------|
| `wingman init` | Interactive setup wizard |
| `wingman auth` | Connect WhatsApp (scan QR code) |
| `wingman console` | Launch interactive console |
| `wingman start` | Start bot as background daemon |
| `wingman start -f` | Start bot in foreground |
| `wingman stop` | Stop running bot |
| `wingman status` | Check if running |
| `wingman logs` | View activity logs |
| `wingman config` | View configuration |
| `wingman uninstall` | Remove Wingman and all data |

## Configuration Files

After running `wingman init`, config files are stored in:

```
~/.config/wingman/
├── config.yaml           # Main configuration (API keys, model, personality)
├── contacts.yaml         # Contact profiles (name, role, tone)
├── groups.yaml           # Group settings (category, reply policy)
└── policies.yaml         # Response rules

~/.local/share/wingman/
├── conversations.db      # Message history (SQLite)
└── auth_state/           # WhatsApp credentials

~/.cache/wingman/
└── logs/                 # Log files
```

### Main Config (`config.yaml`)

```yaml
bot:
  name: "Wingman"

openai:
  api_key: "sk-..."
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

### Contacts (`contacts.yaml`)

```yaml
contacts:
  "+14155551234@s.whatsapp.net":
    name: "Alex"
    role: friend
    tone: casual
    cooldown_override: 30

defaults:
  role: unknown
  tone: neutral
```

### Groups (`groups.yaml`)

```yaml
groups:
  "120363012345678901@g.us":
    name: "Family Chat"
    category: family
    reply_policy: always

defaults:
  category: unknown
  reply_policy: selective
```

### Policies (`policies.yaml`)

```yaml
rules:
  - name: "family_dm"
    conditions:
      is_dm: true
      role: family
    action: always

  - name: "work_group"
    conditions:
      is_group: true
      group_category: work
    action: never

fallback:
  action: selective
```

## Finding JIDs

JIDs (Jabber IDs) identify contacts and groups. To find them:

1. Send a message to the contact/group
2. Check the logs: `wingman logs`
3. Look for: `chat=+14155551234@s.whatsapp.net`

Or use the console:
```bash
/chats          # Lists recent chats with JIDs
/contacts list  # Shows configured contacts with JIDs
/groups list    # Shows configured groups with JIDs
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    WhatsApp Web                          │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│           Node.js Listener (Baileys)                     │
│  - Connects to WhatsApp Web via WebSocket                │
│  - Handles QR auth, message receive/send                 │
└────────────────────────┬────────────────────────────────┘
                         │ IPC (stdin/stdout JSON)
┌────────────────────────▼────────────────────────────────┐
│              Python Agent                                │
│  - Policy evaluation (should we respond?)                │
│  - Contact/group resolution                              │
│  - Tone adaptation based on relationship                 │
│  - OpenAI GPT integration                                │
│  - Conversation memory (SQLite)                          │
│  - Safety controls (rate limits, quiet hours)            │
└─────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Bot Not Responding

```bash
# Check if running
wingman status

# Check logs for errors
wingman logs --error

# Verify config
wingman console
/config show
```

### WhatsApp Disconnected

WhatsApp may disconnect linked devices. Re-authenticate:

```bash
wingman stop
wingman auth
wingman start
```

### QR Code Won't Scan

- Ensure terminal is large enough
- Try reducing font size
- Good lighting helps

## Prerequisites

- **macOS** (tested) or Linux
- **Python 3.10+**
- **Node.js 20+**
- **OpenAI API key**

## Development

```bash
git clone https://github.com/metanoia-oss/wingman.git
cd wingman
pip install -e .
wingman init
```

Run tests:
```bash
PYTHONPATH=src pytest tests/ -q
```

## Uninstalling

```bash
wingman uninstall
pip uninstall wingman-ai
```

## License

MIT License - see [LICENSE](LICENSE)

## Acknowledgments

- [Baileys](https://github.com/WhiskeySockets/Baileys) - WhatsApp Web API
- [OpenAI](https://openai.com/) - GPT models
