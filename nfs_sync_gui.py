#!/usr/bin/env python3
"""
NFS Sync Manager GUI
GTK3-based graphical interface for NFS synchronization
"""



import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import threading
from pathlib import Path
from nfs_sync_backend import NFSSyncBackend


class NFSSyncGUI(Gtk.Window):
    """Main GUI window for NFS Sync Manager"""
    
    def __init__(self):
        """Initialize the GUI window"""
        super().__init__(title="NFS Sync Manager")
        self.set_default_size(800, 600)
        self.set_border_width(10)
        
        self.backend = NFSSyncBackend()
        
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(main_box)
        
        # Notebook (Tabs)
        notebook = Gtk.Notebook()
        main_box.pack_start(notebook, True, True, 0)
        
        # Create tabs
        notebook.append_page(self._create_connection_tab(), Gtk.Label(label="Verbindung"))
        notebook.append_page(self._create_sync_tab(), Gtk.Label(label="Synchronisation"))
        notebook.append_page(self._create_settings_tab(), Gtk.Label(label="Einstellungen"))
        
        # Status bar
        self.statusbar = Gtk.Statusbar()
        main_box.pack_start(self.statusbar, False, False, 0)
        self.statusbar.push(1, "Bereit")
        
        # Initial update
        self._update_mount_status()
    
    def _show_password_dialog(self, allow_save=True):
        """
        Show password dialog
        
        Args:
            allow_save (bool): Show save checkbox
            
        Returns:
            tuple: (password: str or None, save: bool)
        """
        dialog = Gtk.Dialog(
            title="Sudo-Passwort",
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
        
        label = Gtk.Label()
        label.set_markup("Bitte gib dein <b>Sudo-Passwort</b> ein:")
        content.pack_start(label, False, False, 0)
        
        password_entry = Gtk.Entry()
        password_entry.set_visibility(False)
        password_entry.set_invisible_char('●')
        password_entry.set_activates_default(True)
        content.pack_start(password_entry, False, False, 0)
        
        save_check = None
        if allow_save:
            save_check = Gtk.CheckButton(label="Passwort speichern (verschlüsselt)")
            content.pack_start(save_check, False, False, 0)
        
        dialog.set_default_response(Gtk.ResponseType.OK)
        content.show_all()
        
        response = dialog.run()
        password = password_entry.get_text()
        save = save_check.get_active() if save_check else False
        
        dialog.destroy()
        
        if response == Gtk.ResponseType.OK and password:
            return password, save
        return None, False
    
    def _create_connection_tab(self):
        """Create the connection configuration tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)
        
        # NFS Configuration
        nfs_frame = Gtk.Frame(label="NFS-Konfiguration")
        box.pack_start(nfs_frame, False, False, 0)
        
        nfs_grid = Gtk.Grid()
        nfs_grid.set_border_width(10)
        nfs_grid.set_row_spacing(10)
        nfs_grid.set_column_spacing(10)
        nfs_frame.add(nfs_grid)
        
        # Server
        nfs_grid.attach(Gtk.Label(label="Server:", xalign=0), 0, 0, 1, 1)
        self.server_entry = Gtk.Entry()
        self.server_entry.set_text(self.backend.config.get('nfs_server', ''))
        self.server_entry.set_placeholder_text("192.168.1.100")
        nfs_grid.attach(self.server_entry, 1, 0, 1, 1)
        
        # Share
        nfs_grid.attach(Gtk.Label(label="Share:", xalign=0), 0, 1, 1, 1)
        self.share_entry = Gtk.Entry()
        self.share_entry.set_text(self.backend.config.get('nfs_share', ''))
        self.share_entry.set_placeholder_text("/volume1/homes")
        nfs_grid.attach(self.share_entry, 1, 1, 1, 1)
        
        # Mount Point
        nfs_grid.attach(Gtk.Label(label="Mount-Point:", xalign=0), 0, 2, 1, 1)
        self.mount_entry = Gtk.Entry()
        self.mount_entry.set_text(self.backend.config.get('mount_point', '/mnt/unaspro'))
        nfs_grid.attach(self.mount_entry, 1, 2, 1, 1)
        
        # Test Button
        test_button = Gtk.Button(label="Verbindung testen")
        test_button.connect("clicked", self._on_test_connection)
        nfs_grid.attach(test_button, 0, 3, 2, 1)
        
        # Save NFS Config Button
        save_nfs_button = Gtk.Button(label="NFS-Konfiguration speichern")
        save_nfs_button.connect("clicked", self._on_save_nfs_config)
        nfs_grid.attach(save_nfs_button, 0, 4, 2, 1)
        
        # Mount Status
        status_frame = Gtk.Frame(label="Status")
        box.pack_start(status_frame, False, False, 0)
        
        status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        status_box.set_border_width(10)
        status_frame.add(status_box)
        
        self.mount_status_label = Gtk.Label()
        status_box.pack_start(self.mount_status_label, False, False, 0)
        
        # Mount buttons
        button_box = Gtk.Box(spacing=5)
        status_box.pack_start(button_box, False, False, 0)
        
        self.mount_button = Gtk.Button(label="Verbinden")
        self.mount_button.connect("clicked", self._on_mount)
        button_box.pack_start(self.mount_button, True, True, 0)
        
        self.unmount_button = Gtk.Button(label="Trennen")
        self.unmount_button.connect("clicked", self._on_unmount)
        button_box.pack_start(self.unmount_button, True, True, 0)
        
        return box
    
    def _create_sync_tab(self):
        """Create the synchronization tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)
        
        # Folder pairs section
        folders_frame = Gtk.Frame(label="Sync-Ordner")
        box.pack_start(folders_frame, True, True, 0)
        
        folders_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        folders_box.set_border_width(10)
        folders_frame.add(folders_box)
        
        # Scrolled window for folder list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(200)
        folders_box.pack_start(scrolled, True, True, 0)
        
        self.folders_liststore = Gtk.ListStore(str, str)
        self.folders_treeview = Gtk.TreeView(model=self.folders_liststore)
        
        renderer = Gtk.CellRendererText()
        column1 = Gtk.TreeViewColumn("Lokaler Ordner", renderer, text=0)
        column1.set_expand(True)
        self.folders_treeview.append_column(column1)
        
        column2 = Gtk.TreeViewColumn("Ziel-Ordner", renderer, text=1)
        column2.set_expand(True)
        self.folders_treeview.append_column(column2)
        
        scrolled.add(self.folders_treeview)
        
        # Buttons
        folder_buttons = Gtk.Box(spacing=5)
        folders_box.pack_start(folder_buttons, False, False, 0)
        
        add_folder_button = Gtk.Button(label="Ordner hinzufügen")
        add_folder_button.connect("clicked", self._on_add_folder)
        folder_buttons.pack_start(add_folder_button, True, True, 0)
        
        remove_folder_button = Gtk.Button(label="Ordner entfernen")
        remove_folder_button.connect("clicked", self._on_remove_folder)
        folder_buttons.pack_start(remove_folder_button, True, True, 0)
        
        # Sync section
        sync_frame = Gtk.Frame(label="Synchronisation")
        box.pack_start(sync_frame, False, False, 0)
        
        sync_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        sync_box.set_border_width(10)
        sync_frame.add(sync_box)
        
        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        sync_box.pack_start(self.progress_bar, False, False, 0)
        
        # Sync button
        self.sync_button = Gtk.Button(label="Jetzt synchronisieren")
        self.sync_button.connect("clicked", self._on_sync)
        sync_box.pack_start(self.sync_button, False, False, 0)
        
        # Last sync info
        self.last_sync_label = Gtk.Label()
        sync_box.pack_start(self.last_sync_label, False, False, 0)
        
        # Update displays
        self._update_folder_list()
        self._update_last_sync()
        
        return box
    
    def _create_settings_tab(self):
        """Create the settings tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)
        
        # Auto-mount
        self.auto_mount_check = Gtk.CheckButton(label="Automatisch beim Start mounten")
        self.auto_mount_check.set_active(self.backend.config.get('auto_mount', False))
        box.pack_start(self.auto_mount_check, False, False, 0)
        
        # Auto-sync
        self.auto_sync_check = Gtk.CheckButton(label="Automatische Synchronisation aktivieren")
        self.auto_sync_check.set_active(self.backend.config.get('auto_sync', False))
        box.pack_start(self.auto_sync_check, False, False, 0)
        
        # Sync interval
        interval_box = Gtk.Box(spacing=5)
        box.pack_start(interval_box, False, False, 0)
        
        interval_box.pack_start(Gtk.Label(label="Sync-Intervall (Minuten):"), False, False, 0)
        
        adjustment = Gtk.Adjustment(
            value=self.backend.config.get('sync_interval', 3600) / 60,
            lower=1,
            upper=1440,
            step_increment=1,
            page_increment=10
        )
        self.interval_spin = Gtk.SpinButton(adjustment=adjustment)
        interval_box.pack_start(self.interval_spin, False, False, 0)
        
        # Save button
        save_button = Gtk.Button(label="Einstellungen speichern")
        save_button.connect("clicked", self._on_save_settings)
        box.pack_start(save_button, False, False, 0)
        
        return box
    
    def _update_mount_status(self):
        """Update the mount status display"""
        is_mounted = self.backend.check_mount()
        
        if is_mounted:
            self.mount_status_label.set_markup("<span color='green'><b>✅ Verbunden</b></span>")
            self.mount_button.set_sensitive(False)
            self.unmount_button.set_sensitive(True)
        else:
            self.mount_status_label.set_markup("<span color='red'><b>❌ Nicht verbunden</b></span>")
            self.mount_button.set_sensitive(True)
            self.unmount_button.set_sensitive(False)
    
    def _update_folder_list(self):
        """Update the folder list display"""
        self.folders_liststore.clear()
        
        for local_path, target_path in self.backend.config.get('sync_folders', {}).items():
            self.folders_liststore.append([local_path, target_path])
    
    def _update_last_sync(self):
        """Update the last sync time display"""
        last_sync = self.backend.config.get('last_sync')
        
        if last_sync:
            self.last_sync_label.set_text(f"Letzte Synchronisation: {last_sync}")
        else:
            self.last_sync_label.set_text("Noch keine Synchronisation durchgeführt")
    
    def _on_test_connection(self, button):
        """Handle test connection button click"""
        server = self.server_entry.get_text()
        share = self.share_entry.get_text()
        
        self.statusbar.push(1, "Teste Verbindung...")
        button.set_sensitive(False)
        
        def test_thread():
            success, message = self.backend.test_nfs_connection(server, share)
            GLib.idle_add(self._on_test_complete, success, message, button)
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def _on_test_complete(self, success, message, button):
        """Handle test completion"""
        button.set_sensitive(True)
        self.statusbar.push(1, message)
        
        msg_type = Gtk.MessageType.INFO if success else Gtk.MessageType.ERROR
        self._show_message("Verbindungstest", message, msg_type)
        
        return False
    
    def _on_save_nfs_config(self, button):
        """Handle save NFS config button click"""
        self.backend.config['nfs_server'] = self.server_entry.get_text()
        self.backend.config['nfs_share'] = self.share_entry.get_text()
        self.backend.config['mount_point'] = self.mount_entry.get_text()
        
        success, message = self.backend.save_config()
        msg_type = Gtk.MessageType.INFO if success else Gtk.MessageType.ERROR
        self._show_message("Konfiguration", message, msg_type)
    
    def _on_mount(self, button):
        """Handle mount button click"""
        if not self.backend.get_sudo_password():
            password, save = self._show_password_dialog(allow_save=True)
            
            if not password:
                self._show_message("Abgebrochen", "Passwort erforderlich", Gtk.MessageType.WARNING)
                return
            
            self.backend.set_sudo_password(password, save=save)
        
        self.statusbar.push(1, "Verbinde...")
        button.set_sensitive(False)
        
        def mount_thread():
            success, message = self.backend.mount_nfs()
            GLib.idle_add(self._on_mount_complete, success, message, button)
        
        threading.Thread(target=mount_thread, daemon=True).start()
    
    def _on_mount_complete(self, success, message, button):
        """Handle mount completion"""
        button.set_sensitive(True)
        self.statusbar.push(1, message)
        self._update_mount_status()
        
        msg_type = Gtk.MessageType.INFO if success else Gtk.MessageType.ERROR
        self._show_message("Mount", message, msg_type)
        
        return False
    
    def _on_unmount(self, button):
        """Handle unmount button click"""
        self.statusbar.push(1, "Trenne...")
        button.set_sensitive(False)
        
        def unmount_thread():
            success, message = self.backend.unmount_nfs()
            GLib.idle_add(self._on_unmount_complete, success, message, button)
        
        threading.Thread(target=unmount_thread, daemon=True).start()
    
    def _on_unmount_complete(self, success, message, button):
        """Handle unmount completion"""
        button.set_sensitive(True)
        self.statusbar.push(1, message)
        self._update_mount_status()
        
        msg_type = Gtk.MessageType.INFO if success else Gtk.MessageType.ERROR
        self._show_message("Unmount", message, msg_type)
        
        return False
    
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
            
            if chooser.run() == Gtk.ResponseType.OK:
                local_entry.set_text(chooser.get_filename())
            
            chooser.destroy()
        
        local_button.connect("clicked", on_choose_local)
        
        # Target folder
        grid.attach(Gtk.Label(label="Ziel-Ordner:", xalign=0), 0, 1, 1, 1)
        target_entry = Gtk.Entry()
        target_entry.set_width_chars(40)
        target_entry.set_placeholder_text("backup/documents")
        grid.attach(target_entry, 1, 1, 1, 1)
        
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
        selection = self.folders_treeview.get_selection()
        model, treeiter = selection.get_selected()
        
        if treeiter:
            local_path = model[treeiter][0]
            
            success, message = self.backend.remove_sync_folder(local_path)
            
            if success:
                self._update_folder_list()
            
            msg_type = Gtk.MessageType.INFO if success else Gtk.MessageType.ERROR
            self._show_message("Ordnerpaar", message, msg_type)
        else:
            self._show_message("Fehler", "Kein Ordner ausgewählt", Gtk.MessageType.WARNING)
    
    def _on_sync(self, button):
        """Handle sync button click"""
        if not self.backend.check_mount():
            self._show_message("Fehler", "NFS nicht gemountet", Gtk.MessageType.ERROR)
            return
        
        button.set_sensitive(False)
        self.progress_bar.set_fraction(0)
        self.statusbar.push(1, "Synchronisiere...")
        
        def progress_callback(percent, message):
            GLib.idle_add(self._update_progress, percent / 100, message)
        
        def sync_thread():
            success, message, stats = self.backend.sync_folders(progress_callback)
            GLib.idle_add(self._on_sync_complete, success, message, stats, button)
        
        threading.Thread(target=sync_thread, daemon=True).start()
    
    def _update_progress(self, fraction, text):
        """Update progress bar"""
        self.progress_bar.set_fraction(fraction)
        self.progress_bar.set_text(text)
        return False
    
    def _on_sync_complete(self, success, message, stats, button):
        """Handle sync completion"""
        button.set_sensitive(True)
        self.progress_bar.set_fraction(1.0)
        self.progress_bar.set_text("Abgeschlossen")
        self.statusbar.push(1, message)
        self._update_last_sync()
        
        msg_type = Gtk.MessageType.INFO if success else Gtk.MessageType.ERROR
        
        if stats and stats.get('files_transferred', 0) > 0:
            message += f"\n\nDateien: {stats['files_transferred']}"
            if 'total_size' in stats:
                message += f"\nGröße: {stats['total_size']}"
        
        self._show_message("Synchronisation", message, msg_type)
        
        return False
    
    def _on_save_settings(self, button):
        """Handle save settings button click"""
        self.backend.config['auto_mount'] = self.auto_mount_check.get_active()
        self.backend.config['auto_sync'] = self.auto_sync_check.get_active()
        self.backend.config['sync_interval'] = int(self.interval_spin.get_value()) * 60
        
        success, message = self.backend.save_config()
        msg_type = Gtk.MessageType.INFO if success else Gtk.MessageType.ERROR
        self._show_message("Einstellungen", message, msg_type)
    
    def _show_message(self, title, message, msg_type):
        """Show a message dialog"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=msg_type,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()


def main():
    """Main entry point"""
    app = NFSSyncGUI()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()


if __name__ == '__main__':
    main()

