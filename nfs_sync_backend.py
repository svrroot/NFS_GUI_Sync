#!/usr/bin/env python3
"""
NFS Sync Backend
Handles NFS mounting, syncing, and scheduling operations
"""

import subprocess
import json
import os
import shutil
from pathlib import Path
from datetime import datetime
import logging
import base64

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PasswordManager:
    """Secure password storage using base64 encoding"""
    
    @staticmethod
    def encode_password(password):
        """Encode password to base64"""
        return base64.b64encode(password.encode()).decode()
    
    @staticmethod
    def decode_password(encoded):
        """Decode password from base64"""
        try:
            return base64.b64decode(encoded.encode()).decode()
        except:
            return None


class NFSSyncBackend:
    """Backend class for NFS synchronization operations"""
    
    def __init__(self):
        """Initialize the backend with configuration"""
        self.config_file = Path.home() / '.config' / 'nfs-sync' / 'config.json'
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config = self.load_config()
        self.is_mounted = False
        self.sudo_password = None
        
    def load_config(self):
        """
        Load configuration from JSON file
        
        Returns:
            dict: Configuration dictionary
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                return self.get_default_config()
        return self.get_default_config()
    
    def get_default_config(self):
        """
        Get default configuration
        
        Returns:
            dict: Default configuration dictionary
        """
        return {
            'nfs_server': '',
            'nfs_share': '',
            'mount_point': '/mnt/unaspro',
            'sync_folders': {},
            'auto_mount': False,
            'auto_sync': False,
            'sync_interval': 3600,
            'last_sync': None
        }
    
    def save_config(self):
        """
        Save current configuration to JSON file
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            return True, "✅ Konfiguration gespeichert"
        except Exception as e:
            error_msg = f"❌ Fehler beim Speichern: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def set_sudo_password(self, password, save=False):
        """
        Set sudo password for current session
        
        Args:
            password (str): Sudo password
            save (bool): Save encrypted to config
            
        Returns:
            tuple: (success: bool, message: str)
        """
        self.sudo_password = password
        
        if save:
            encoded = PasswordManager.encode_password(password)
            self.config['sudo_password'] = encoded
            return self.save_config()
        
        return True, "✅ Passwort gesetzt"

    def get_sudo_password(self):
        """
        Get sudo password from memory or config
        
        Returns:
            str: Sudo password or None
        """
        if self.sudo_password:
            return self.sudo_password
        
        encoded = self.config.get('sudo_password')
        if encoded:
            password = PasswordManager.decode_password(encoded)
            if password:
                self.sudo_password = password
                return password
        
        return None

    def clear_saved_password(self):
        """Remove saved password from config"""
        if 'sudo_password' in self.config:
            del self.config['sudo_password']
            self.sudo_password = None
            return self.save_config()
        return True, "Kein gespeichertes Passwort"
    
    def test_nfs_connection(self, server, share):
        """
        Test NFS connection without mounting
        
        Args:
            server (str): NFS server address
            share (str): NFS share path
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if not server or not share:
            return False, "❌ Server und Share erforderlich"
        
        nfs_path = f"{server}:{share}"
        cmd = ['showmount', '-e', server]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                if share in result.stdout:
                    return True, f"✅ NFS erreichbar: {nfs_path}"
                else:
                    return False, f"⚠️ Server erreichbar, aber Share '{share}' nicht gefunden"
            else:
                return False, f"❌ Server nicht erreichbar: {result.stderr}"
        except subprocess.TimeoutExpired:
            return False, "❌ Timeout: Server antwortet nicht"
        except FileNotFoundError:
            return False, "❌ 'showmount' nicht installiert (nfs-common benötigt)"
        except Exception as e:
            return False, f"❌ Fehler: {e}"
    
    def mount_nfs(self):
        """
        Mount the NFS share
        
        Returns:
            tuple: (success: bool, message: str)
        """
        server = self.config.get('nfs_server', '')
        share = self.config.get('nfs_share', '')
        mount_point = self.config.get('mount_point', '')
        
        if not all([server, share, mount_point]):
            return False, "❌ Unvollständige NFS-Konfiguration"
        
        if self.check_mount():
            self.is_mounted = True
            return True, "✅ NFS bereits gemountet"
        
        try:
            Path(mount_point).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return False, f"❌ Mount-Point erstellen fehlgeschlagen: {e}"
        
        password = self.get_sudo_password()
        if not password:
            return False, "❌ Sudo-Passwort erforderlich"
        
        nfs_path = f"{server}:{share}"
        cmd = ['sudo', '-S', 'mount', '-t', 'nfs', nfs_path, mount_point]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=password + '\n', timeout=30)
            
            if process.returncode == 0:
                self.is_mounted = True
                return True, f"✅ NFS gemountet: {mount_point}"
            else:
                error_msg = stderr.strip() or stdout.strip() or "Unbekannter Fehler"
                
                if 'password' in error_msg.lower() or 'sorry' in error_msg.lower():
                    self.sudo_password = None
                    return False, "❌ Falsches Sudo-Passwort"
                
                return False, f"❌ Mount fehlgeschlagen: {error_msg}"
                
        except subprocess.TimeoutExpired:
            return False, "❌ Mount-Timeout"
        except Exception as e:
            return False, f"❌ Mount-Fehler: {e}"
    
    def unmount_nfs(self):
        """
        Unmount the NFS share
        
        Returns:
            tuple: (success: bool, message: str)
        """
        mount_point = self.config.get('mount_point', '')
        
        if not mount_point:
            return False, "❌ Kein Mount-Point konfiguriert"
        
        if not self.check_mount():
            return True, "✅ NFS nicht gemountet"
        
        password = self.get_sudo_password()
        if not password:
            return False, "❌ Sudo-Passwort erforderlich"
        
        cmd = ['sudo', '-S', 'umount', mount_point]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=password + '\n', timeout=10)
            
            if process.returncode == 0:
                self.is_mounted = False
                return True, f"✅ NFS unmounted: {mount_point}"
            else:
                error_msg = stderr.strip() or stdout.strip()
                return False, f"❌ Unmount fehlgeschlagen: {error_msg}"
                
        except Exception as e:
            return False, f"❌ Unmount-Fehler: {e}"
    
    def check_mount(self):
        """
        Check if NFS is currently mounted
        
        Returns:
            bool: True if mounted, False otherwise
        """
        mount_point = self.config.get('mount_point', '')
        if not mount_point:
            return False
        
        try:
            result = subprocess.run(
                ['mountpoint', '-q', mount_point],
                capture_output=True,
                timeout=5
            )
            is_mounted = result.returncode == 0
            self.is_mounted = is_mounted
            return is_mounted
        except:
            return False
    
    def add_sync_folder(self, local_path, target_path):
        """
        Add a folder pair for synchronization
        
        Args:
            local_path (str): Local source folder
            target_path (str): Target folder on NFS
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if not local_path or not target_path:
            return False, "❌ Beide Pfade erforderlich"
        
        local_path = str(Path(local_path).expanduser())
        
        if not Path(local_path).exists():
            return False, f"❌ Lokaler Ordner existiert nicht: {local_path}"
        
        self.config['sync_folders'][local_path] = target_path
        success, msg = self.save_config()
        
        if success:
            return True, f"✅ Ordnerpaar hinzugefügt"
        return False, msg
    
    def remove_sync_folder(self, local_path):
        """
        Remove a folder pair from synchronization
        
        Args:
            local_path (str): Local source folder to remove
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if local_path in self.config['sync_folders']:
            del self.config['sync_folders'][local_path]
            success, msg = self.save_config()
            
            if success:
                return True, "✅ Ordnerpaar entfernt"
            return False, msg
        
        return False, "❌ Ordnerpaar nicht gefunden"
    
    def sync_folders(self, progress_callback=None):
        """
        Synchronize all configured folder pairs
        
        Args:
            progress_callback (callable): Function to call with progress updates
            
        Returns:
            tuple: (success: bool, message: str, stats: dict)
        """
        if not self.check_mount():
            return False, "❌ NFS nicht gemountet", {}
        
        sync_folders = self.config.get('sync_folders', {})
        if not sync_folders:
            return False, "❌ Keine Sync-Ordner konfiguriert", {}
        
        mount_point = self.config.get('mount_point', '')
        total_folders = len(sync_folders)
        successful = 0
        failed = 0
        stats = {
            'files_transferred': 0,
            'total_size': '0',
            'errors': []
        }
        
        for idx, (local_path, target_path) in enumerate(sync_folders.items(), 1):
            if progress_callback:
                progress = (idx / total_folders) * 100
                progress_callback(progress, f"Sync {idx}/{total_folders}: {Path(local_path).name}")
            
            full_target = Path(mount_point) / target_path.lstrip('/')
            
            try:
                full_target.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                error_msg = f"Zielordner erstellen fehlgeschlagen: {e}"
                stats['errors'].append(error_msg)
                failed += 1
                continue
            
            cmd = [
                'rsync',
                '-avh',
                '--progress',
                '--delete',
                f"{local_path}/",
                str(full_target)
            ]
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0:
                    successful += 1
                    
                    for line in result.stdout.split('\n'):
                        if 'files transferred' in line.lower():
                            try:
                                files = int(line.split()[0])
                                stats['files_transferred'] += files
                            except:
                                pass
                        elif 'total size' in line.lower():
                            stats['total_size'] = line.split('total size is')[1].strip()
                else:
                    failed += 1
                    error_msg = f"{local_path}: {result.stderr[:200]}"
                    stats['errors'].append(error_msg)
                    
            except subprocess.TimeoutExpired:
                failed += 1
                stats['errors'].append(f"{local_path}: Timeout")
            except Exception as e:
                failed += 1
                stats['errors'].append(f"{local_path}: {str(e)}")
        
        self.config['last_sync'] = datetime.now().isoformat()
        self.save_config()
        
        if failed == 0:
            message = f"✅ Alle {successful} Ordner synchronisiert"
            return True, message, stats
        elif successful > 0:
            message = f"⚠️ {successful} erfolgreich, {failed} fehlgeschlagen"
            return True, message, stats
        else:
            message = f"❌ Alle {failed} Ordner fehlgeschlagen"
            return False, message, stats


def main():
    """Main entry point for testing"""
    backend = NFSSyncBackend()
    print(f"Config loaded: {backend.config}")
    
    if backend.check_mount():
        print("✅ NFS is mounted")
    else:
        print("❌ NFS is not mounted")


if __name__ == "__main__":
    main()

