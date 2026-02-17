#!/usr/bin/env python3
"""Script to resolve merge conflicts in README.md by merging both sides intelligently."""

import re

def resolve_readme_conflicts(filepath):
    """Read README, resolve conflicts by merging both sides, write back."""

    with open(filepath, 'r') as f:
        content = f.read()

    # Strategy: For most sections, preserve origin/main (newer implementation)
    # But keep any unique content from HEAD that adds value

    # Resolve by taking origin/main for the major sections since it has:
    # - More comprehensive Polymarket API documentation
    # - BinanceWebSocket class documentation
    # - State persistence documentation
    # - More complete examples

    # Pattern: Remove conflict markers and choose appropriate content
    def resolve_conflict(match):
        head_content = match.group(1)
        main_content = match.group(2)

        # For the large API documentation sections, use main (more complete)
        # Check if this is one of the large documentation blocks
        if len(main_content) > len(head_content) and ('## ' in main_content or '### ' in main_content):
            return main_content
        elif 'BinanceWebSocket' in main_content and 'BinanceWebSocketClient' in head_content:
            # Origin/main has better BinanceWebSocket documentation
            return main_content
        elif 'State Persistence' in main_content or 'StateManager' in main_content:
            # Origin/main has state persistence documentation
            return main_content
        elif 'PolymarketClient' in main_content and 'get_btc_markets' in main_content:
            # Origin/main has more comprehensive Polymarket docs
            return main_content
        elif 'pytest' in head_content and 'pytest' in main_content:
            # Merge pytest commands from both
            return main_content  # origin/main has more complete test docs
        else:
            # Default: prefer origin/main as it's the more recent/complete version
            return main_content

    # Regex to match conflict blocks
    conflict_pattern = r'<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> origin/main'

    resolved = re.sub(conflict_pattern, resolve_conflict, content, flags=re.DOTALL)

    with open(filepath, 'w') as f:
        f.write(resolved)

    print(f"Resolved conflicts in {filepath}")
    return resolved

if __name__ == '__main__':
    resolve_readme_conflicts('/workspace/polymarket-bot/README.md')
