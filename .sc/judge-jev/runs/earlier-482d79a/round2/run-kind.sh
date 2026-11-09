#!/bin/sh
# usage: run-kind.sh <kind> <attempt> <ids...>
S=/private/tmp/claude-501/-Users-randlee-github-atm-core/2165a35b-650f-4075-81e0-940d0574bbfc/scratchpad
O=/private/tmp/claude-501/-Users-randlee-github-atm-core/2165a35b-650f-4075-81e0-940d0574bbfc/scratchpad/dogfood-0.3.0
R2=/private/tmp/claude-501/-Users-randlee-github-atm-core/2165a35b-650f-4075-81e0-940d0574bbfc/scratchpad/dogfood-0.3.0/round2
kind=$1; n=$2; shift 2
args=""; for id in "$@"; do args="$args --$kind $id"; done
cd $R2/repo && PYTHONDONTWRITEBYTECODE=1 $S/jjpy $O/skill/scripts/jev_judge.py quality $args --index $R2/index.json --run-dir $R2/runs/$kind-$n --run-name dogfood-r2-$kind-$n --repository-root $R2/repo > $R2/$kind-$n.json 2> $R2/$kind-$n.stderr.txt
echo "exit $?" > $R2/$kind-$n.exit
