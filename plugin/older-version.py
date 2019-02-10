import requests
import terminatorlib.plugin as plugin
import gtk as Gtk
from terminatorlib.config import ConfigBase
from terminatorlib.translation import _
from terminatorlib.util import get_config_dir, err, dbg, gerr

AVAILABLE = ['TerminatorThemes']

class TerminatorThemes(plugin.Plugin):

    capabilities = ['terminal_menu']
    config_base = ConfigBase()
    base_url = 'https://api.github.com/repos/EliverLara/terminator-themes/contents/themes.json'
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
        dbox = Gtk.Dialog(_("Terminator themes"), None, Gtk.DIALOG_MODAL)

        headers = { "Accept": "application/vnd.github.v3.raw" }
        response = requests.get(self.base_url, headers=headers)
        
        if response.status_code != 200:
            gerr(_("Failed to get list of available themes"))
            return
        
        self.themes_from_repo = response.json()["themes"]
        self.profiles = self.terminal.config.list_profiles()

        main_container = Gtk.HBox(spacing=5)
        main_container.pack_start(self._create_themes_list(ui), True, True)
        main_container.pack_start(self._create_settings_grid(ui), True, True, 0)
        dbox.vbox.pack_start(main_container, True, True)        

        self.dbox = dbox
        dbox.show_all()
        res = dbox.run()
        
        if res == Gtk.RESPONSE_ACCEPT:
            self.terminal.config.save()
        del(self.dbox)
        dbox.destroy()

        return

    def _create_themes_list(self, ui):
        liststore = Gtk.ListStore(str, bool, object)
        # Set add/remove buttons availability
        for theme in self.themes_from_repo:
            if theme["name"] in self.profiles:
                liststore.append([theme["name"], False, theme])
            else:
                liststore.append([theme["name"], True, theme])

        treeview = Gtk.TreeView(liststore)

        selection = treeview.get_selection()
        selection.set_mode(Gtk.SELECTION_SINGLE)
        selection.connect("changed", self.on_selection_changed, ui)
        ui['treeview'] = treeview

        renderer_text = Gtk.CellRendererText()
        column_text = Gtk.TreeViewColumn("Theme", renderer_text, text=0)
        treeview.append_column(column_text)

        scroll_window = Gtk.ScrolledWindow()
        scroll_window.set_size_request(300, 250)
        scroll_window.set_policy(Gtk.POLICY_AUTOMATIC, Gtk.POLICY_AUTOMATIC)
        scroll_window.add_with_viewport(treeview)

        return scroll_window

    def _create_settings_grid(self, ui):
        settings_grid = Gtk.VBox(spacing=7)
        settings_grid.set_homogeneous(False)
        settings_grid.pack_start(self._create_default_inherits_check(ui), False, True)
        settings_grid.pack_start(self._create_inherits_from_grid(ui), False, True)
        settings_grid.pack_start(self._create_main_actions_grid(ui), False, True)

        return settings_grid

    def _create_default_inherits_check(self, ui):
        check = Gtk.CheckButton("Inherits preferences from default profile")
        check.set_active(True)
        check.connect("toggled", self.on_inheritsfromdefaultcheck_toggled, ui)
        ui['check_inherits_from_default'] = check

        return check

    def _create_inherits_from_grid(self, ui):
        # Available themes to inherit combo
        combo_model = Gtk.ListStore(str)
        for profile in self.profiles:
            combo_model.append([profile])

        combo = Gtk.ComboBox()
        combo.set_model(combo_model)
        combo_renderer_text = Gtk.CellRendererText()
        combo.pack_start(combo_renderer_text, True)
        combo.add_attribute(combo_renderer_text, "text", 0)
        combo.set_sensitive(False)
        combo.connect("changed", self.on_inheritsfromcombo_changed, ui)
        ui['inherits_from_combo'] = combo
        combo.set_active(self.profiles.index(self.terminal.config.get_profile()))
         
        combo_grid = Gtk.HBox()
        combo_grid.pack_start(Gtk.Label("Available profiles: "), False, True)
        combo_grid.pack_start(combo, False, True)

        return combo_grid

    def _create_main_actions_grid(self, ui):
        # Install/Remove buttons grid
        main_actions_box = Gtk.HBox()
        main_actions_box.pack_start(self._create_main_action_button(ui, "install", self.on_install), True, True)
        main_actions_box.pack_start(self._create_main_action_button(ui, "remove", self.on_uninstall), True, True, 0)
        
        return main_actions_box

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

    def on_selection_changed(self,selection, data=None):
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

        data['inherits_from_combo'].set_active(self.profiles.index(target))
        self.update_comboInheritsFrom(data, 2)

        #'Add' button available again
        data["treeview"].get_model().set_value(iter, 1, True)
        self.on_selection_changed(selection, data)

    def on_install(self, button, data):
        treeview = data['treeview']
        selection = treeview.get_selection()
        (store, iter) = selection.get_selected()
        target = store[iter][2]
        widget = self.terminal.get_vte()
        treeview.set_enable_tree_lines(False)
        
        if not iter:
            return

        # Creates a new profile and overwrites the default colors for the new theme
        self.terminal.config.add_profile(target["name"]) 
        template_data = self.config_base.profiles[self.inherits_config_from].copy()
      
        for k, v in target.items():
            if k != 'background_image' and k != 'name' and k != 'type':
                if k == 'background_darkness':
                    template_data[k] = float(v)
                else:
                    template_data[k] = v

        for k, v in template_data.items():
            self.config_base.set_item(k, v, target["name"])
                 
        self.terminal.force_set_profile(widget, target["name"])
        self.terminal.config.save()
        self.update_comboInheritsFrom(data, 1, target["name"])
 
        # "Remove" button available again
        data["treeview"].get_model().set_value(iter, 1, False)
        self.on_selection_changed(selection, data)
        treeview.set_enable_tree_lines(True)

    def update_comboInheritsFrom(self, data, action=1, target=None):
        profiles = self.terminal.config.list_profiles()
        self.profiles = profiles
        data["inherits_from_combo"].get_model().clear()
        for profile in profiles:
            data["inherits_from_combo"].get_model().append([profile])

        data['inherits_from_combo'].set_active(profiles.index(self.terminal.config.get_profile()))