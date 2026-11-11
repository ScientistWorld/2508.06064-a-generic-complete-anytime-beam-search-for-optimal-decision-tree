#!/bin/bash
set -euo pipefail
cd /home/user
python -m redteam.audit case null_error_shortcut
