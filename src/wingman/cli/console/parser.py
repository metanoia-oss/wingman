"""Command parser for the interactive console."""

from dataclasses import dataclass, field


@dataclass
class ParsedCommand:
    """Result of parsing a slash command."""

    command: str  # e.g., "config"
    subcommand: str | None = None  # e.g., "show"
    args: list[str] = field(default_factory=list)  # positional args
    flags: dict[str, str | bool] = field(default_factory=dict)  # --key value or --flag


def parse_input(raw: str) -> ParsedCommand | None:
    """
    Parse a slash command string into a ParsedCommand.

    Supports:
        /command
        /command subcommand
        /command subcommand arg1 arg2
        /command subcommand --flag value --bool-flag
        /command subcommand arg1 --flag value

    Quoted strings are handled for arguments with spaces.

    Returns None if input is empty or not a slash command.
    """
    raw = raw.strip()
    if not raw or not raw.startswith("/"):
        return None

    tokens = _tokenize(raw[1:])  # strip leading /
    if not tokens:
        return None

    command = tokens[0].lower()
    tokens = tokens[1:]

    subcommand = None
    args: list[str] = []
    flags: dict[str, str | bool] = {}

    i = 0

    # Check if first remaining token is a subcommand (not a flag, not quoted)
    if tokens and not tokens[0].startswith("-"):
        subcommand = tokens[0].lower()
        i = 1

    while i < len(tokens):
        token = tokens[i]
        if token.startswith("--"):
            key = token[2:]
            # Check if next token is a value (not another flag)
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                flags[key] = tokens[i + 1]
                i += 2
            else:
                flags[key] = True
                i += 1
        elif token.startswith("-") and len(token) == 2:
            key = token[1:]
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                flags[key] = tokens[i + 1]
                i += 2
            else:
                flags[key] = True
                i += 1
        else:
            args.append(token)
            i += 1

    return ParsedCommand(command=command, subcommand=subcommand, args=args, flags=flags)


def _tokenize(text: str) -> list[str]:
    """Split text into tokens, respecting quoted strings."""
    tokens: list[str] = []
    current: list[str] = []
    in_quote: str | None = None

    for char in text:
        if in_quote:
            if char == in_quote:
                in_quote = None
            else:
                current.append(char)
        elif char in ('"', "'"):
            in_quote = char
        elif char == " ":
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(char)

    if current:
        tokens.append("".join(current))

    return tokens
