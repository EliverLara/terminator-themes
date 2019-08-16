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
        dbox = Gtk.Dialog( _("Terminator themes"), None, Gtk.DialogFlags.MODAL)
        
        headers = { "Accept": "application/vnd.github.v3.raw" }
        response = requests.get(self.base_url, headers=headers)

        if response.status_code != 200:
            gerr(_("Failed to get list of available themes"))
            return
        
        self.themes_from_repo = response.json()["themes"]
        self.profiles = self.terminal.config.list_profiles()

        main_container = Gtk.HBox(spacing=5)
        main_container.pack_start(self._create_themes_grid(ui), True, True, 0)
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

    def _create_themes_grid(self, ui):
        grid = Gtk.Grid()
        grid.set_column_spacing(5)
        grid.set_row_spacing(7)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)

        scroll_window = self._create_themes_list(ui)

        #creating buttons to filter by theme type, and setting up their events
        buttons = list()
        for theme_type in ["light", "dark", "None"]:
            button = Gtk.Button(theme_type)
            buttons.append(button)
            button.connect("clicked", self.on_filter_button_clicked)

        grid.attach(scroll_window, 0, 0, 4, 10)
        grid.attach_next_to(buttons[0], scroll_window, Gtk.PositionType.BOTTOM, 1, 1)

        for i, button in enumerate(buttons[1:]):
            grid.attach_next_to(button, buttons[i], Gtk.PositionType.RIGHT, 1, 1)

        return grid

    def _create_themes_list(self, ui):

        profiles_list_model = Gtk.ListStore(str, str,bool, object)
        # Set add/remove buttons availability
        for theme in self.themes_from_repo:
            if theme["name"] in self.profiles:
                profiles_list_model.append([theme["name"], theme["type"],False, theme])
            else:
                profiles_list_model.append([theme["name"], theme["type"],True, theme])

        self.current_filter_theme = None
        self.theme_filter = profiles_list_model.filter_new()
        self.theme_filter.set_visible_func(self.theme_filter_func)
        
        treeview = Gtk.TreeView.new_with_model(self.theme_filter)

        selection = treeview.get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        selection.connect("changed", self.on_selection_changed, ui)
        ui['treeview'] = treeview

        for i, column_title in enumerate(["Theme", "Type"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            treeview.append_column(column)

        scroll_window = Gtk.ScrolledWindow()
        scroll_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_window.add(treeview)

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

    def theme_filter_func(self, model, iter, data):
        """Tests if the theme in the row is the one in the filter"""
        if self.current_filter_theme is None or self.current_filter_theme == "None":
            return True
        else:
            return model[iter][1] == self.current_filter_theme

    def on_filter_button_clicked(self, widget):
        """Called on any of the button clicks"""
        #we set the current theme filter to the button's label
        self.current_filter_theme = widget.get_label()

        #we update the filter, which updates in turn the view
        self.theme_filter.refilter()


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
        data['button_install'].set_sensitive(model[iter][2])
        data['button_remove'].set_sensitive(model[iter][2] is not True)

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
        data['treeview'].get_model().set_value(iter, 2, True)
        self.on_selection_changed(selection, data)

    def on_install(self, button, data):
        treeview = data['treeview']
        selection = treeview.get_selection()
        (store, iter) = selection.get_selected()
        target = store[iter][3]
        widget = self.terminal.get_vte()
        treeview.set_enable_tree_lines(False)
        
        if not iter:
            return

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
        self.update_comboInheritsFrom(data)

        # "Remove" button available again
        data['treeview'].get_model().set_value(iter, 2, False)
        self.on_selection_changed(selection, data)
        treeview.set_enable_tree_lines(True)

    def update_comboInheritsFrom(self, data):
        data['inherits_from_combo'].remove_all()
        profiles = self.terminal.config.list_profiles()
        self.profiles = profiles
        for profile in profiles:
            data['inherits_from_combo'].append_text(profile)

        data['inherits_from_combo'].set_active(profiles.index(self.terminal.config.get_profile()))