import requests

BASE_URL = "http://127.0.0.1:8000"


class CloudAPI:
    def __init__(self):
        self.token = None

    def login(self, username, password):
        try:
            res = requests.post(f"{BASE_URL}/token", data={"username": username, "password": password})
            if res.status_code == 200:
                self.token = res.json()["access_token"]
                return True
        except:
            pass
        return False

    def register(self, username, password):
        try:
            requests.post(f"{BASE_URL}/register", data={"username": username, "password": password})
        except:
            pass

    def get_header(self):
        return {"Authorization": f"Bearer {self.token}"}

    def get_files(self):
        try:
            return requests.get(f"{BASE_URL}/files", headers=self.get_header()).json()
        except:
            return []

    def upload_file(self, path):
        try:
            files = {'file': open(path, 'rb')}
            requests.post(f"{BASE_URL}/upload", files=files, headers=self.get_header())
        except:
            pass

    def share_file(self, filename, target, level):
        try:
            requests.post(f"{BASE_URL}/share", json={"filename": filename, "target_user": target, "level": level},
                          headers=self.get_header())
            return True
        except:
            return False

    def update_content(self, storage_name, new_text):
        try:
            url = f"{BASE_URL}/update_content"
            # Формуємо JSON для відправки
            data = {
                "storage_name": storage_name,
                "content": new_text
            }
            res = requests.post(url, json=data, headers=self.get_header())
            return res.status_code == 200
        except Exception as e:
            print(f"Update error: {e}")
            return False