[app]

# title of your application
title = markdownwiki

# project root directory. default = The parent directory of input_file
project_dir = .

# source file entry point path. default = main.py
input_file = /home/pdelboca/Repos/markdown-wiki/main.py

# directory where the executable output is generated
exec_directory = dist

# path to the project file relative to project_dir
project_file = pyproject.toml

# application icon
icon = ./assets/icon.ico

[python]

# python path
python_path = /home/pdelboca/Repos/markdown-wiki/.venv/bin/python3

# python packages to install
packages = Nuitka==2.6.8

[qt]

# paths to required qml files. comma separated
# normally all the qml files required by the project are added automatically
qml_files = 

# excluded qml plugin binaries
excluded_qml_plugins = 

# qt modules used. comma separated
modules = Widgets,Core,DBus,Gui

# qt plugins used by the application. only relevant for desktop deployment
# for qt plugins used in android application see [android][plugins]
plugins = xcbglintegrations,iconengines,egldeviceintegrations,platformthemes,platforms/darwin,platforminputcontexts,styles,imageformats,platforms,generic,accessiblebridge

[nuitka]

# usage description for permissions requested by the app as found in the info.plist file
# of the app bundle. comma separated
# eg = extra_args = --show-modules --follow-stdlib
macos.permissions = 

# mode of using nuitka. accepts standalone or onefile. default = onefile
mode = standalone

# specify any extra nuitka arguments
extra_args = --quiet --noinclude-qt-translations

