#!/usr/bin/env bash
mkdir -p ~/.config/terminator/plugins
sudo ln -s "`pwd`"/plugin/terminator-themes.py ${HOME}/.config/terminator/plugins/terminator-themes.py

echo "Please reopen Terminator for all changes to take effect"