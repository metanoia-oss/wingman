#!/usr/bin/env python3
"""
WhatsApp Personal Agent - Entry Point

Usage:
    python run.py

Prerequisites:
    1. Copy .env.example to .env and add your OPENAI_API_KEY
    2. Build Node.js listener: cd node_listener && npm install && npm run build
    3. Install Python deps: pip install -r requirements.txt
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    """Run the WhatsApp agent."""
    import asyncio
    from python_orchestrator.main import main as agent_main

    try:
        asyncio.run(agent_main())
    except KeyboardInterrupt:
        print("\nShutdown requested. Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
