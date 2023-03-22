#!/usr/bin/env bash
mkdir -p ~/.config/terminator/plugins
mkdir -p ~/.config/terminator/themes
sudo ln -s "`pwd`"/plugin/terminator-themes-local.py ${HOME}/.config/terminator/plugins/terminator-themes-local.py
sudo ln -s "`pwd`"/themes.json ${HOME}/.config/terminator/themes/terminator-themes.json

echo "Please reopen Terminator for all changes to take effect"