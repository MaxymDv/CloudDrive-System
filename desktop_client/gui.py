import os
import tempfile
import shutil
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTableWidget, QTableWidgetItem, QPushButton,
                             QLabel, QFileDialog, QComboBox, QCheckBox,
                             QInputDialog, QHeaderView, QSplitter, QTextEdit, QMessageBox, QAbstractItemView)
from PyQt6.QtGui import QColor, QBrush, QPixmap, QDragEnterEvent, QDropEvent, QDrag
from PyQt6.QtCore import Qt, QUrl, QMimeData
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest


class DraggableTable(QTableWidget):
    def __init__(self, parent_window):
        super().__init__()
        self.parent = parent_window
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.viewport().setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.source() == self: return
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files: self.parent.upload_file(files[0])

    def startDrag(self, supportedActions):
        row = self.currentRow()
        if row < 0: return
        name_item = self.item(row, 0)
        filename = name_item.text()
        storage_name = name_item.data(Qt.ItemDataRole.UserRole)
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, filename)
        try:
            import requests
            url = f"http://127.0.0.1:8000/raw/{storage_name}"
            r = requests.get(url, stream=True)
            if r.status_code == 200:
                with open(temp_path, 'wb') as f:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw, f)
            else:
                return
        except:
            return
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(temp_path)])
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)


