#!/usr/bin/env python3
"""Run the FixLens scaffold locally (mock provider only).

Usage:  python3 run.py [--port 8000]
Then open http://127.0.0.1:8000/ and upload any photo.
No API key, no network call to any model provider, no spending.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fixlens.app import make_server  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = make_server(args.port)
    print(f"FixLens (mock) at http://127.0.0.1:{args.port}/  — Ctrl-C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
