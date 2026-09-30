#!/bin/sh
# Installa la sincronizzazione automatica del libro (da eseguire una sola volta per progetto).
# Il nome del servizio include il nome della cartella, cosi' piu' libri sullo stesso PC
# possono sincronizzarsi in automatico in parallelo senza sovrascriversi a vicenda.
set -e
LIBRO="$(cd "$(dirname "$0")/.." && pwd)"
NOME="$(basename "$LIBRO" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9' '-' | sed 's/^-*//;s/-*$//')"
SERVIZIO="libro-autosync-$NOME.service"
mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/$SERVIZIO" <<EOF
[Unit]
Description=Sincronizzazione automatica del libro ($NOME)
After=graphical-session.target network-online.target

[Service]
ExecStart=/usr/bin/python3 $LIBRO/strumenti/autosync.py
WorkingDirectory=$LIBRO
Environment=PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin
Restart=always
RestartSec=30

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now "$SERVIZIO"
# salva in Git i nuovi strumenti (solo i file che esistono in questo repo)
cd "$LIBRO"
for f in strumenti .gitignore .gitattributes LEGGIMI.md; do
    [ -e "$f" ] && git add "$f"
done
git diff --cached --quiet || { git commit -q -m "Sincronizzazione automatica"; git push -q; }
sleep 2
systemctl --user --no-pager status "$SERVIZIO" | head -5
echo
echo "Fatto. Da ora il libro ($NOME) si sincronizza da solo (servizio $SERVIZIO)."
