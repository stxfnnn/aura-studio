#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
python3 -m venv "$project_dir/.venv"
"$project_dir/.venv/bin/pip" install -e "$project_dir"
mkdir -p "$HOME/.local/share/applications"
mkdir -p "$HOME/.local/share/icons/hicolor/scalable/apps"
install -m 644 "$project_dir/src/aura_studio/assets/aura-studio.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/aura-studio.svg"
cat > "$HOME/.local/share/applications/aura-studio.desktop" <<EOF
[Desktop Entry]
Name=Aura Studio
Comment=RGB and OLED control for ASUS ROG devices
Exec=$project_dir/.venv/bin/aura-studio
Icon=aura-studio
Terminal=false
Type=Application
Categories=Settings;HardwareSettings;
StartupNotify=true
EOF
chmod 644 "$HOME/.local/share/applications/aura-studio.desktop"
echo "Aura Studio is installed for your user. Start it with: $project_dir/.venv/bin/aura-studio"
