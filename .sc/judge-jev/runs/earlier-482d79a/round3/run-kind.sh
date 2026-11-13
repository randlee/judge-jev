#!/bin/sh
# usage: run-kind.sh <kind> <tag> <index> <ids...>
S=/private/tmp/claude-501/-Users-randlee-github-atm-core/2165a35b-650f-4075-81e0-940d0574bbfc/scratchpad
O=$S/dogfood-0.3.0
R3=$O/round3
kind=$1; n=$2; idx=$3; shift 3
args=""; for id in "$@"; do args="$args --$kind $id"; done
cd $R3/repo && PYTHONDONTWRITEBYTECODE=1 $S/jjpy $O/skill/scripts/jev_judge.py quality $args --index $idx --run-dir $R3/runs/$kind-$n --run-name dogfood-r3-$kind-$n --repository-root $R3/repo > $R3/$kind-$n.json 2> $R3/$kind-$n.stderr.txt
echo "exit $?" > $R3/$kind-$n.exit