class MainWindow(QMainWindow):
    def __init__(self, api, username, logout_callback):
        super().__init__()
        self.api = api
        self.username = username
        self.logout_callback = logout_callback
        self.raw_data = []
        self.current_storage_name = None

        self.net_man = QNetworkAccessManager()
        self.net_man.finished.connect(self.on_img_downloaded)

        self.setWindowTitle(f"Desktop Drive - {username}")
        self.resize(1200, 700)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        central = QWidget()
        main_layout = QVBoxLayout()

        #TOOLBAR
        toolbar = QHBoxLayout()
        btn_refresh = QPushButton("🔄 Refresh");
        btn_refresh.clicked.connect(self.load_data)
        btn_upload = QPushButton("⬆ Upload");
        btn_upload.clicked.connect(lambda: self.upload_file(None))
        btn_sync = QPushButton("⚙ Sync");
        btn_sync.clicked.connect(self.sync)

        self.btn_share = QPushButton("🤝 Share");
        self.btn_share.clicked.connect(self.share)
        self.btn_share.setEnabled(False)
        self.btn_download = QPushButton("⬇ Download");
        self.btn_download.clicked.connect(self.download_selected)
        self.btn_download.setEnabled(False)
        self.btn_delete = QPushButton("🗑 Delete");
        self.btn_delete.clicked.connect(self.delete_selected)
        self.btn_delete.setEnabled(False)

        self.combo_sort = QComboBox()
        self.combo_sort.addItems(["Default", "Uploader A-Z","Uploader Z-A"])
        self.combo_sort.currentIndexChanged.connect(self.apply_filter_sort)

        self.check_filter = QCheckBox("Filter: .py/.jpg")
        self.check_filter.stateChanged.connect(self.apply_filter_sort)

        self.check_cols = QCheckBox("Hide Cols")
        self.check_cols.stateChanged.connect(self.toggle_cols)

        btn_logout = QPushButton("Logout");
        btn_logout.clicked.connect(self.logout)
        btn_logout.setStyleSheet("background-color: #444; color: white;")

        toolbar.addWidget(btn_refresh);
        toolbar.addWidget(btn_upload)
        toolbar.addWidget(self.btn_download);
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_share);
        toolbar.addWidget(btn_sync)
        toolbar.addWidget(QLabel("|"));
        toolbar.addWidget(self.combo_sort)
        toolbar.addWidget(self.check_filter);
        toolbar.addWidget(self.check_cols)
        toolbar.addStretch();
        toolbar.addWidget(QLabel(f"User: {self.username}"));
        toolbar.addWidget(btn_logout)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # TABLE
        self.table = DraggableTable(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Name", "Ext", "Created", "Edited", "Uploader", "Editor"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.cellClicked.connect(self.on_file_click)

        # PREVIEW PANEL
        self.preview_panel = QWidget()
        p_layout = QHBoxLayout()
        header_layout = QHBoxLayout()

        # Кнопка збереження (прихована за замовчуванням)
        self.btn_save_changes = QPushButton("💾 Save Changes")
        self.btn_save_changes.setStyleSheet("background-color: #2E8B57; color: white; font-weight: bold;")
        self.btn_save_changes.clicked.connect(self.save_text_changes)
        self.btn_save_changes.hide()

        header_layout.addStretch()
        header_layout.addWidget(self.btn_save_changes)

        p_layout.addLayout(header_layout)

        # Елементи прев'ю
        self.lbl_preview_img = QLabel("Select a file")
        self.lbl_preview_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview_img.setWordWrap(True)

        self.txt_preview = QTextEdit()
        self.txt_preview.setReadOnly(True)
        self.txt_preview.hide()
        self.txt_preview.textChanged.connect(self.on_text_edited)

        p_layout.addWidget(self.lbl_preview_img)
        p_layout.addWidget(self.txt_preview)
        self.preview_panel.setLayout(p_layout)

        splitter.addWidget(self.table)
        splitter.addWidget(self.preview_panel)
        splitter.setSizes([800, 400])

        main_layout.addLayout(toolbar)
        main_layout.addWidget(splitter)
        central.setLayout(main_layout)
        self.setCentralWidget(central)

    def load_data(self):
        self.raw_data = self.api.get_files()
        self.apply_filter_sort()
        # Скидання
        self.btn_download.setEnabled(False);
        self.btn_delete.setEnabled(False);
        self.btn_share.setEnabled(False)
        self.lbl_preview_img.show();
        self.lbl_preview_img.setText("Select a file");
        self.lbl_preview_img.setPixmap(QPixmap())
        self.txt_preview.hide();
        self.txt_preview.clear()
        self.btn_save_changes.hide()
        self.current_storage_name = None

    def apply_filter_sort(self):
        data = self.raw_data[:]
        if self.check_filter.isChecked():
            data = [f for f in data if f['extension'] in ['.py', '.jpg']]
        idx = self.combo_sort.currentIndex()
        if idx == 1: data.sort(key=lambda x: x['uploader'])
        if idx == 2: data.sort(key=lambda x: x['uploader'], reverse=True)
        self.populate_table(data)

    def populate_table(self, data):
        self.table.setRowCount(0)
        for i, f in enumerate(data):
            self.table.insertRow(i)

            # Створюємо комірки
            item_name = QTableWidgetItem(f['filename'])
            # Зберігаємо приховані дані для логіки
            item_name.setData(Qt.ItemDataRole.UserRole, f['storage_name'])
            item_name.setData(Qt.ItemDataRole.UserRole + 1, f['access_type'])

            self.table.setItem(i, 0, item_name)
            self.table.setItem(i, 1, QTableWidgetItem(f['extension']))
            self.table.setItem(i, 2, QTableWidgetItem(f['created_at']))
            self.table.setItem(i, 3, QTableWidgetItem(f['updated_at']))
            self.table.setItem(i, 4, QTableWidgetItem(f['uploader']))
            self.table.setItem(i, 5, QTableWidgetItem(f['editor']))

            if f['access_type'] != 'owner':
                text_color = QColor("#FFD700")

                for c in range(6):
                    item = self.table.item(i, c)
                    if item:
                        item.setForeground(QBrush(text_color))

    def on_file_click(self, row, col):
        item = self.table.item(row, 0)
        storage_name = item.data(Qt.ItemDataRole.UserRole)
        access_type = item.data(Qt.ItemDataRole.UserRole + 1)
        ext = self.table.item(row, 1).text()

        self.current_storage_name = storage_name

        self.btn_download.setEnabled(True)
        self.btn_delete.setEnabled(True)

        if access_type == 'owner':
            self.btn_share.setEnabled(True)
            self.btn_share.setToolTip("Share file")
            self.btn_delete.setText("🗑 Delete File")
        else:
            self.btn_share.setEnabled(False)
            self.btn_share.setToolTip("You can only share your own files")
            self.btn_delete.setText("🚫 Remove Access")

        self.lbl_preview_img.setText("Loading...")
        self.lbl_preview_img.show()
        self.txt_preview.hide()
        self.btn_save_changes.hide()

        file_url = f"http://127.0.0.1:8000/raw/{storage_name}"
        can_edit = (ext == '.js') and (access_type == 'owner' or access_type == 'write')

        if ext == '.png':
            self.net_man.get(QNetworkRequest(QUrl(file_url)))
        elif ext == '.js':
            self.lbl_preview_img.hide()
            self.txt_preview.show()
            self.txt_preview.setReadOnly(not can_edit)

            import requests
            try:
                content = requests.get(file_url).text
                self.txt_preview.blockSignals(True)
                self.txt_preview.setText(content)
                self.txt_preview.blockSignals(False)
            except:
                self.txt_preview.setText("Error loading")
        else:
            self.lbl_preview_img.show();
            self.lbl_preview_img.clear();
            self.lbl_preview_img.setText("No preview available for this type.")
            self.txt_preview.hide()

    def on_text_edited(self):
        self.btn_save_changes.show()

    def save_text_changes(self):
        if not self.current_storage_name: return
        new_text = self.txt_preview.toPlainText()

        if self.api.update_content(self.current_storage_name, new_text):
            QMessageBox.information(self, "Saved", "File updated successfully!")
            self.btn_save_changes.hide()
            self.load_data()
        else:
            QMessageBox.critical(self, "Error", "Failed to save changes")

    def download_selected(self):
        row = self.table.currentRow()
        if row < 0: return
        name = self.table.item(row, 0).text()
        storage_name = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        save_path, _ = QFileDialog.getSaveFileName(self, "Save File", name)
        if save_path:
            import requests
            try:
                url = f"http://127.0.0.1:8000/raw/{storage_name}"
                r = requests.get(url)
                with open(save_path, 'wb') as f:
                    f.write(r.content)
                QMessageBox.information(self, "Success", "Saved")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def delete_selected(self):
        row = self.table.currentRow()
        if row < 0: return
        name = self.table.item(row, 0).text()
        storage_name = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        access_type = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole + 1)

        msg = f"Delete file '{name}' permanently?" if access_type == 'owner' else f"Remove access to '{name}'?"

        ans = QMessageBox.question(self, "Confirm", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ans == QMessageBox.StandardButton.Yes:
            import requests
            try:
                headers = {"Authorization": f"Bearer {self.api.token}"}
                res = requests.delete(f"http://127.0.0.1:8000/delete/{storage_name}", headers=headers)
                if res.status_code == 200:
                    self.load_data()
                    QMessageBox.information(self, "Done", "Operation successful.")
                else:
                    QMessageBox.warning(self, "Error", f"Code: {res.status_code}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def logout(self):
        self.api.token = None; self.close(); self.logout_callback()

    def on_img_downloaded(self, reply):
        http_status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if http_status == 200:
            data = reply.readAll()
            pix = QPixmap()
            if pix.loadFromData(data):
                self.lbl_preview_img.setPixmap(pix.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio))
                self.lbl_preview_img.setText("")
        reply.deleteLater()

    def upload_file(self, file_path=None):
        if not file_path: file_path, _ = QFileDialog.getOpenFileName(self)
        if file_path: self.api.upload_file(file_path); self.load_data()

    def share(self):
        row = self.table.currentRow()
        if row < 0: return
        fname = self.table.item(row, 0).text()
        user, ok = QInputDialog.getText(self, "Share", "Target Username:")
        if ok and user:
            level, ok2 = QInputDialog.getItem(self, "Level", "Access:", ["read", "write"])
            if ok2: self.api.share_file(fname, user, level)

    def toggle_cols(self):
        hidden = self.check_cols.isChecked()
        for c in [2, 3, 4, 5]: self.table.setColumnHidden(c, hidden)

    def sync(self):
        from workers import SyncWorker
        d = QFileDialog.getExistingDirectory(self)
        if d:
            self.worker = SyncWorker(self.api, d)
            self.worker.log.connect(lambda s: QMessageBox.information(self, "Sync", s))
            self.worker.start()