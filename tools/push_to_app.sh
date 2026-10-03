#!/bin/bash
# Copies every downloaded Spanish or French channel into the clean app clone and pushes.
# A channel's language is in its lang.txt (written by channelSearcher.py); without one it is Spanish.
# A lang.txt that says anything else ("skip") keeps a downloaded channel out of the app.
PF=$HOME/Documents/GitHub/phraseFinder/transcripts
APP=$HOME/Documents/GitHub/phrase-finder-app-push
declare -A NAME=( ["Comedy_Central_Latinoamérica"]=ComedyCentralLA ["Caracol_Televisión"]=CaracolTV ["Telemundo_Series"]=TelemundoSeries ["Canal_RCN"]=CanalRCN ["El_Señor_De_Los_Cielos"]=El_Señor_de_los_Cielos )
NAME+=( ["Golden_Moustache_(M6)"]=Golden_Moustache ["HugoDécrypte_-_Grands_formats"]=HugoDécrypte ["Le_Dessous_des_Cartes_-_ARTE"]=Le_Dessous_des_Cartes ["Restons_Curieux_—_TED-Ed"]=Restons_Curieux_TED-Ed ["Tout_Simplement_–_Kurzgesagt"]=Tout_Simplement_Kurzgesagt ["Un_gars_une_fille__Officiel"]=Un_gars_une_fille ["Un_si_grand_soleil_-_France_Télévisions"]=Un_si_grand_soleil )
NAME+=( ["Bluey_-_Türkçe_Resmi_Kanal"]=Bluey ["Caillou_Türkçe_-_WildBrain"]=Caillou ["MinikaÇOCUK"]=Minika_Çocuk ["Peppa_Pig_Türkçe"]=Peppa_Pig ["Maşa_İle_Koca_Ayı"]=Maşa_ile_Koca_Ayı )
declare -A LANGUAGE=( [es]=Spanish [fr]=French )
cd "$APP" || exit 1
total=0
for src in "$PF"/*/; do
	[ -f "$src/video_list.txt" ] || continue
	lang=es; [ -f "$src/lang.txt" ] && lang=$(tr -d '[:space:]' < "$src/lang.txt")
	[ -n "${LANGUAGE[$lang]}" ] || continue
	base=$(basename "$src"); dst=${NAME[$base]:-$base}
	mkdir -p "transcripts/$lang/$dst"; cp -u "$src"/*.json "transcripts/$lang/$dst/" 2>/dev/null
	# never bring back transcripts that were removed on purpose
	awk -F"	" -v c="$dst" '$2==c {print $1}' "transcripts/$lang/removed.tsv" 2>/dev/null | while read -r id; do rm -f "transcripts/$lang/$dst/$id.json"; done
	git add "transcripts/$lang/$dst"
	n=$(git diff --cached --name-only -- "transcripts/$lang/$dst" | wc -l)
	[ "$n" -eq 0 ] && continue
	git commit -q -m "Add $n ${LANGUAGE[$lang]} transcripts: ${dst//_/ }" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- "transcripts/$lang/$dst"
	echo "  $n $lang $dst"; total=$((total + n))
done
[ "$total" -eq 0 ] && { echo "nothing new"; exit 0; }
if git pull -q --rebase && git push -q; then echo "pushed $total"; else git rebase --abort 2>/dev/null; echo "PUSH FAILED ($total committed locally)"; fi
