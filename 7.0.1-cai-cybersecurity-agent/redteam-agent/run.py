#!/usr/bin/env python3
"""
Simple runner for Red Team Agent - local testing.

Usage:
    python run.py                              # Run with default prompt
    python run.py "Your custom prompt"         # Run with custom prompt
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from redtem_agent import main, main_streamed

if __name__ == "__main__":
    print("=" * 60)
    print("Red Team Agent - Local Runner")
    print("=" * 60)
    print()

    try:
        # Run both normal and streamed modes
        asyncio.run(main())
        print("\n" + "=" * 60)
        asyncio.run(main_streamed())
        print("\n" + "=" * 60)
        print("✓ Red team agent completed successfully!")

    except KeyboardInterrupt:
        print("\n\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
