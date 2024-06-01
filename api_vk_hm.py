import requests
import json
import os
from tqdm import tqdm
import configparser

class VkAPI:
    def __init__(self, token):
        self.token = token

    def get_user_id(self, vk_user_identifier):
        if vk_user_identifier.isdigit():
            return vk_user_identifier
        url = f"https://api.vk.com/method/users.get?user_ids={vk_user_identifier}&access_token={self.token}&v=5.131"
        response = requests.get(url)
        data = response.json()
        if 'response' in data:
            return data['response'][0]['id']
        else:
            print("Ошибка при получении id пользователя:", data)
            return None

    def get_photos(self, user_id):
        url = f"https://api.vk.com/method/photos.get?owner_id={user_id}&album_id=profile&photo_sizes=1&access_token={self.token}&v=5.131"
        response = requests.get(url)
        data = response.json()
        if 'response' in data:
            return data['response']['items']
        else:
            print("Ошибка при получении фотографий:", data)
            return []

class YandexDiskAPI:
    def __init__(self, token):
        self.token = token

    def create_folder(self, folder_name):
        url = "https://cloud-api.yandex.net/v1/disk/resources"
        headers = {'Authorization': f'OAuth {self.token}'}
        params = {'path': folder_name}
        response = requests.put(url, headers=headers, params=params)
        if response.status_code == 201:
            print(f"Папка {folder_name} успешно создана на Яндекс.Диске.")
        elif response.status_code == 409:
            print(f"Папка {folder_name} уже существует на Яндекс.Диске.")
        else:
            print(f"Не удалось создать папку {folder_name} на Яндекс.Диске: {response.json()}")

    def upload_photo(self, photo_url, folder_name, photo_name):
        headers = {'Authorization': f'OAuth {self.token}'}
        base_url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
        upload_url = f"{base_url}?path={folder_name}/{photo_name}&overwrite=true"
        response = requests.get(upload_url, headers=headers)
        upload_data = response.json()

        if 'href' in upload_data:
            with requests.get(photo_url, stream=True) as r:
                with open(photo_name, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            with open(photo_name, 'rb') as f:
                requests.put(upload_data['href'], files={'file': f})
            os.remove(photo_name)
            return True
        else:
            print(f"Не удалось загрузить {photo_name}: {upload_data.get('message', 'Unknown error')}")
            return False

class BackupPhotos:
    def __init__(self, vk_token, yandex_token):
        self.vk_api = VkAPI(vk_token)
        self.yandex_api = YandexDiskAPI(yandex_token)

    def backup(self, vk_user_identifier, folder_name, photo_count=5):
        user_id = self.vk_api.get_user_id(vk_user_identifier)
        if user_id is None:
            print("Не удалось получить id пользователя. Завершение программы.")
            return

        self.yandex_api.create_folder(folder_name)
        photos = self.vk_api.get_photos(user_id)
        if photos:
            uploaded_photos = []
            for photo in tqdm(photos[:photo_count], desc="Uploading photos"):
                max_size_url = max(photo['sizes'], key=lambda x: x['width'] * x['height'])['url']
                if 'likes' in photo:
                    photo_name = f"{photo['likes']['count']}.jpg"
                else:
                    photo_name = f"{photo['id']}.jpg"  # Используем id фотографии, если 'likes' нет
                if self.yandex_api.upload_photo(max_size_url, folder_name, photo_name):
                    uploaded_photos.append({"file_name": photo_name, "size": "z"})

            with open("uploaded_photos.json", "w") as json_file:
                json.dump(uploaded_photos, json_file, indent=4)

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.ini')

    vk_token = config['tokens']['vk_token']
    yandex_token = config['tokens']['yandex_token']

    vk_user_identifier = input("Введите ID пользователя VK или никнейм: ")
    folder_name = input("Введите название папки для сохранения фотографий: ")
    photo_count = int(input("Введите количество фотографий для загрузки: "))

    backup_photos = BackupPhotos(vk_token, yandex_token)
    backup_photos.backup(vk_user_identifier, folder_name, photo_count)
