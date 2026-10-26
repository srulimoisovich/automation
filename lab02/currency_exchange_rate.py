#!/usr/bin/env python3
"""
Получение курса валют через Web API (лабораторная работа №2).

Скрипт обращается к локальному сервису курсов валют (lab02prep),
получает курс одной валюты к другой на указанную дату и сохраняет
результат в JSON-файл в каталоге data/ рядом со скриптом.

Все ошибки (неверные параметры, ошибка API, отсутствие связи,
некорректный ответ) выводятся в stderr и дописываются в файл error.log,
который также лежит рядом со скриптом. При ошибке код возврата равен 1.

Использование:
    python3 currency_exchange_rate.py -f RON -t MDL -d 2025-01-10 [-k KEY] [-u URL]

Примеры:
    python3 currency_exchange_rate.py -f RON -t MDL -d 2025-01-10
    python3 currency_exchange_rate.py --from-currency usd --to-currency eur --date 2025-05-10
    python3 currency_exchange_rate.py -f RON -t MDL -d 2025-01-10 -k EXAMPLE_API_KEY -u http://localhost:8080
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime

import requests

# Адрес сервиса по умолчанию (локально запущенный lab02prep)
API_URL = "http://localhost:8080"

# Имя переменной окружения, из которой берётся ключ API
API_KEY_ENV = "EXCHANGE_API_KEY"

# Ключ по умолчанию для локального учебного сервиса
DEFAULT_KEY = "EXAMPLE_API_KEY"

# Границы периода, за который у сервиса есть данные
FIRST_DATE = "2025-01-01"
LAST_DATE = "2025-09-15"

# Время ожидания ответа сервиса в секундах
REQUEST_TIMEOUT = 10

# Каталог, в котором лежит сам скрипт. От него считаются пути к data/ и
# error.log, поэтому результат не зависит от текущего каталога запуска.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
LOG_FILE = os.path.join(SCRIPT_DIR, "error.log")


def setup_logging():
    """
    Настраивает модуль logging для записи ошибок в файл error.log.

    В файл попадают только сообщения уровня ERROR и выше. Каждая строка
    содержит дату и время, уровень и текст сообщения.

    Аргументы:
        нет.

    Возвращает:
        None.
    """
    # Формат строки: "2026-10-23 15:10:31 - ERROR - текст ошибки"
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.ERROR,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        encoding="utf-8",
    )


def report_error(message):
    """
    Сообщает об ошибке пользователю и записывает её в журнал.

    Аргументы:
        message (str): полный текст ошибки, например
            "Ошибка: дата ... указана в неверном формате".

    Возвращает:
        None.
    """
    # Пользователь видит сообщение в стандартном потоке ошибок
    print(message, file=sys.stderr)
    # Та же ошибка дописывается в error.log
    logging.error(message)


def read_arguments():
    """
    Разбирает параметры командной строки.

    Обязательные параметры: исходная валюта, целевая валюта и дата.
    Необязательные: ключ API и адрес сервиса.

    Аргументы:
        нет (используется sys.argv).

    Возвращает:
        argparse.Namespace: объект с полями from_currency, to_currency,
        date, key и url.
    """
    parser = argparse.ArgumentParser(
        description="Получение курса валют на указанную дату через Web API.",
    )
    # Исходная валюта (из какой валюты переводим)
    parser.add_argument(
        "-f", "--from-currency", required=True,
        help="код исходной валюты из трёх букв, например RON",
    )
    # Целевая валюта (в какую валюту переводим)
    parser.add_argument(
        "-t", "--to-currency", required=True,
        help="код целевой валюты из трёх букв, например MDL",
    )
    # Дата, на которую нужен курс
    parser.add_argument(
        "-d", "--date", required=True,
        help=f"дата в формате ГГГГ-ММ-ДД в пределах с {FIRST_DATE} по {LAST_DATE}",
    )
    # Ключ API: сначала из переменной окружения, иначе учебный ключ
    parser.add_argument(
        "-k", "--key", default=os.environ.get(API_KEY_ENV, DEFAULT_KEY),
        help=f"ключ API (по умолчанию из переменной {API_KEY_ENV} или {DEFAULT_KEY})",
    )
    # Адрес сервиса
    parser.add_argument(
        "-u", "--url", default=API_URL,
        help=f"адрес сервиса (по умолчанию {API_URL})",
    )
    return parser.parse_args()


def check_currency(code):
    """
    Проверяет код валюты и приводит его к верхнему регистру.

    Код считается корректным, если он состоит ровно из трёх латинских
    букв (A-Z). Сервис принимает только заглавные буквы, поэтому
    строчные буквы переводятся в заглавные.

    Аргументы:
        code (str): код валюты, введённый пользователем.

    Возвращает:
        str | None: код в верхнем регистре или None, если код неверный.
    """
    # Убираем пробелы по краям и переводим в верхний регистр
    upper_code = code.strip().upper()
    # Допускаем только латиницу ASCII: isalpha() без isascii()
    # пропустил бы, например, кириллицу
    if len(upper_code) == 3 and upper_code.isascii() and upper_code.isalpha():
        return upper_code
    report_error(f'Ошибка: код валюты должен состоять из трёх латинских букв (получено: "{code}").')
    return None


def check_date(date_text):
    """
    Проверяет формат даты и её попадание в доступный период.

    Аргументы:
        date_text (str): дата, введённая пользователем.

    Возвращает:
        str | None: дата в формате ГГГГ-ММ-ДД или None, если дата
        неверная или выходит за пределы периода.
    """
    # Пробуем разобрать дату строго по шаблону ГГГГ-ММ-ДД
    try:
        parsed = datetime.strptime(date_text, "%Y-%m-%d").date()
    except ValueError:
        report_error(f'Ошибка: дата "{date_text}" указана в неверном формате, ожидается ГГГГ-ММ-ДД.')
        return None

    # Сервис без ошибки подставляет последний курс для дат вне периода,
    # поэтому границы проверяем сами
    first = datetime.strptime(FIRST_DATE, "%Y-%m-%d").date()
    last = datetime.strptime(LAST_DATE, "%Y-%m-%d").date()
    if not first <= parsed <= last:
        report_error(
            f"Ошибка: дата {parsed.isoformat()} выходит за пределы доступного периода "
            f"(с {FIRST_DATE} по {LAST_DATE})."
        )
        return None

    # Возвращаем дату в нормализованном виде
    return parsed.isoformat()


def request_rate(currency_from, currency_to, date_text, api_key, api_url):
    """
    Запрашивает курс валют у сервиса.

    Аргументы:
        currency_from (str): код исходной валюты.
        currency_to (str): код целевой валюты.
        date_text (str): дата в формате ГГГГ-ММ-ДД.
        api_key (str): ключ API.
        api_url (str): адрес сервиса.

    Возвращает:
        dict | None: полный ответ сервиса ({"error": "", "data": {...}})
        или None, если произошла ошибка.
    """
    # Формируем параметры GET-запроса (они попадают в строку адреса)
    params = {"from": currency_from, "to": currency_to, "date": date_text}
    # Ключ передаётся в теле POST-запроса
    body = {"key": api_key}
    # Краткое описание запроса для сообщений об ошибках
    request_info = f"запрос {currency_from} -> {currency_to}, {date_text}"

    # Отправляем запрос с явным ограничением времени ожидания
    try:
        response = requests.post(api_url, params=params, data=body, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.ConnectionError:
        report_error(f"Ошибка: не удалось подключиться к сервису {api_url}. Проверьте, что он запущен.")
        return None
    except requests.exceptions.Timeout:
        report_error(f"Ошибка: сервис {api_url} не ответил за {REQUEST_TIMEOUT} секунд.")
        return None
    except requests.exceptions.RequestException as error:
        report_error(f"Ошибка: не удалось выполнить запрос к {api_url}: {error}")
        return None

    # Проверяем HTTP-код ответа
    if response.status_code != 200:
        report_error(f"Ошибка: сервис вернул HTTP-код {response.status_code} ({request_info}).")
        return None

    # Разбираем тело ответа как JSON. При неверных параметрах сервис
    # может вернуть HTML-страницу с ошибкой PHP вместо JSON.
    try:
        result = response.json()
    except ValueError:
        report_error(f"Ошибка: сервис вернул ответ, который не является JSON ({request_info}).")
        return None

    # Ответ должен быть объектом JSON (словарём)
    if not isinstance(result, dict):
        report_error(f"Ошибка: сервис вернул ответ неожиданного вида ({request_info}).")
        return None

    # Непустое поле error означает ошибку на стороне API
    if result.get("error"):
        report_error(f"Ошибка API: {result['error']} ({request_info})")
        return None

    # Без поля data курс получить нельзя
    if not isinstance(result.get("data"), dict) or "rate" not in result["data"]:
        report_error(f"Ошибка: в ответе сервиса нет данных о курсе ({request_info}).")
        return None

    return result


def make_file_name(currency_from, currency_to, date_text):
    """
    Составляет имя файла для сохранения результата.

    Аргументы:
        currency_from (str): код исходной валюты.
        currency_to (str): код целевой валюты.
        date_text (str): дата в формате ГГГГ-ММ-ДД.

    Возвращает:
        str: имя файла вида RON_to_MDL_2025-01-10.json.
    """
    return f"{currency_from}_to_{currency_to}_{date_text}.json"


def save_to_json(currency_from, currency_to, date_text, response_data):
    """
    Сохраняет запрос и ответ сервиса в JSON-файл в каталоге data/.

    Каталог data/ создаётся, если его ещё нет. Ключ API в файл
    не записывается.

    Аргументы:
        currency_from (str): код исходной валюты.
        currency_to (str): код целевой валюты.
        date_text (str): дата в формате ГГГГ-ММ-ДД.
        response_data (dict): ответ сервиса.

    Возвращает:
        str | None: путь к файлу относительно каталога скрипта
        или None, если файл записать не удалось.
    """
    # Создаём каталог data/, если его ещё нет
    os.makedirs(DATA_DIR, exist_ok=True)

    # Полный путь к файлу результата
    file_path = os.path.join(DATA_DIR, make_file_name(currency_from, currency_to, date_text))

    # Содержимое файла: параметры запроса, ответ сервиса и время сохранения
    content = {
        "request": {"from": currency_from, "to": currency_to, "date": date_text},
        "response": response_data,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Записываем файл в UTF-8 с отступами для удобного чтения
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(content, file, ensure_ascii=False, indent=4)
    except OSError as error:
        report_error(f"Ошибка: не удалось записать файл {file_path}: {error}")
        return None

    # Для вывода показываем путь относительно каталога скрипта
    return os.path.relpath(file_path, SCRIPT_DIR)


def main():
    """
    Главная функция: выполняет все шаги по порядку.

    Шаги: настройка журнала, чтение параметров, проверка валют и даты,
    запрос к сервису, сохранение результата и вывод курса.

    Аргументы:
        нет.

    Возвращает:
        int: 0 при успехе, 1 при ошибке (код возврата программы).
    """
    # Шаг 1. Настраиваем запись ошибок в error.log
    setup_logging()

    # Шаг 2. Читаем параметры командной строки
    args = read_arguments()

    # Шаг 3. Проверяем коды валют
    currency_from = check_currency(args.from_currency)
    if currency_from is None:
        return 1
    currency_to = check_currency(args.to_currency)
    if currency_to is None:
        return 1

    # Шаг 4. Проверяем дату
    date_text = check_date(args.date)
    if date_text is None:
        return 1

    # Шаг 5. Запрашиваем курс у сервиса
    response_data = request_rate(currency_from, currency_to, date_text, args.key, args.url)
    if response_data is None:
        return 1

    # Шаг 6. Сохраняем результат в data/
    saved_path = save_to_json(currency_from, currency_to, date_text, response_data)
    if saved_path is None:
        return 1

    # Шаг 7. Выводим курс и путь к файлу
    rate = response_data["data"]["rate"]
    print(f"Курс {currency_from} -> {currency_to} на {date_text}: {rate}")
    print(f"Результат сохранён в файл: {saved_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
