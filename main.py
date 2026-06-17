import json

import requests


class CatApiClient:
    """Класс определяет методы работы с Cats API
    Атрибуты - основной url API
    Метод - получение картинки кошки по заданному тексту
    """
    def __init__(self):
        self._BASE_URL = "https://cataas.com/cat/says"

    def get_cat_image(self, text):
        """Получение картинки по  Cats API с надписью text
        Функция возвращает полученную картинку, если код ответа успешен
        """
        response = requests.get(f"{self._BASE_URL}/{text}")
        response.raise_for_status()
        return response.content


class YandexDiskClient:
    """Класс определяет методы работы с Яндекс Диском
    Атрибуты - основной url и токен
    Методы:
    _request - внутренний метод, обертка над requests.request
    create_folder - создание папки на диске
    get_file_info - получение информации о файле
    _get_link_for_upload - внутренний метод, получение ссылки для загрузки файла
    upload_file - загрузка файла на диск
    """
    def __init__(self, token):
        self._BASE_URL = "https://cloud-api.yandex.net/v1/disk/resources"
        self._headers = {"Authorization": token}

    def _request(self, method, params, path=""):
        """Метод обертка над requests.request
        Переиспользует внутри общий путь к API Яндекс диска - self._BASE_URL и заголовки self._headers
        Пропускает статус 409 - ситуации, когда ресурс уже существует на Яндекс Диске
        Возвращает полученный response
        """
        response = requests.request(method,
                                    f'{self._BASE_URL}{path}',
                                    params=params,
                                    headers=self._headers
                                    )

        if response.status_code != 409:
            response.raise_for_status()

        return response

    def create_folder(self, folder_path):
        """Создание папки на Яндекс Диске
        Успешным ответом считается статус, что папка создана, либо уже существует на диске
        Ошибки обрабатываются через обертку _request
        """
        response = self._request("PUT", {"path": folder_path})
        return response

    def get_file_info(self, file_path):
        """Получение информации о файле на Яндекс Диске
        В случае успеха функция возвращает информацию в формате json
         Ошибки обрабатываются через обертку _request
        """
        response = self._request("GET", {"path": file_path})
        return response.json()

    def _get_link_for_upload(self, destination_path, overwrite=True):
        """Получение ссылки для загрузки файла на Яндекс Диск
        По умолчанию получаем ссылку для перезаписи файла (параметр overwrite = True)
        В случае успеха функция возвращает ссылку, ошибки обрабатываются через обертку _request
        """
        response = self._request("GET",
                                 {"path": destination_path, "overwrite": overwrite},
                                 path="/upload"
                                 )
        return response.json().get("href")

    def upload_file(self, destination_path, data):
        """Загрузка файла на Яндекс Диск по пути destination_path.
        Переиспольузет внутри функцию _get_link_for_upload для получения ссылки на загрузку
        В качестве параметра data может получать словарь или поток байтов
        Если в data содержится словарь, то предварительно происходит сериализация, а потом уже загрузка
        """
        if isinstance(data, dict):
            data = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')

        response = requests.put(self._get_link_for_upload(destination_path),
                                files={'file': data})
        response.raise_for_status()
        return response

class CatFileUploader:
    """Класс - обертка для CatApiClient и YandexDiskClient.
    Связывает логику получения данных из Cats Api и загрузки на Яндекс Диск
    """
    def __init__(self, disk_client, cat_client):
        self.disk = disk_client
        self.cat = cat_client
        self._DEFAULT_FOLDER = "PYAPI-154"

    def upload(self, text, folder_path=""):
        """Функция последовательно выполняет следующие шаги:
        1. Получение картинки из Cats Api
        2. Создание папки на Яндекс Диске (по умолчанию константа DEFAULT_FOLDER).
        Если папка с этим именем есть, это обрабатывается стандартным API Диска
        3. Загрузка полученной картинки в папку - по имени <text>.jpg
        4. Получение информации по картинке в json (в том числе там есть информация по размеру файла)
        5. Создание json файла в папке - по имени <text>.json
        """
        if folder_path == "":
            folder_path = self._DEFAULT_FOLDER

        print("1. Получаем картинку")
        image = self.cat.get_cat_image(text)

        print("2. Создаем\проверяем наличие папки")
        self.disk.create_folder(folder_path)

        print("3. Загружаем картинку на диск")
        image_path = f'/{folder_path}/{text}.jpg'
        self.disk.upload_file(image_path, image)

        print("4. Получаем информацию по картинке")
        file_info = self.disk.get_file_info(image_path)

        print("5. Загружаем json с метаданными")
        metadata_path = f'/{folder_path}/{text}.json'
        self.disk.upload_file(metadata_path, file_info)

def main():
    print("Введите текст для отображения на фото: ", end='')
    text = input().strip()
    if not text:
        print("Текст не может быть пустым")
        return

    print("Введите токен Яндекс.Диска: ", end='')
    token = input().strip()
    if not token:
        print("Токен не может быть пустым")
        return

    disk_client = YandexDiskClient(token)
    cat_client = CatApiClient()
    uploader = CatFileUploader(disk_client, cat_client)

    try:
        uploader.upload(text)
        print("Успешно завершено!")
    except Exception as e:
        print(f"Ошибка исполнения: {e}")

if __name__ == "__main__":
    main()
