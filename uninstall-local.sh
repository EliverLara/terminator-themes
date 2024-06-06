#!/usr/bin/env bash
if [ -L /home/seanl/.config/terminator/plugins/terminator-themes-local.py ]; then
  unlink ${HOME}/.config/terminator/plugins/terminator-themes-local.py
fi

if [ -L /home/seanl/.config/terminator/themes/terminator-themes.json ]; then
  unlink ${HOME}/.config/terminator/themes/terminator-themes.json
fi

if [ -f ${HOME}/.config/terminator/plugins/__pycache__/terminator-themes-local.* ]; then
  rm ${HOME}/.config/terminator/plugins/__pycache__/terminator-themes-local.*
fi

if [ -d ${HOME}/.config/terminator/plugins/__pycache__ ]; then
  if [ "$(ls -A ${HOME}/.config/terminator/plugins/__pycache__)" ]; then
    echo "Other plugin pycache objects exist, not removing plugins pycache dir"
  else
    rmdir ${HOME}/.config/terminator/plugins/__pycache__
  fi
fi

if [ -d ${HOME}/.config/terminator/plugins ]; then
  if [ "$(ls -A ${HOME}/.config/terminator/plugins)" ]; then
    echo "Other plugins exist, not removing plugins dir"
  else
    rmdir ${HOME}/.config/terminator/plugins
  fi
fi

if [ -d ${HOME}/.config/terminator/themes ]; then
  if [ "$(ls -A ${HOME}/.config/terminator/themes)" ]; then
    echo "Other themes exist, not removing themes dir"
  else
    rmdir ${HOME}/.config/terminator/themes
  fi
fi

echo "Please reopen Terminator for all changes to take effect"