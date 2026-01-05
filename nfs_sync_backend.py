#!/usr/bin/env python3
"""
NFS Sync Backend
Handles all sync operations, config management and NFS operations
"""

import os
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import keyring
import threading

class NFSSyncBackend:
    """Backend for NFS sync operations"""
    
    def __init__(self):
        self.config_dir = Path.home() / '.config' / 'nfs_sync'
        self.config_file = self.config_dir / 'config.json'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.config = self.load_config()
        self.stop_sync = False
        self.sync_process = None
        self.sync_thread = None
        
    def load_config(self):
        """Load configuration from file"""
        default_config = {
            'nfs_server': '',
            'nfs_share': '',
            'nfs_mount': '/mnt/nfs_backup',
            'sync_folders': [],
            'exclude_patterns': [
                '.git',
                'node_modules',
                '__pycache__',
                '*.tmp',
                '*.swp'
            ]
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                    default_config.update(loaded)
            except Exception as e:
                print(f"Error loading config: {e}")
        
        return default_config
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get_nfs_password(self):
        """Get NFS password from keyring"""
        try:
            return keyring.get_password("nfs_sync", "nfs_mount")
        except:
            return None
    
    def set_nfs_password(self, password):
        """Store NFS password in keyring"""
        try:
            keyring.set_password("nfs_sync", "nfs_mount", password)
            return True
        except Exception as e:
            print(f"Error storing password: {e}")
            return False
    
    def clear_nfs_password(self):
        """Clear stored NFS password"""
        try:
            keyring.delete_password("nfs_sync", "nfs_mount")
            return True
        except keyring.errors.PasswordDeleteError:
            return True
        except Exception as e:
            print(f"Error clearing password: {e}")
            return False
    
    def is_nfs_mounted(self):
        """Check if NFS is currently mounted"""
        mount_point = self.config.get('nfs_mount', '')
        if not mount_point:
            return False
        
        try:
            result = subprocess.run(
                ['mountpoint', '-q', mount_point],
                capture_output=True
            )
            return result.returncode == 0
        except:
            return False
    
    def mount_nfs(self, password=None):
        """Mount NFS share"""
        server = self.config.get('nfs_server', '')
        share = self.config.get('nfs_share', '')
        mount_point = self.config.get('nfs_mount', '')
        
        if not all([server, share, mount_point]):
            return False, "NFS-Konfiguration unvollständig"
        
        try:
            Path(mount_point).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return False, f"Mount-Point erstellen fehlgeschlagen: {e}"
        
        if self.is_nfs_mounted():
            return True, "NFS bereits gemountet"
        
        nfs_source = f"{server}:{share}"
        
        try:
            if password:
                process = subprocess.Popen(
                    ['sudo', '-S', 'mount', '-t', 'nfs', nfs_source, mount_point],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(input=f"{password}\n", timeout=10)
                
                if process.returncode == 0:
                    return True, "NFS erfolgreich gemountet"
                else:
                    return False, f"Mount fehlgeschlagen: {stderr}"
            else:
                result = subprocess.run(
                    ['sudo', 'mount', '-t', 'nfs', nfs_source, mount_point],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    return True, "NFS erfolgreich gemountet"
                else:
                    return False, f"Mount fehlgeschlagen: {result.stderr}"
                    
        except subprocess.TimeoutExpired:
            return False, "Mount-Timeout"
        except Exception as e:
            return False, f"Mount-Fehler: {e}"
    
    def unmount_nfs(self, password=None):
        """Unmount NFS share"""
        mount_point = self.config.get('nfs_mount', '')
        
        if not mount_point:
            return False, "Kein Mount-Point konfiguriert"
        
        if not self.is_nfs_mounted():
            return True, "NFS nicht gemountet"
        
        try:
            if password:
                process = subprocess.Popen(
                    ['sudo', '-S', 'umount', mount_point],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(input=f"{password}\n", timeout=10)
                
                if process.returncode == 0:
                    return True, "NFS erfolgreich unmountet"
                else:
                    return False, f"Unmount fehlgeschlagen: {stderr}"
            else:
                result = subprocess.run(
                    ['sudo', 'umount', mount_point],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    return True, "NFS erfolgreich unmountet"
                else:
                    return False, f"Unmount fehlgeschlagen: {result.stderr}"
                    
        except subprocess.TimeoutExpired:
            return False, "Unmount-Timeout"
        except Exception as e:
            return False, f"Unmount-Fehler: {e}"
    
    def add_sync_folder(self, local_path, target_path):
        """Add a new sync folder pair"""
        local_path = str(Path(local_path).resolve())
        
        for folder in self.config['sync_folders']:
            if folder['local'] == local_path:
                return False, "Lokaler Ordner bereits in Liste"
        
        self.config['sync_folders'].append({
            'local': local_path,
            'target': target_path,
            'enabled': True
        })
        
        self.save_config()
        return True, "Ordnerpaar hinzugefügt"
    
    def remove_sync_folder(self, local_path):
        """Remove a sync folder pair"""
        self.config['sync_folders'] = [
            f for f in self.config['sync_folders']
            if f['local'] != local_path
        ]
        self.save_config()
        return True, "Ordnerpaar entfernt"
    
    def toggle_folder_enabled(self, local_path):
        """Toggle enabled state of a folder pair"""
        for folder in self.config['sync_folders']:
            if folder['local'] == local_path:
                folder['enabled'] = not folder.get('enabled', True)
                self.save_config()
                return True
        return False
    
    def get_sync_folders(self):
        """Get all sync folder pairs"""
        return self.config.get('sync_folders', [])
    
    def stop_sync_process(self):
        """Stop running sync process"""
        self.stop_sync = True
        if self.sync_process and self.sync_process.poll() is None:
            try:
                self.sync_process.terminate()
                self.sync_process.wait(timeout=5)
            except:
                try:
                    self.sync_process.kill()
                except:
                    pass
    
    def sync_folder(self, local_path, target_path, progress_callback=None):
        """Sync a single folder pair using rsync with live file monitoring"""
        
        if not self.is_nfs_mounted():
            return False, "NFS nicht gemountet"
        
        if self.stop_sync:
            return False, "Sync abgebrochen"
        
        mount_point = self.config.get('nfs_mount', '')
        full_target = Path(mount_point) / target_path.lstrip('/')
        
        try:
            full_target.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return False, f"Zielordner erstellen fehlgeschlagen: {e}"
        
        exclude_args = []
        for pattern in self.config.get('exclude_patterns', []):
            exclude_args.extend(['--exclude', pattern])
        
        rsync_cmd = [
            'rsync',
            '-avh',
            '--info=progress2',
            '--delete',
            *exclude_args,
            f"{local_path}/",
            f"{full_target}/"
        ]
        
        try:
            self.sync_process = subprocess.Popen(
                rsync_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Read output line by line
            for line in self.sync_process.stdout:
                if self.stop_sync:
                    self.sync_process.terminate()
                    return False, "Sync abgebrochen"
                
                line = line.strip()
                if line and progress_callback:
                    # Parse rsync output for file names
                    if line.startswith('sending incremental file list'):
                        continue
                    elif line.startswith('sent ') or line.startswith('total size'):
                        progress_callback(f"    📊 {line}")
                    elif '%' in line and 'xfr#' in line:
                        # Progress line
                        progress_callback(f"    ⏳ {line}")
                    elif not line.startswith('.d') and len(line) > 0:
                        # File name
                        progress_callback(f"    📄 {line}")
            
            self.sync_process.wait()
            
            if self.sync_process.returncode == 0:
                return True, "Sync erfolgreich"
            else:
                stderr = self.sync_process.stderr.read()
                return False, f"Rsync-Fehler: {stderr}"
                
        except Exception as e:
            return False, f"Sync-Fehler: {e}"
        finally:
            self.sync_process = None
    
    def sync_all(self, progress_callback=None, finished_callback=None):
        """Sync all enabled folders in background thread"""
        
        def sync_thread():
            self.stop_sync = False
            
            if not self.is_nfs_mounted():
                if progress_callback:
                    progress_callback("❌ NFS nicht gemountet")
                if finished_callback:
                    finished_callback(False, "NFS nicht gemountet")
                return
            
            success_count = 0
            error_count = 0
            errors = []
            
            enabled_folders = [f for f in self.config['sync_folders'] if f.get('enabled', True)]
            
            if not enabled_folders:
                if progress_callback:
                    progress_callback("⚠️  Keine aktivierten Ordner zum Syncen")
                if finished_callback:
                    finished_callback(False, "Keine aktivierten Ordner")
                return
            
            total = len(enabled_folders)
            
            for idx, folder in enumerate(enabled_folders, 1):
                if self.stop_sync:
                    if progress_callback:
                        progress_callback("\n🛑 Sync wurde abgebrochen!")
                    if finished_callback:
                        finished_callback(False, "Sync abgebrochen")
                    return
                
                local = folder['local']
                target = folder['target']
                
                if progress_callback:
                    progress_callback(f"\n{'='*60}")
                    progress_callback(f"📁 [{idx}/{total}] {local}")
                    progress_callback(f"    → {target}")
                    progress_callback(f"{'='*60}")
                
                success, message = self.sync_folder(local, target, progress_callback)
                
                if self.stop_sync:
                    if finished_callback:
                        finished_callback(False, "Sync abgebrochen")
                    return
                
                if success:
                    success_count += 1
                    if progress_callback:
                        progress_callback(f"    ✅ Erfolgreich abgeschlossen")
                else:
                    error_count += 1
                    errors.append(f"{local}: {message}")
                    if progress_callback:
                        progress_callback(f"    ❌ {message}")
            
            # Final summary
            if progress_callback:
                progress_callback(f"\n{'='*60}")
                progress_callback(f"📊 ZUSAMMENFASSUNG:")
                progress_callback(f"   ✅ Erfolgreich: {success_count}")
                progress_callback(f"   ❌ Fehlgeschlagen: {error_count}")
                progress_callback(f"{'='*60}")
            
            if error_count == 0:
                final_msg = f"Alle {success_count} Ordner erfolgreich gesync't"
                if finished_callback:
                    finished_callback(True, final_msg)
            else:
                error_msg = f"{success_count} erfolgreich, {error_count} fehlgeschlagen"
                if finished_callback:
                    finished_callback(False, error_msg)
        
        # Start sync in background thread
        self.sync_thread = threading.Thread(target=sync_thread, daemon=True)
        self.sync_thread.start()

