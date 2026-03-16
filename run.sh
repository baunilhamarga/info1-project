#!/usr/bin/env bash
set -euo pipefail

for i in 1 2 3 4 5 6; do
  python main.py "examples/${i}.imp" --k 5 > "examples/${i}.out"
done