"""
FisTransfer — Windows File Picker
=====================================
Uses pywin32 COM interfaces to get the selected file from the active Windows Explorer window.
Supports both files and folders — folders are zipped before transfer.
"""

import os
import tempfile
import zipfile

# Conditional import to avoid crashing tools directly inspecting this file on Macs
try:
    import win32com.client
    import win32gui
    import pythoncom
    HAS_PYWIN32 = True
except ImportError as e:
    HAS_PYWIN32 = False
    print(f"[FilePicker] PyWin32 not available: {e}")


class FilePicker:
    """Picks up files from Windows Explorer selection."""

    @staticmethod
    def get_selected_file():
        """
        Get the path of the currently selected item in Windows Explorer.
        """
        if not HAS_PYWIN32:
            print("[FilePicker] Cannot pick file: pywin32 is not installed properly.")
            return None

        try:
            # Required for COM in threads
            pythoncom.CoInitialize()

            # The CLSID for ShellWindows collection
            clsid = '{9BA05972-F6A8-11CF-A442-00A0C90A8F39}'
            shell_windows = win32com.client.Dispatch(clsid)

            foreground_hwnd = win32gui.GetForegroundWindow()
            target_window = None

            # 1. Try to find if an Explorer window is currently active
            for i in range(shell_windows.Count):
                try:
                    w = shell_windows.Item(i)
                    if w and getattr(w, "HWND", 0) == foreground_hwnd:
                        target_window = w
                        break
                except Exception:
                    continue

            # 2. Fallback if the user clicked the console window after selecting:
            # Just grab the first available Explorer window.
            if not target_window and shell_windows.Count > 0:
                try:
                    target_window = shell_windows.Item(0)
                except Exception:
                    pass

            if not target_window:
                return None

            try:
                # Extract the Document object (the view inside the folder)
                doc = target_window.Document
                selected = doc.SelectedItems()
            except AttributeError:
                # Happens if the window is an Internet Explorer instance or misconfigured shell
                return None

            if selected.Count == 0:
                return None

            first_item = selected.Item(0)
            path = first_item.Path

            if not path or not os.path.exists(path):
                return None

            is_dir = first_item.IsFolder
            name = first_item.Name

            if is_dir:
                size = _dir_size(path)
            else:
                size = first_item.Size

            return {
                "path": path,
                "name": name,
                "size": size,
                "is_dir": is_dir,
            }

        except Exception as e:
            print(f"[FilePicker] Error accessing Windows COM: {e}")
            return None
        finally:
            if HAS_PYWIN32:
                pythoncom.CoUninitialize()

    @staticmethod
    def prepare_for_transfer(file_info):
        """
        Prepare a file for transfer. Folders are zipped.

        Returns
        -------
        dict
            {"transfer_path": str, "transfer_name": str, "transfer_size": int,
             "original_name": str, "is_zipped": bool, "cleanup_path": str or None}
        """
        if file_info["is_dir"]:
            # Zip the folder
            zip_name = f"{file_info['name']}.zip"
            zip_path = os.path.join(tempfile.gettempdir(), zip_name)

            print(f"[FilePicker] Zipping folder: {file_info['name']}...")
            _zip_directory(file_info["path"], zip_path)

            zip_size = os.path.getsize(zip_path)
            print(f"[FilePicker] Zipped: {zip_size / 1024 / 1024:.1f} MB")

            return {
                "transfer_path": zip_path,
                "transfer_name": zip_name,
                "transfer_size": zip_size,
                "original_name": file_info["name"],
                "is_zipped": True,
                "cleanup_path": zip_path,
            }
        else:
            return {
                "transfer_path": file_info["path"],
                "transfer_name": file_info["name"],
                "transfer_size": file_info["size"],
                "original_name": file_info["name"],
                "is_zipped": False,
                "cleanup_path": None,
            }

    @staticmethod
    def cleanup(prepared_info):
        """Remove temporary files (zipped folders)."""
        if prepared_info.get("cleanup_path"):
            try:
                os.remove(prepared_info["cleanup_path"])
            except OSError:
                pass


def _dir_size(path):
    """Calculate total size of a directory."""
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
    return total


def _zip_directory(folder_path, zip_path):
    """Zip a directory into a zip file."""
    # Ensure folder_path doesn't end with a slash so basename works
    folder_path = folder_path.rstrip("\\/")
    base_name = os.path.basename(folder_path)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_path):
            for f in files:
                file_path = os.path.join(root, f)
                arcname = os.path.join(
                    base_name,
                    os.path.relpath(file_path, folder_path),
                )
                zf.write(file_path, arcname)
