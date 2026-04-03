"""
FisTransfer — File Picker
============================
Gets the currently selected file/folder from Finder using AppleScript.
Supports both files and folders — folders are zipped before transfer.
"""

import json
import os
import shutil
import subprocess
import tempfile
import zipfile


class FilePicker:
    """Picks up files from Finder selection."""

    @staticmethod
    def get_selected_file():
        """
        Get the POSIX path of the currently selected item in Finder.

        Returns
        -------
        dict or None
            {"path": str, "name": str, "size": int, "is_dir": bool}
            None if nothing is selected.
        """
        script = '''
        tell application "Finder"
            set sel to selection
            if (count of sel) > 0 then
                set firstItem to item 1 of sel
                return POSIX path of (firstItem as alias)
            else
                return ""
            end if
        end tell
        '''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=3,
            )
            path = result.stdout.strip()

            if not path or not os.path.exists(path):
                return None

            is_dir = os.path.isdir(path)
            name = os.path.basename(path.rstrip("/"))

            if is_dir:
                size = _dir_size(path)
            else:
                size = os.path.getsize(path)

            return {
                "path": path,
                "name": name,
                "size": size,
                "is_dir": is_dir,
            }

        except (subprocess.TimeoutExpired, Exception) as e:
            print(f"[FilePicker] Error: {e}")
            return None

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
    folder_path = folder_path.rstrip("/")
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
