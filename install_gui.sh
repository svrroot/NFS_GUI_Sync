#!/bin/bash
"""
NFS Sync Manager - Installer Script
Installs dependencies, creates desktop entry, and sets up the application
"""

set -e  # Exit on error

echo "🚀 NFS Sync Manager - Installer"
echo "================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${YELLOW}📦 Schritt 1: Prüfe System-Abhängigkeiten...${NC}"

# Check if running on Arch Linux
if ! command -v pacman &> /dev/null; then
    echo -e "${RED}❌ Fehler: Dieses Script ist für Arch Linux gedacht${NC}"
    exit 1
fi

echo "✅ Arch Linux erkannt"

# Check and install dependencies
DEPENDENCIES=(
    "python"
    "python-gobject"
    "gtk4"
    "libadwaita"
    "rsync"
    "nfs-utils"
)

MISSING_DEPS=()

for dep in "${DEPENDENCIES[@]}"; do
    if ! pacman -Qi "$dep" &> /dev/null; then
        MISSING_DEPS+=("$dep")
    fi
done

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo -e "${YELLOW}📥 Installiere fehlende Abhängigkeiten: ${MISSING_DEPS[*]}${NC}"
    sudo pacman -S --needed --noconfirm "${MISSING_DEPS[@]}"
else
    echo "✅ Alle Abhängigkeiten bereits installiert"
fi

echo ""
echo -e "${YELLOW}📝 Schritt 2: Erstelle Desktop Entry...${NC}"

# Create .desktop file
DESKTOP_FILE="$HOME/.local/share/applications/nfs-sync-manager.desktop"
mkdir -p "$HOME/.local/share/applications"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=NFS Sync Manager
Comment=Manage NFS shares and sync operations
Exec=$SCRIPT_DIR/nfs_sync_gui.py
Icon=folder-sync
Terminal=false
Categories=Utility;System;FileTools;
Keywords=nfs;sync;backup;mount;
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE"
echo "✅ Desktop Entry erstellt: $DESKTOP_FILE"

# Make scripts executable
chmod +x nfs_sync_backend.py
chmod +x nfs_sync_gui.py

echo ""
echo -e "${YELLOW}🔗 Schritt 3: Erstelle Symlink für Terminal-Befehl...${NC}"

# Create symlink in ~/.local/bin
mkdir -p "$HOME/.local/bin"
ln -sf "$SCRIPT_DIR/nfs_sync_gui.py" "$HOME/.local/bin/nfs-sync-manager"

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo -e "${YELLOW}⚠️  Hinweis: ~/.local/bin ist nicht im PATH${NC}"
    echo "   Füge folgende Zeile zu ~/.bashrc oder ~/.zshrc hinzu:"
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo "✅ Symlink erstellt: ~/.local/bin/nfs-sync-manager"

echo ""
echo -e "${YELLOW}⚙️  Schritt 4: Erstelle Konfigurationsverzeichnis...${NC}"

CONFIG_DIR="$HOME/.config/nfs-sync-manager"
mkdir -p "$CONFIG_DIR"
echo "✅ Config-Verzeichnis: $CONFIG_DIR"

echo ""
echo -e "${YELLOW}🔐 Schritt 5: Prüfe sudo-Rechte...${NC}"

# Check if user can mount without password
if sudo -n mount -t nfs 2>/dev/null; then
    echo "✅ Sudo-Rechte vorhanden"
else
    echo -e "${YELLOW}⚠️  Du benötigst sudo-Rechte zum Mounten${NC}"
    echo "   Optional: Erlaube mounten ohne Passwort:"
    echo "   sudo visudo"
    echo "   Füge hinzu: $USER ALL=(ALL) NOPASSWD: /usr/bin/mount, /usr/bin/umount"
fi

echo ""
echo -e "${YELLOW}🎨 Schritt 6 (Optional): Autostart aktivieren?${NC}"
read -p "Soll die App beim Login automatisch starten? (j/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[JjYy]$ ]]; then
    AUTOSTART_DIR="$HOME/.config/autostart"
    mkdir -p "$AUTOSTART_DIR"
    cp "$DESKTOP_FILE" "$AUTOSTART_DIR/"
    echo "✅ Autostart aktiviert"
else
    echo "⏭️  Autostart übersprungen"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Installation erfolgreich!         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo "📝 Nächste Schritte:"
echo ""
echo "1️⃣  Starte die GUI:"
echo "   • Im Anwendungsmenü: Suche 'NFS Sync Manager'"
echo "   • Im Terminal: nfs-sync-manager"
echo ""
echo "2️⃣  Konfiguriere die Einstellungen:"
echo "   • Klicke auf ☰ → Einstellungen"
echo "   • Gib NFS-Server und Pfade ein"
echo ""
echo "3️⃣  Teste die Verbindung:"
echo "   • Klicke 'Mount'"
echo "   • Klicke 'Test-Sync'"
echo ""
echo "📁 Dateien:"
echo "   Config:  $CONFIG_DIR/config.json"
echo "   Log:     $CONFIG_DIR/nfs-sync.log"
echo "   Script:  $SCRIPT_DIR"
echo ""
echo "🆘 Bei Problemen:"
echo "   Log anschauen: cat ~/.config/nfs-sync-manager/nfs-sync.log"
echo "   Backend testen: python nfs_sync_backend.py status"
echo ""

# Offer to start the application
read -p "Möchtest du die Anwendung jetzt starten? (j/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[JjYy]$ ]]; then
    echo "🚀 Starte NFS Sync Manager..."
    "$SCRIPT_DIR/nfs_sync_gui.py" &
    echo "✅ Gestartet!"
fi

echo ""
echo "Viel Erfolg! 🎉"

