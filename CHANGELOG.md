# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-01-XX

### Added

- Initial public release
- CLI commands: `init`, `auth`, `start`, `stop`, `status`, `logs`, `config`, `uninstall`
- Interactive setup wizard with prerequisite checking
- WhatsApp transport via Baileys
- Background daemon with auto-restart (macOS launchd)
- OpenAI GPT integration for AI responses
- Personality-driven responses with configurable tone
- Role-based tone adaptation (partner, family, friends, colleagues)
- Policy-driven response rules
- Safety controls: rate limiting, cooldowns, quiet hours
- Conversation memory with SQLite storage
- Hot-reload configuration (contacts, groups, policies)
- XDG-compliant config and data directories

### Security

- API keys stored in user config directory with restricted permissions
- WhatsApp credentials stored in local data directory
- No sensitive data in logs

[Unreleased]: https://github.com/metanoia-oss/wingman/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/metanoia-oss/wingman/releases/tag/v1.0.0
