#!/bin/bash
set -euo pipefail
cd /home/user
python -m redteam.audit case omit_hard_shortcut
