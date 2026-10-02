#!/bin/bash
# Copies every downloaded Spanish channel into the clean app clone and pushes.
PF=$HOME/Documents/GitHub/phraseFinder/transcripts
APP=$HOME/Documents/GitHub/phrase-finder-app-push
declare -A NAME=( ["Comedy_Central_Latinoamérica"]=ComedyCentralLA ["Caracol_Televisión"]=CaracolTV ["Telemundo_Series"]=TelemundoSeries ["Canal_RCN"]=CanalRCN ["El_Señor_De_Los_Cielos"]=El_Señor_de_los_Cielos )
cd "$APP" || exit 1
total=0
for src in "$PF"/*/; do
	[ -f "$src/video_list.txt" ] || continue
	base=$(basename "$src"); dst=${NAME[$base]:-$base}
	mkdir -p "transcripts/es/$dst"; cp -u "$src"/*.json "transcripts/es/$dst/" 2>/dev/null
	# never bring back transcripts that were removed on purpose
	awk -F"	" -v c="$dst" '$2==c {print $1}' transcripts/es/removed.tsv 2>/dev/null | while read -r id; do rm -f "transcripts/es/$dst/$id.json"; done
	git add "transcripts/es/$dst"
	n=$(git diff --cached --name-only -- "transcripts/es/$dst" | wc -l)
	[ "$n" -eq 0 ] && continue
	git commit -q -m "Add $n Spanish transcripts: ${dst//_/ }" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- "transcripts/es/$dst"
	echo "  $n $dst"; total=$((total + n))
done
[ "$total" -eq 0 ] && { echo "nothing new"; exit 0; }
if git pull -q --rebase && git push -q; then echo "pushed $total"; else git rebase --abort 2>/dev/null; echo "PUSH FAILED ($total committed locally)"; fi
