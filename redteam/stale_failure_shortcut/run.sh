#!/bin/bash
set -euo pipefail
cd /home/user
python -m redteam.audit case stale_failure_shortcut
