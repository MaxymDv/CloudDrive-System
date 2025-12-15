import os
from PyQt6.QtCore import QThread, pyqtSignal


class SyncWorker(QThread):
    log = pyqtSignal(str)

    def __init__(self, api, folder):
        super().__init__()
        self.api = api
        self.folder = folder

    def run(self):
        self.log.emit("Sync started...")
        remote_files = self.api.get_files()
        remote_names = [f['filename'] for f in remote_files]

        local_files = os.listdir(self.folder)
        count = 0
        for f in local_files:
            path = os.path.join(self.folder, f)
            if os.path.isfile(path) and f not in remote_names:
                self.log.emit(f"Uploading new file: {f}")
                self.api.upload_file(path)
                count += 1

        self.log.emit(f"Sync finished. Uploaded {count} files.")