import unittest
from unittest.mock import MagicMock
import sys
import os
from PyQt6.QtWidgets import QApplication

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from desktop_client.gui import MainWindow


app = QApplication(sys.argv)


class TestVariantUploader(unittest.TestCase):
    def setUp(self):
        """Підготовка тестових даних перед кожним тестом"""
        self.mock_api = MagicMock()
        self.mock_api.get_files.return_value = []
        self.window = MainWindow(self.mock_api, "tester", lambda: None)

        # Набір даних з різними Uploader та Extension
        self.test_data = [
            # uploader: 'anna' (найменше в алфавіті)
            {'filename': 'script.py', 'extension': '.py', 'uploader': 'anna', 'created_at': '', 'updated_at': '',
             'editor': '', 'access_type': 'owner', 'storage_name': '1'},
            # uploader: 'boris'
            {'filename': 'photo.jpg', 'extension': '.jpg', 'uploader': 'boris', 'created_at': '', 'updated_at': '',
             'editor': '', 'access_type': 'owner', 'storage_name': '2'},
            # uploader: 'victor'
            {'filename': 'text.txt', 'extension': '.txt', 'uploader': 'victor', 'created_at': '', 'updated_at': '',
             'editor': '', 'access_type': 'owner', 'storage_name': '3'},
            # uploader: 'zoya' (найбільше в алфавіті)
            {'filename': 'code.js', 'extension': '.js', 'uploader': 'zoya', 'created_at': '', 'updated_at': '',
             'editor': '', 'access_type': 'owner', 'storage_name': '4'}
        ]
        self.window.raw_data = self.test_data

    # 1. Сортування за Uploader
    def test_sort_by_uploader(self):
        """Перевірка сортування за іменем завантажувача (Asc/Desc)"""

        # 1. Сортування A-Z (Index 1)
        self.window.combo_sort.setCurrentIndex(1)
        self.window.apply_filter_sort()

        # Першим має бути 'anna', останнім 'zoya'
        first_uploader = self.window.table.item(0, 4).text()
        last_uploader = self.window.table.item(3, 4).text()

        self.assertEqual(first_uploader, 'anna', "First should be 'anna' (A-Z)")
        self.assertEqual(last_uploader, 'zoya')

        # 2. Сортування Z-A (Index 2)
        self.window.combo_sort.setCurrentIndex(2)
        self.window.apply_filter_sort()

        # Першим має бути 'zoya', останнім 'anna'
        first_uploader_desc = self.window.table.item(0, 4).text()
        self.assertEqual(first_uploader_desc, 'zoya', "First should be 'zoya' (Z-A)")

    # 2.Фільтрація .py / .jpg
    def test_filter_py_jpg(self):

        # Без фільтру -> 4 файли
        self.window.check_filter.setChecked(False)
        self.window.apply_filter_sort()
        self.assertEqual(self.window.table.rowCount(), 4)

        # Вмикаємо фільтр
        self.window.check_filter.setChecked(True)
        self.window.apply_filter_sort()

        # Має залишитись 2 файли (.py та .jpg). Файли .txt та .js мають зникнути.
        self.assertEqual(self.window.table.rowCount(), 2)

        # Перевіряємо розширення видимих файлів
        exts = [self.window.table.item(i, 1).text() for i in range(2)]
        self.assertIn('.py', exts)
        self.assertIn('.jpg', exts)
        self.assertNotIn('.txt', exts)

    # 3. Пошук та вибір
    def test_selection_logic(self):
        """Перевірка, що при виборі файлу кнопки стають активними"""
        self.window.apply_filter_sort()

        # Кнопки спочатку вимкнені
        self.assertFalse(self.window.btn_share.isEnabled())

        # Вибираємо перший файл (anna/script.py, access: owner)
        self.window.on_file_click(0, 0)

        # Оскільки це owner, кнопка Share має активуватись
        self.assertTrue(self.window.btn_share.isEnabled())
        # І кнопка Delete
        self.assertTrue(self.window.btn_delete.isEnabled())

    # 4. Збереження цілісності даних
    def test_data_consistency(self):
        """Перевірка відповідності даних у таблиці оригінальним даним"""
        self.window.apply_filter_sort()

        # Шукаємо файл photo.jpg
        row = -1
        for i in range(self.window.table.rowCount()):
            if self.window.table.item(i, 0).text() == 'photo.jpg':
                row = i
                break

        self.assertNotEqual(row, -1, "File photo.jpg not found in table")

        # Перевіряємо, чи правильний Uploader прив'язаний до цього рядка
        uploader_in_table = self.window.table.item(row, 4).text()
        self.assertEqual(uploader_in_table, 'boris')


if __name__ == '__main__':
    unittest.main()