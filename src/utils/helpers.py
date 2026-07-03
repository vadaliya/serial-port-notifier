import os
import sys

def get_resource_path(relative_path):
    """
    Get the absolute path to a resource.
    Works for standard local development and when compiled via PyInstaller.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # If not compiled, use the current working directory
        # (Assuming the app is run from the root 'serial-port-notifier' folder)
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)