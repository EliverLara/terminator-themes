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
   
        dbox = Gtk.Dialog(
                        _("Terminator themes"),
                        None,
                        Gtk.DialogFlags.MODAL,
                        (
                            
                            _("_Close"), Gtk.ResponseType.ACCEPT
                        )
                        )

        self.liststore = Gtk.ListStore(str, bool)

        profiles_from_repo = []
        response = requests.get(self.base_url)
        
        if response.status_code != 200:
            gerr(_("Failed to get list of available themes"))
            return

        for repo in response.json():
            profiles_from_repo.append(repo['name'])
        
       
        profiles = self.terminal.config.list_profiles()

        # Set add/remove buttons availability
        for profile in profiles_from_repo:
            profile = profile.split(".")
            if profile[0] in profiles:
                self.liststore.append([profile[0], False])
            else:
                self.liststore.append([profile[0], True])
        

        treeview = Gtk.TreeView(self.liststore)

        selection = treeview.get_selection()
       
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        selection.connect("changed", self.on_selection_changed, ui)
        ui['treeview'] = treeview

        renderer_text = Gtk.CellRendererText()
        column_text = Gtk.TreeViewColumn("Theme", renderer_text, text=0)
        treeview.append_column(column_text)


        scroll_window = Gtk.ScrolledWindow()
        scroll_window.set_size_request(500, 250)
        scroll_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_window.add_with_viewport(treeview)

        hbox = Gtk.HBox()
        hbox.pack_start(scroll_window, True, True, 0)
        dbox.vbox.pack_start(hbox, True, True, 0)

        button_box = Gtk.VBox()
        
        button = Gtk.Button(_("Install"))
        button_box.pack_start(button, False, True, 0)
        button.connect("clicked", self.on_install, ui) 
        button.set_sensitive(False)
        ui['button_install'] = button

        button = Gtk.Button(_("Remove"))
        button_box.pack_start(button, False, True, 0)
        button.connect("clicked", self.on_uninstall, ui) 
        button.set_sensitive(False)
        ui['button_uninstall'] = button

        hbox.pack_start(button_box, False, True, 0)
        self.dbox = dbox
        dbox.show_all()
        res = dbox.run()
        if res == Gtk.ResponseType.ACCEPT:
            self.terminal.config.save()
        del(self.dbox)
        dbox.destroy()
        return

   
    def on_selection_changed(self, selection, data=None):
        (model, iter) = selection.get_selected()
        data['button_install'].set_sensitive(model[iter][1])
        data['button_uninstall'].set_sensitive(model[iter][1] is not True)

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

        #'Add' button available again
        self.liststore.set_value(iter, 1, True)
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

        # Creates a new profile and overwrites the default colors for the new theme
        self.terminal.config.add_profile(target) 
        target_data = self.make_dictionary(response.content)
        for k, v in target_data.items():
            if k != 'background_image':
                 self.config_base.set_item(k, v[1:-1], target)

        self.terminal.force_set_profile(widget, target)
        self.terminal.config.save()

        # "Remove" button available again
        self.liststore.set_value(iter, 1, False)
        self.on_selection_changed(selection, data)
        treeview.set_enable_tree_lines(True)

    def make_dictionary(self, data):
        arr = []
        out_dict = {}
        for line in data.split("\n"):
            arr.append(line.split("="))

        for item in arr:
            if len(item) > 1:
                out_dict[item[0].strip()] = item[1].strip()

        return out_dict
