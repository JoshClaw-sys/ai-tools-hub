"""Find Quora questions matching our content topics, for community engagement."""
import os
import sys
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent

def find_questions():
    """Use Exa search to find trending Quora questions about AI tools."""
    # Need Exa through Agent Reach
    try:
        result = subprocess.run(
            ["mcporter", "call", "exa.web_search_exa(query: \"site:quora.com best AI tool 2026\", numResults: 10)"],
            capture_output=True, text=True, timeout=30,
            env={**os.environ},
        )
        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error: {result.stderr}"
    except Exception as e:
        return f"Error: {e}"


def main():
    print("🔍 Searching for Quora questions matching our content...")
    print()
    output = find_questions()

    # Save to file
    out_file = ROOT / "quora_leads.md"
    out_file.write_text(f"# Quora Questions to Answer\n\nGenerated: {Path(__file__).name}\n\n```\n{output}\n```\n")

    # Show preview
    print(output[:2000])
    print(f"\n✅ Saved to {out_file}")


if __name__ == "__main__":
    main()
