#!/usr/bin/env python3
"""
NFS Sync GUI
GTK3 interface for NFS backup synchronization
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Pango
from pathlib import Path
from datetime import datetime
from nfs_sync_backend import NFSSyncBackend

class SettingsDialog(Gtk.Dialog):
    """Settings dialog with NFS config and Exclude patterns"""
    
    def __init__(self, parent, backend):
        super().__init__(
            title="Einstellungen",
            parent=parent,
            flags=Gtk.DialogFlags.MODAL
        )
        
        self.backend = backend
        self.set_default_size(600, 500)
        
        self.add_buttons(
            Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE
        )
        
        content = self.get_content_area()
        content.set_border_width(10)
        
        notebook = Gtk.Notebook()
        content.pack_start(notebook, True, True, 0)
        
        nfs_box = self._create_nfs_tab()
        notebook.append_page(nfs_box, Gtk.Label(label="NFS"))
        
        exclude_box = self._create_exclude_tab()
        notebook.append_page(exclude_box, Gtk.Label(label="Exclude"))
        
        self.show_all()
    
    def _create_nfs_tab(self):
        """Create NFS configuration tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)
        
        box.pack_start(Gtk.Label(label="NFS Server:", xalign=0), False, False, 0)
        self.server_entry = Gtk.Entry()
        self.server_entry.set_text(self.backend.config.get('nfs_server', ''))
        self.server_entry.set_placeholder_text("192.168.1.100")
        box.pack_start(self.server_entry, False, False, 0)
        
        box.pack_start(Gtk.Label(label="NFS Share:", xalign=0), False, False, 0)
        self.share_entry = Gtk.Entry()
        self.share_entry.set_text(self.backend.config.get('nfs_share', ''))
        self.share_entry.set_placeholder_text("/volume1/backup")
        box.pack_start(self.share_entry, False, False, 0)
        
        box.pack_start(Gtk.Label(label="Mount Point:", xalign=0), False, False, 0)
        self.mount_entry = Gtk.Entry()
        self.mount_entry.set_text(self.backend.config.get('nfs_mount', ''))
        self.mount_entry.set_placeholder_text("/mnt/nfs_backup")
        box.pack_start(self.mount_entry, False, False, 0)
        
        save_btn = Gtk.Button(label="Speichern")
        save_btn.connect("clicked", self._on_save_nfs)
        box.pack_start(save_btn, False, False, 10)
        
        return box
    
    def _create_exclude_tab(self):
        """Create exclude patterns tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)
        
        info = Gtk.Label(
            label="Diese Muster werden beim Sync ignoriert.\nUnterstützt Wildcards (* und ?)",
            xalign=0
        )
        info.set_line_wrap(True)
        box.pack_start(info, False, False, 0)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        box.pack_start(scroll, True, True, 0)
        
        self.exclude_store = Gtk.ListStore(str)
        for pattern in self.backend.config.get('exclude_patterns', []):
            self.exclude_store.append([pattern])
        
        self.exclude_view = Gtk.TreeView(model=self.exclude_store)
        self.exclude_view.set_headers_visible(False)
        
        renderer = Gtk.CellRendererText()
        renderer.set_property("editable", True)
        renderer.connect("edited", self._on_pattern_edited)
        
        column = Gtk.TreeViewColumn("Pattern", renderer, text=0)
        self.exclude_view.append_column(column)
        
        scroll.add(self.exclude_view)
        
        btn_box = Gtk.Box(spacing=5)
        box.pack_start(btn_box, False, False, 0)
        
        add_btn = Gtk.Button(label="Hinzufügen")
        add_btn.connect("clicked", self._on_add_pattern)
        btn_box.pack_start(add_btn, True, True, 0)
        
        remove_btn = Gtk.Button(label="Entfernen")
        remove_btn.connect("clicked", self._on_remove_pattern)
        btn_box.pack_start(remove_btn, True, True, 0)
        
        return box
    
    def _on_save_nfs(self, button):
        """Save NFS configuration"""
        self.backend.config['nfs_server'] = self.server_entry.get_text()
        self.backend.config['nfs_share'] = self.share_entry.get_text()
        self.backend.config['nfs_mount'] = self.mount_entry.get_text()
        self.backend.save_config()
        
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="NFS-Konfiguration gespeichert!"
        )
        dialog.run()
        dialog.destroy()
    
    def _on_add_pattern(self, button):
        """Add new exclude pattern"""
        dialog = Gtk.Dialog(
            title="Pattern hinzufügen",
            parent=self,
            flags=Gtk.DialogFlags.MODAL
        )
        
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        
        content = dialog.get_content_area()
        content.set_border_width(10)
        content.set_spacing(10)
        
        content.pack_start(Gtk.Label(label="Exclude Pattern:"), False, False, 0)
        
        entry = Gtk.Entry()
        entry.set_placeholder_text("*.tmp")
        entry.set_activates_default(True)
        content.pack_start(entry, False, False, 0)
        
        dialog.set_default_response(Gtk.ResponseType.OK)
        content.show_all()
        
        response = dialog.run()
        pattern = entry.get_text()
        dialog.destroy()
        
        if response == Gtk.ResponseType.OK and pattern:
            self.exclude_store.append([pattern])
            self._save_exclude_patterns()
    
    def _on_remove_pattern(self, button):
        """Remove selected pattern"""
        selection = self.exclude_view.get_selection()
        model, tree_iter = selection.get_selected()
        
        if tree_iter:
            model.remove(tree_iter)
            self._save_exclude_patterns()
    
    def _on_pattern_edited(self, renderer, path, new_text):
        """Handle pattern edit"""
        self.exclude_store[path][0] = new_text
        self._save_exclude_patterns()
    
    def _save_exclude_patterns(self):
        """Save exclude patterns to config"""
        patterns = []
        for row in self.exclude_store:
            patterns.append(row[0])
        
        self.backend.config['exclude_patterns'] = patterns
        self.backend.save_config()
class NFSSyncGUI(Gtk.Window):
    """Main GUI window"""
    
    def __init__(self):
        super().__init__(title="NFS Backup Sync")
        
        self.backend = NFSSyncBackend()
        self.is_syncing = False
        
        self.set_default_size(800, 600)
        self.set_border_width(10)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)
        
        # NFS Status
        nfs_frame = Gtk.Frame(label="NFS Status")
        vbox.pack_start(nfs_frame, False, False, 0)
        
        nfs_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        nfs_box.set_border_width(10)
        nfs_frame.add(nfs_box)
        
        self.status_label = Gtk.Label(label="Status: Nicht verbunden")
        self.status_label.set_xalign(0)
        nfs_box.pack_start(self.status_label, False, False, 0)
        
        button_box = Gtk.Box(spacing=5)
        nfs_box.pack_start(button_box, False, False, 0)
        
        self.mount_button = Gtk.Button(label="Mount")
        self.mount_button.connect("clicked", self._on_mount)
        button_box.pack_start(self.mount_button, True, True, 0)
        
        self.unmount_button = Gtk.Button(label="Unmount")
        self.unmount_button.connect("clicked", self._on_unmount)
        self.unmount_button.set_sensitive(False)
        button_box.pack_start(self.unmount_button, True, True, 0)
        
        # Password
        password_frame = Gtk.Frame(label="Sudo-Passwort")
        vbox.pack_start(password_frame, False, False, 0)
        
        password_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        password_box.set_border_width(10)
        password_frame.add(password_box)
        
        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_placeholder_text("Optional: Passwort für sudo")
        password_box.pack_start(self.password_entry, False, False, 0)
        
        pwd_button_box = Gtk.Box(spacing=5)
        password_box.pack_start(pwd_button_box, False, False, 0)
        
        set_pwd_button = Gtk.Button(label="Passwort setzen")
        set_pwd_button.connect("clicked", self._on_set_password)
        pwd_button_box.pack_start(set_pwd_button, True, True, 0)
        
        clear_pwd_button = Gtk.Button(label="Gespeichertes löschen")
        clear_pwd_button.connect("clicked", self._on_clear_password)
        pwd_button_box.pack_start(clear_pwd_button, True, True, 0)
        
        # Sync Folders
        folders_frame = Gtk.Frame(label="Sync-Ordner")
        vbox.pack_start(folders_frame, True, True, 0)
        
        folders_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        folders_box.set_border_width(10)
        folders_frame.add(folders_box)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        folders_box.pack_start(scroll, True, True, 0)
        
        self.folder_store = Gtk.ListStore(bool, str, str)
        self.folder_view = Gtk.TreeView(model=self.folder_store)
        
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self._on_folder_toggled)
        column_enabled = Gtk.TreeViewColumn("Aktiv", renderer_toggle, active=0)
        self.folder_view.append_column(column_enabled)
        
        renderer_text = Gtk.CellRendererText()
        column_local = Gtk.TreeViewColumn("Lokaler Ordner", renderer_text, text=1)
        column_local.set_expand(True)
        self.folder_view.append_column(column_local)
        
        renderer_text = Gtk.CellRendererText()
        column_target = Gtk.TreeViewColumn("Ziel-Ordner", renderer_text, text=2)
        column_target.set_expand(True)
        self.folder_view.append_column(column_target)
        
        scroll.add(self.folder_view)
        
        folder_btn_box = Gtk.Box(spacing=5)
        folders_box.pack_start(folder_btn_box, False, False, 0)
        
        add_folder_btn = Gtk.Button(label="Ordnerpaar hinzufügen")
        add_folder_btn.connect("clicked", self._on_add_folder)
        folder_btn_box.pack_start(add_folder_btn, True, True, 0)
        
        remove_folder_btn = Gtk.Button(label="Entfernen")
        remove_folder_btn.connect("clicked", self._on_remove_folder)
        folder_btn_box.pack_start(remove_folder_btn, True, True, 0)
        
        # Log
        log_frame = Gtk.Frame(label="Log")
        vbox.pack_start(log_frame, True, True, 0)
        
        log_scroll = Gtk.ScrolledWindow()
        log_scroll.set_vexpand(True)
        log_scroll.set_min_content_height(150)
        log_frame.add(log_scroll)
        
        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.log_view.modify_font(Pango.FontDescription("monospace 9"))
        self.log_buffer = self.log_view.get_buffer()
        log_scroll.add(self.log_view)
        
        # Bottom buttons
        bottom_box = Gtk.Box(spacing=5)
        vbox.pack_start(bottom_box, False, False, 0)
        
        self.sync_button = Gtk.Button(label="🚀 Sync starten")
        self.sync_button.connect("clicked", self._on_sync_clicked)
        self.sync_button.set_sensitive(False)
        bottom_box.pack_start(self.sync_button, True, True, 0)
        
        settings_button = Gtk.Button(label="⚙️ Einstellungen")
        settings_button.connect("clicked", self._on_open_settings)
        bottom_box.pack_start(settings_button, True, True, 0)
        
        self._update_status()
        self._update_folder_list()
        
        self.connect("destroy", Gtk.main_quit)
    
    def _log(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        GLib.idle_add(self._log_idle, f"[{timestamp}] {message}\n")
    
    def _log_idle(self, message):
        """Idle handler for logging (thread-safe)"""
        self.log_buffer.insert(
            self.log_buffer.get_end_iter(),
            message
        )
        
        mark = self.log_buffer.create_mark(None, self.log_buffer.get_end_iter(), False)
        self.log_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
        return False
    
    def _update_status(self):
        """Update NFS mount status"""
        is_mounted = self.backend.is_nfs_mounted()
        
        if is_mounted:
            self.status_label.set_markup("<b>Status: <span foreground='green'>Verbunden</span></b>")
            self.mount_button.set_sensitive(False)
            self.unmount_button.set_sensitive(True)
            if not self.is_syncing:
                self.sync_button.set_sensitive(True)
        else:
            self.status_label.set_markup("<b>Status: <span foreground='red'>Nicht verbunden</span></b>")
            self.mount_button.set_sensitive(True)
            self.unmount_button.set_sensitive(False)
            self.sync_button.set_sensitive(False)
    
    def _update_folder_list(self):
        """Refresh folder list"""
        self.folder_store.clear()
        
        for folder in self.backend.get_sync_folders():
            self.folder_store.append([
                folder.get('enabled', True),
                folder['local'],
                folder['target']
            ])
    
    def _on_mount(self, button):
        """Handle mount button click"""
        password = self.password_entry.get_text() or self.backend.get_nfs_password()
        
        self._log("Mounte NFS...")
        success, message = self.backend.mount_nfs(password)
        
        self._log(message)
        self._update_status()
        
        if not success:
            self._show_message("Mount-Fehler", message, Gtk.MessageType.ERROR)
    
    def _on_unmount(self, button):
        """Handle unmount button click"""
        password = self.password_entry.get_text() or self.backend.get_nfs_password()
        
        self._log("Unmounte NFS...")
        success, message = self.backend.unmount_nfs(password)
        
        self._log(message)
        self._update_status()
        
        if not success:
            self._show_message("Unmount-Fehler", message, Gtk.MessageType.ERROR)
    
    def _on_set_password(self, button):
        """Save password to keyring"""
        password = self.password_entry.get_text()
        
        if not password:
            self._show_message("Fehler", "Bitte Passwort eingeben", Gtk.MessageType.WARNING)
            return
        
        if self.backend.set_nfs_password(password):
            self._log("Passwort gespeichert")
            self.password_entry.set_text("")
            self._show_message("Erfolg", "Passwort gespeichert", Gtk.MessageType.INFO)
        else:
            self._show_message("Fehler", "Passwort speichern fehlgeschlagen", Gtk.MessageType.ERROR)
    
    def _on_clear_password(self, button):
        """Clear saved password"""
        self.backend.clear_nfs_password()
        self._log("✅ Gespeichertes Passwort gelöscht")
        self._show_message("Erfolg", "Gespeichertes Passwort wurde gelöscht", Gtk.MessageType.INFO)
    
    def _on_folder_toggled(self, renderer, path):
        """Handle folder enabled toggle"""
        self.folder_store[path][0] = not self.folder_store[path][0]
        local_path = self.folder_store[path][1]
        self.backend.toggle_folder_enabled(local_path)
    
    def _on_add_folder(self, button):
        """Handle add folder button click"""
        dialog = Gtk.Dialog(
            title="Ordnerpaar hinzufügen",
            parent=self,
            flags=Gtk.DialogFlags.MODAL
        )
        
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        
        content = dialog.get_content_area()
        content.set_border_width(10)
        content.set_spacing(10)
        
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        content.pack_start(grid, True, True, 0)
        
        # Local folder
        grid.attach(Gtk.Label(label="Lokaler Ordner:", xalign=0), 0, 0, 1, 1)
        
        local_box = Gtk.Box(spacing=5)
        grid.attach(local_box, 1, 0, 1, 1)
        
        local_entry = Gtk.Entry()
        local_entry.set_width_chars(40)
        local_box.pack_start(local_entry, True, True, 0)
        
        local_button = Gtk.Button(label="Durchsuchen")
        local_box.pack_start(local_button, False, False, 0)
        
        def on_choose_local(btn):
            chooser = Gtk.FileChooserDialog(
                title="Lokalen Ordner wählen",
                parent=dialog,
                action=Gtk.FileChooserAction.SELECT_FOLDER
            )
            chooser.add_buttons(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK
            )
            
            response = chooser.run()
            if response == Gtk.ResponseType.OK:
                local_entry.set_text(chooser.get_filename())
            chooser.destroy()
        
        local_button.connect("clicked", on_choose_local)
        
        # Target folder
        grid.attach(Gtk.Label(label="Ziel auf NFS:", xalign=0), 0, 1, 1, 1)
        
        target_box = Gtk.Box(spacing=5)
        grid.attach(target_box, 1, 1, 1, 1)
        
        target_entry = Gtk.Entry()
        target_entry.set_width_chars(40)
        target_entry.set_placeholder_text("backup/documents")
        target_box.pack_start(target_entry, True, True, 0)
        
        target_button = Gtk.Button(label="Durchsuchen")
        target_box.pack_start(target_button, False, False, 0)
        
        def on_choose_target(btn):
            if not self.backend.is_nfs_mounted():
                self._show_message("Fehler", "NFS muss gemountet sein!", Gtk.MessageType.ERROR)
                return
            
            mount_point = self.backend.config.get('nfs_mount', '')
            
            chooser = Gtk.FileChooserDialog(
                title="Zielordner auf NFS wählen",
                parent=dialog,
                action=Gtk.FileChooserAction.SELECT_FOLDER
            )
            chooser.add_buttons(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK
            )
            
            chooser.set_current_folder(mount_point)
            
            response = chooser.run()
            if response == Gtk.ResponseType.OK:
                selected = chooser.get_filename()
                relative = Path(selected).relative_to(mount_point)
                target_entry.set_text(str(relative))
            chooser.destroy()
        
        target_button.connect("clicked", on_choose_target)
        
        content.show_all()
        
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            local_path = local_entry.get_text()
            target_path = target_entry.get_text()
            
            if local_path and target_path:
                success, message = self.backend.add_sync_folder(local_path, target_path)
                
                if success:
                    self._update_folder_list()
                
                msg_type = Gtk.MessageType.INFO if success else Gtk.MessageType.ERROR
                self._show_message("Ordnerpaar", message, msg_type)
        
        dialog.destroy()
    
    def _on_remove_folder(self, button):
        """Handle remove folder button click"""
        selection = self.folder_view.get_selection()
        model, tree_iter = selection.get_selected()
        
        if not tree_iter:
            self._show_message("Fehler", "Bitte Ordner auswählen", Gtk.MessageType.WARNING)
            return
        
        local_path = model[tree_iter][1]
        success, message = self.backend.remove_sync_folder(local_path)
        
        if success:
            self._update_folder_list()
        
        msg_type = Gtk.MessageType.INFO if success else Gtk.MessageType.ERROR
        self._show_message("Ordner entfernen", message, msg_type)
    
    def _on_sync_clicked(self, button):
        """Handle sync/stop button click"""
        if self.is_syncing:
            # Stop sync
            self._log("\n🛑 Stoppe Synchronisation...")
            self.backend.stop_sync_process()
            self.sync_button.set_label("🚀 Sync starten")
            self.is_syncing = False
        else:
            # Start sync
            self.is_syncing = True
            self.sync_button.set_label("🛑 STOP")
            
            self._log("=== SYNC GESTARTET ===\n")
            
            def progress_callback(message):
                self._log(message)
            
            def finished_callback(success, message):
                GLib.idle_add(self._on_sync_finished, success, message)
            
            self.backend.sync_all(progress_callback, finished_callback)
    
    def _on_sync_finished(self, success, message):
        """Handle sync finished"""
        self.is_syncing = False
        self.sync_button.set_label("🚀 Sync starten")
        
        self._log(f"\n=== SYNC BEENDET ===")
        self._log(message)
        
        msg_type = Gtk.MessageType.INFO if success else Gtk.MessageType.ERROR
        self._show_message("Sync", message, msg_type)
        
        return False
    
    def _on_open_settings(self, button):
        """Open settings dialog"""
        dialog = SettingsDialog(self, self.backend)
        dialog.run()
        dialog.destroy()
    
    def _show_message(self, title, message, msg_type):
        """Show message dialog"""
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            type=msg_type,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()


if __name__ == "__main__":
    app = NFSSyncGUI()
    app.show_all()
    Gtk.main()

