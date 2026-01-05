# 🔄 NFS Sync Manager

Ein leistungsstarker, benutzerfreundlicher Sync-Manager für NFS-Shares mit GTK3-GUI. Perfekt für automatische Backups auf NAS-Systeme!

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey.svg)

## ✨ Features

### 🎯 Kern-Features
- ✅ **Differenz-Sync** - Nur geänderte Dateien werden übertragen
- ✅ **Live-Monitoring** - Sieh jede kopierte Datei in Echtzeit
- ✅ **Stop-Funktion** - Sync jederzeit sauber abbrechen
- ✅ **Exclude-Patterns** - Definiere was NICHT gesichert werden soll
- ✅ **Thread-sicher** - UI bleibt während Sync responsiv
- ✅ **Passwort-Manager** - Sichere Speicherung mit Keyring

### 🖥️ GUI-Features
- 📊 Live-Progress mit Emoji-Feedback
- 📁 Einfache Ordner-Verwaltung
- 🎨 Moderne GTK3-Oberfläche
- 🔧 Umfangreiche Einstellungen
- 📝 Detailliertes Log-Fenster

### 🔐 Sicherheit
- 🔒 Passwörter werden **NIE** im Klartext gespeichert
- 🗝️ Verwendung des System-Keyrings (GNOME Keyring / KWallet)
- ✅ Sichere CIFS-Mount-Optionen



## 📋 Voraussetzungen

### System-Pakete
```bash
# Debian/Ubuntu
sudo apt install python3 python3-pip python3-gi gir1.2-gtk-3.0 rsync cifs-utils

# Fedora/RHEL
sudo dnf install python3 python3-pip python3-gobject gtk3 rsync cifs-utils

# Arch Linux
sudo pacman -S python python-pip python-gobject gtk3 rsync cifs-utils

pip3 install keyring

# Repository klonen
git clone https://github.com/DEIN-USERNAME/nfs-sync-manager.git
cd nfs-sync-manager

# Ausführbar machen
chmod +x nfs_sync_gui.py

# Starten
./nfs_sync_gui.py


# Dateien herunterladen
wget https://raw.githubusercontent.com/svrroot/nfs-sync-manager/main/nfs_sync_gui.py
wget https://raw.githubusercontent.com/svrroot/nfs-sync-manager/main/nfs_sync_backend.py

# Ausführbar machen
chmod +x nfs_sync_gui.py

# Starten
./nfs_sync_gui.py





# Desktop-Eintrag erstellen
cat > ~/.local/share/applications/nfs-sync.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=NFS Sync Manager
Comment=Sync folders to NFS shares
Exec=/PFAD/ZU/nfs_sync_gui.py
Icon=folder-sync
Terminal=false
Categories=Utility;System;
EOF




# Icon kopieren (optional)
cp icon.png ~/.local/share/icons/hicolor/48x48/apps/nfs-sync.png




Konfigurationsdatei
Speicherort:
~/.config/nfs_sync/config.json
Inhalt:
{
    "nfs_server": "192.168.1.100",
    "nfs_share": "backup",
    "nfs_mount": "/mnt/nfs_backup",
    "sync_folders": [
        {
            "local_path": "/home/user/Documents",
            "target_subdir": "documents",
            "enabled": true
        },
        {
            "local_path": "/home/user/Photos",
            "target_subdir": "photos",
            "enabled": true
        }
    ],
    "exclude_patterns": [
        ".git",
        "node_modules",
        "__pycache__",
        "*.tmp",
        "*.swp"
    ]
}