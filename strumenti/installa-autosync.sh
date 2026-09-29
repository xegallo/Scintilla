#!/bin/sh
# Installa la sincronizzazione automatica del libro (da eseguire una sola volta).
set -e
LIBRO="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/libro-autosync.service" <<EOF
[Unit]
Description=Sincronizzazione automatica del libro
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
systemctl --user enable --now libro-autosync.service
# salva in Git i nuovi strumenti
cd "$LIBRO"
git add strumenti .gitignore .gitattributes LEGGIMI.md
git diff --cached --quiet || { git commit -q -m "Sincronizzazione automatica"; git push -q; }
sleep 2
systemctl --user --no-pager status libro-autosync.service | head -5
echo
echo "Fatto. Da ora il libro si sincronizza da solo."
