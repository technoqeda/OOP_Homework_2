import requests
import json
import os
from tqdm import tqdm


def get_vk_photos(user_id, token):
    url = f"https://api.vk.com/method/photos.get?owner_id={user_id}&album_id=profile&photo_sizes=1&access_token={token}&v=5.131"
    response = requests.get(url)
    data = response.json()
    if 'response' in data:
        photos = data['response']['items']
        return photos
    else:
        print("Ошибка при получении фотографий:", data)
        return []


def create_folder_on_yandex_disk(folder_name, yandex_token):
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {'Authorization': f'OAuth {yandex_token}'}
    params = {'path': folder_name}
    response = requests.put(url, headers=headers, params=params)
    if response.status_code == 201:
        print(f"Папка {folder_name} успешно создана на Яндекс.Диске.")
    elif response.status_code == 409:
        print(f"Папка {folder_name} уже существует на Яндекс.Диске.")
    else:
        print(f"Не удалось создать папку {folder_name} на Яндекс.Диске: {response.json()}")


def upload_to_yandex_disk(photos, yandex_token, folder_name, limit=5):
    headers = {'Authorization': f'OAuth {yandex_token}'}
    base_url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
    uploaded_photos = []

    for photo in tqdm(photos[:limit], desc="Uploading photos"):
        max_size_url = max(photo['sizes'], key=lambda x: x['width'] * x['height'])['url']
        if 'likes' in photo:
            photo_name = f"{photo['likes']['count']}.jpg"
        else:
            photo_name = f"{photo['id']}.jpg"  # Используем id фотографии, если 'likes' нет
        upload_url = f"{base_url}?path={folder_name}/{photo_name}&overwrite=true"
        response = requests.get(upload_url, headers=headers)
        upload_data = response.json()

        if 'href' in upload_data:
            with requests.get(max_size_url, stream=True) as r:
                with open(photo_name, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            with open(photo_name, 'rb') as f:
                requests.put(upload_data['href'], files={'file': f})
            os.remove(photo_name)
            uploaded_photos.append({"file_name": photo_name, "size": "z"})
        else:
            print(f"Не удалось загрузить {photo_name}: {upload_data.get('message', 'Unknown error')}")

    with open("uploaded_photos.json", "w") as json_file:
        json.dump(uploaded_photos, json_file, indent=4)


if __name__ == "__main__":
    vk_user_id = input("Введите ID пользователя VK: ")
    vk_token = input("Введите новый токен доступа VK: ")
    yandex_token = input("Введите токен Яндекс.Диска: ")
    folder_name = input("Введите название папки для сохранения фотографий: ")

    # Создаем папку на Яндекс.Диске
    create_folder_on_yandex_disk(folder_name, yandex_token)

    photos = get_vk_photos(vk_user_id, vk_token)
    if photos:
        upload_to_yandex_disk(photos, yandex_token, folder_name)
