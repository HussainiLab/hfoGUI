import sys
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
#build_exe_options = {"packages": ["os"], "excludes": ["tkinter"]}

# GUI applications require a different base on Windows (the default is for a
# console application).

base = None
#if sys.platform == "win32":
#    base = "Win32GUI"

additional_imports = ['numpy.core._methods', 'numpy.lib.format', "matplotlib.backends.backend_tkagg",
                      'scipy.spatial']

packages = ['matplotlib', 'scipy', 'scipy.spatial']

setup(name="hfoGUIV2",
      version="1.0",
      description="Software designed to view .EEG and .EGF files created with Axona's data acquisition software.",
      options={"build_exe": {'packages': packages, 'includes': additional_imports}},
      executables=[Executable("hfoGUI.py", base=base)])