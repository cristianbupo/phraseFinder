#!/bin/bash
# Round of parallel downloads. usage: download_round.sh <pause "a,b"> <max per lane> <handle or handle=i/n> ...
# Speed test stage: runs several channels at the same time and reports the pace.
# usage: stage.sh <pause "a,b"> <max per lane> <handle> [handle...]
PF=$HOME/Documents/GitHub/phraseFinder
export PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
export CS_PAUSE=$1; max=$2; shift 2
cd "$PF" || exit 1
count() { find transcripts -name '*.json' -newer "$TEMP/stage_start" 2>/dev/null | wc -l; }
touch "$TEMP/stage_start"; t0=$(date +%s)
echo "[$(date +%H:%M:%S)] stage: $# lanes, pause $CS_PAUSE, up to $max each: $*"
pids=()
for h in "$@"; do
	hh=${h%%=*}; pp=""; [ "$h" != "$hh" ] && pp="--part ${h##*=}"; .venv/Scripts/python channelSearcher.py --lang es --max "$max" $pp "https://www.youtube.com/@$hh" > "$TEMP/cs_${h////-}.log" 2>&1 &
	pids+=($!)
done
# a line every minute, so the pace is visible while it runs
while :; do
	alive=0; for p in "${pids[@]}"; do kill -0 "$p" 2>/dev/null && alive=$((alive+1)); done
	[ "$alive" -eq 0 ] && break
	for i in $(seq 12); do ping -n 6 127.0.0.1 > /dev/null; alive=0; for p in "${pids[@]}"; do kill -0 "$p" 2>/dev/null && alive=$((alive+1)); done; [ "$alive" -eq 0 ] && break; done
	el=$(( $(date +%s) - t0 )); n=$(count)
	echo "[$(date +%H:%M:%S)] ${el}s: $n saved, $(( n * 60 / (el > 0 ? el : 1) ))/min, $alive lanes running"
done
blocked=0
for h in "$@"; do
	last=$(tr '\r' '\n' < "$TEMP/cs_${h////-}.log" | grep -a -E "Total new saved|Total failed|blocking|stopped answering|^   -" | cut -c1-110 | tr '\n' ' ')
	echo "  $h: $last"
	grep -a -q -E "blocking this computer|stopped answering" "$TEMP/cs_${h////-}.log" && blocked=1
done
el=$(( $(date +%s) - t0 )); n=$(count)
echo "[$(date +%H:%M:%S)] STAGE RESULT: $n saved in ${el}s = $(( n * 60 / (el > 0 ? el : 1) ))/min; blocked=$blocked"
exit $((blocked * 2))
