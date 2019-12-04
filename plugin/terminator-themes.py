import requests
import terminatorlib.plugin as plugin
from gi.repository import Gtk, Gdk
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
        main_container.pack_start(self._create_themes_grid(ui), True, True, 0) #Left column
        main_container.pack_start(self._create_settings_grid(ui), True, True, 0) #Right column
       
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

        (combo, search_entry) = self._create_filter_widgets(ui)

        grid.attach(search_entry, 0,0,2,1)
        grid.attach(combo, 2,0,1,1)
        grid.attach(scroll_window, 0, 1, 3, 10)

        return grid

    def _create_filter_widgets(self, ui):

        combo = Gtk.ComboBoxText()
        combo.set_entry_text_column(0)
        combo.connect("changed", self.on_filter_combo_changed)
        combo.append_text("Filter by type")

        for theme_type in ["light", "dark", "All"]:
            combo.append_text(theme_type)

        combo.set_active(0)

        search_entry = Gtk.SearchEntry(max_width_chars=30)
        search_entry.connect("search-changed", self.on_theme_search_changed, ui)    

        return [combo,search_entry]

    def _create_themes_list(self, ui):

        profiles_list_model = Gtk.ListStore(str, str,bool, object)
        # Set add/remove buttons availability
        for theme in self.themes_from_repo:
            if theme["name"] in self.profiles:
                profiles_list_model.append([theme["name"], theme["type"],False, theme])
            else:
                profiles_list_model.append([theme["name"], theme["type"],True, theme])

        self.current_filter_theme = None
        self.filter_type = "theme_type"
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
        grid.attach(self._create_default_inherits_check(ui), 0, 15, 2, 1)
        grid.attach(Gtk.Label("Available profiles: "), 0, 16, 1, 1)
        grid.attach(self._create_inherits_from_combo(ui), 1, 16, 1, 1)
        grid.attach(self._create_main_action_button(ui, "install", self.on_install), 0, 20, 1, 1)
        grid.attach(self._create_main_action_button(ui, "remove", self.on_uninstall), 1, 20, 1, 1)
        self.theme_preview = ThemePreview(self.themes_from_repo[0])
        grid.attach(self.theme_preview, 0, 10, 4, 2)

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

        combo.set_active(self.profiles.index(self.terminal.config.get_profile())) #set current terminal profile as current item

        return combo
    
    def _create_main_action_button(self, ui, label, action):
        btn = Gtk.Button(_(label.capitalize()))
        btn.connect("clicked", action, ui) 
        btn.set_sensitive(False)
        ui['button_' + label] = btn

        return btn

    def theme_filter_func(self, model, iter, data):
        if self.filter_type == "theme_type":
            return self.filter_by_theme_type(model, iter, data)
        else:
            return self.filter_by_theme_search(model, iter, data)

    def filter_by_theme_search(self, model, iter, data):
        return model[iter][0].lower().find(self.current_filter_theme) > -1

    def filter_by_theme_type(self, model, iter, data):
        if self.current_filter_theme is None or self.current_filter_theme == "All":
            return True
        else:
            return model[iter][1] == self.current_filter_theme

    def on_theme_search_changed(self, widget, ui):
        self.filter_type = "theme_search"
        self.current_filter_theme = widget.get_text()
        self.theme_filter.refilter()

    def on_filter_combo_changed(self, widget):

        if widget.get_active() == 0:
            self.current_filter_theme = None
        else:
            self.current_filter_theme = widget.get_active_text()

        self.filter_type = "theme_type"

        # #we update the filter, which updates in turn the view
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
        self.theme_preview.update_preview(model[iter][3])

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

class ThemePreview(Gtk.VBox):
    def __init__(self, theme):
        Gtk.VBox.__init__(self)

        self.theme = theme
        self.palette_preview_colors = list()
        self.prompt_line = {}

        self.pack_start (self._create_preview_margin(), True, True,0)
        self.pack_start (self._create_palette_preview(), False,False,0)
        self.pack_start (self._create_preview_margin(), True, True,0)
        self.pack_start (self._create_prompt_line(), True, True,0)

        self.update_preview(self.theme)

    def _create_palette_preview(self):
        palette_preview = Gtk.FlowBox()
        palette_preview.set_min_children_per_line(10)
        palette_preview.set_max_children_per_line(10)
        palette_preview.set_selection_mode(Gtk.SelectionMode.NONE)

        palette_preview.add(Gtk.VBox())

        for color in self.theme['palette'].split(":")[0:8]:
            area = Gtk.DrawingArea()
            area.set_size_request(20, 25)
            color_preview = Gtk.VBox()
            color_preview.pack_start(area, False,False,0)
            color_preview.modify_bg(0, color = Gdk.color_parse(color)) 
           
            self.palette_preview_colors.append(color_preview)

            palette_preview.add(color_preview)

        palette_preview.add(Gtk.VBox())

        return palette_preview

    def _create_prompt_line(self):
        line = Gtk.HBox()

        self.prompt_line["prompt"] = Gtk.Label("  ~> ")
        self.prompt_line["cmd"] = Gtk.Label("echo ")
        self.prompt_line["arg"] = Gtk.Label("\"nice\" ")

        line.pack_start(self.prompt_line["prompt"],False,True,0)
        line.pack_start(self.prompt_line["cmd"],False,True,0)
        line.pack_start(self.prompt_line["arg"],False,True,0)

        return line

    def _create_preview_margin(self):
        area = Gtk.DrawingArea()
        area.set_size_request(270, 50)

        return area

    def update_preview(self, new_theme):
        self.modify_bg(0, color = Gdk.color_parse(new_theme['background_color'])) 
        self.update_palette_preview(new_theme['palette'])
        self.update_prompt_line_colors(new_theme['palette'])
 
    def update_palette_preview(self, palette):
        for i,color in enumerate(palette.split(":")[0:8]):
            self.palette_preview_colors[i].modify_bg(0,color = Gdk.color_parse(color)) 
            
    def update_prompt_line_colors(self, palette):
        palette = palette.split(":")
        self.prompt_line["prompt"].modify_fg(0,color = Gdk.color_parse(palette[6])) 
        self.prompt_line["cmd"].modify_fg(0,color = Gdk.color_parse(palette[3])) 
        self.prompt_line["arg"].modify_fg(0,color = Gdk.color_parse(palette[2])) 