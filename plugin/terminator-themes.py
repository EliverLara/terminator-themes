import requests
import terminatorlib.plugin as plugin
from gi.repository import Gtk
from terminatorlib.config import ConfigBase
from terminatorlib.translation import _
from terminatorlib.util import get_config_dir, err, dbg, gerr

AVAILABLE = ['TerminatorThemes']

class TerminatorThemes(plugin.Plugin):

    capabilities = ['terminal_menu']
    config_base = ConfigBase()
    base_url = 'https://api.github.com/repos/EliverLara/terminator-themes/contents/schemes'
    inherits_config_from = "default"

    def callback(self, menuitems, menu, terminal):
        """Add our item to the menu"""
        self.terminal = terminal
        item = Gtk.ImageMenuItem(Gtk.STOCK_FIND)
        item.connect('activate',self.configure)
        item.set_label("Themes")
        item.set_sensitive(True)
        menuitems.append(item)

    def configure(self, widget, data = None):
        ui = {}
        dbox = Gtk.Dialog( _("Terminator themes"), None, Gtk.DialogFlags.MODAL)

        self.profiles_from_repo = []
        response = requests.get(self.base_url)
        
        if response.status_code != 200:
            gerr(_("Failed to get list of available themes"))
            return

        for repo in response.json():
            self.profiles_from_repo.append(repo['name'])
        
        self.profiles = self.terminal.config.list_profiles()

        main_container = Gtk.HBox(spacing=7)
        main_container.pack_start(self._create_themes_list(ui), True, True, 0)
        main_container.pack_start(self._create_settings_grid(ui), True, True, 0)
        dbox.vbox.pack_start(main_container, True, True, 0)

        self.dbox = dbox
        dbox.show_all()
        res = dbox.run()

        if res == Gtk.ResponseType.ACCEPT:
            self.terminal.config.save()

        del(self.dbox)
        dbox.destroy()
        return

    def _create_themes_list(self, ui):
        profiles_list_model = Gtk.ListStore(str, bool)
        # Set add/remove buttons availability
        for profile in self.profiles_from_repo:
            profile = profile.split(".")
            if profile[0] in self.profiles:
                profiles_list_model.append([profile[0], False])
            else:
                profiles_list_model.append([profile[0], True])
        
        treeview = Gtk.TreeView(profiles_list_model)

        selection = treeview.get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        selection.connect("changed", self.on_selection_changed, ui)
        ui['treeview'] = treeview

        renderer_text = Gtk.CellRendererText()
        column_text = Gtk.TreeViewColumn("Theme", renderer_text, text=0)
        treeview.append_column(column_text)

        scroll_window = Gtk.ScrolledWindow()
        scroll_window.set_size_request(300, 250)
        scroll_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_window.add_with_viewport(treeview)

        return scroll_window

    def _create_settings_grid(self, ui):
        grid = Gtk.Grid()
        grid.set_column_spacing(5)
        grid.set_row_spacing(7)
        grid.attach(self._create_default_inherits_check(ui), 0, 0, 2, 1)
        grid.attach(Gtk.Label("Available profiles: "), 0, 1, 1, 1)
        grid.attach(self._create_inherits_from_combo(ui), 1, 1, 1, 1)
        grid.attach(self._create_main_action_button(ui, "install", self.on_install), 0, 4, 1, 1)
        grid.attach(self._create_main_action_button(ui, "remove", self.on_uninstall), 1, 4, 1, 1)

        return grid

    def _create_default_inherits_check(self, ui):
        check = Gtk.CheckButton("Inherit preferences from default profile")
        check.set_active(True)
        check.connect("toggled", self.on_inheritsfromdefaultcheck_toggled, ui)
        ui['check_inherits_from_default'] = check
        
        return check

    def _create_inherits_from_combo(self, ui):
        combo = Gtk.ComboBoxText()
        combo.set_entry_text_column(0)
        combo.set_sensitive(False)
        combo.connect("changed", self.on_inheritsfromcombo_changed, ui)
        ui['inherits_from_combo'] = combo

        for profile in self.profiles:
            combo.append_text(profile)

        combo.set_active(self.profiles.index(self.terminal.config.get_profile()))

        return combo
    
    def _create_main_action_button(self, ui, label, action):
        btn = Gtk.Button(_(label.capitalize()))
        btn.connect("clicked", action, ui) 
        btn.set_sensitive(False)
        ui['button_' + label] = btn

        return btn

    def  on_inheritsfromdefaultcheck_toggled(self, check, data=None):
        if check.get_active() is not True:
            data["inherits_from_combo"].set_sensitive(True)
            self.inherits_config_from = self.profiles[data['inherits_from_combo'].get_active()]
        else:
            data["inherits_from_combo"].set_sensitive(False)
            self.inherits_config_from = 'default'
        
    def  on_inheritsfromcombo_changed(self, combo, data):
        if combo.get_sensitive():    
            self.inherits_config_from = self.profiles[combo.get_active()]
        else:
            self.inherits_config_from = 'default'

    def on_selection_changed(self, selection, data=None):
        (model, iter) = selection.get_selected()
        data['button_install'].set_sensitive(model[iter][1])
        data['button_remove'].set_sensitive(model[iter][1] is not True)

    def on_uninstall(self, button, data):
        treeview = data['treeview']
        selection = treeview.get_selection()
        (store, iter) = selection.get_selected()
        target = store[iter][0]

        # If selected theme is active, sets terminal profile to default before unistalling
        if self.terminal.get_profile() == target:
            widget = self.terminal.get_vte()
            self.terminal.force_set_profile(widget, 'default')

        self.terminal.config.del_profile(target)
        self.terminal.config.save()
        self.update_comboInheritsFrom(data)

        #'Add' button available again
        data['treeview'].get_model().set_value(iter, 1, True)
        self.on_selection_changed(selection, data)

    def on_install(self, button, data):
        treeview = data['treeview']
        selection = treeview.get_selection()
        (store, iter) = selection.get_selected()
        target = store[iter][0]
        widget = self.terminal.get_vte()
        treeview.set_enable_tree_lines(False)
        
        if not iter:
            return

        headers = { "Accept": "application/vnd.github.v3.raw" }
        response = requests.get(self.base_url+ '/' + target + '.config', headers=headers)
       
        if response.status_code != 200:
            gerr(_("Failed to download selected theme"))
            return

        # creates a new profile and overwrites the default colors for the new theme
        self.terminal.config.add_profile(target) 
        target_data = self.make_dictionary(response.content)
        template_data = self.config_base.profiles[self.inherits_config_from].copy()
      
        for k, v in target_data.items():
            if k == 'background_darkness':
                template_data[k] = float(v)
            elif k == 'background_type':
                template_data[k] = v
            else:
                template_data[k] = v[1:-1]

        for k, v in template_data.items():
            if k != 'background_image':
                self.config_base.set_item(k, v, target)
                 
        self.terminal.force_set_profile(widget, target)
        self.terminal.config.save()
        self.update_comboInheritsFrom(data)
        
        # "Remove" button available again
        data['treeview'].get_model().set_value(iter, 1, False)
        self.on_selection_changed(selection, data)
        treeview.set_enable_tree_lines(True)

    def update_comboInheritsFrom(self, data):
        data['inherits_from_combo'].remove_all()
        profiles = self.terminal.config.list_profiles()
        for profile in profiles:
            data['inherits_from_combo'].append_text(profile)

        data['inherits_from_combo'].set_active(profiles.index(self.terminal.config.get_profile()))
        self.profiles = profiles

    def make_dictionary(self, data):
        arr = []
        out_dict = {}
        for line in data.split("\n"):
            arr.append(line.split("="))

        for item in arr:
            if len(item) > 1:
                out_dict[item[0].strip()] = item[1].strip()

        return out_dict