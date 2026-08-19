"""Patch builder/agent.py in place on VPS to sanitize unbalanced tags before failing."""
import re

VPATH = r"\opt\fralib\backend\agents\builder\agent.py"

# We'll read from stdin and write to stdout, then scp back.
# But simpler: use Edit tool on local, then transfer.
print("Use Edit tool on local copy, then transfer via cat|ssh")
