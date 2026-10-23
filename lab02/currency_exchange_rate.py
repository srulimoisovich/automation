#!/usr/bin/env python3
"""Получение курса валют через Web API (лабораторная работа №2)."""

import argparse
import json
import logging
import os
import sys
from datetime import datetime

import requests

API_URL = "http://localhost:8080"
API_KEY_ENV = "EXCHANGE_API_KEY"
DEFAULT_KEY = "EXAMPLE_API_KEY"
FIRST_DATE = "2025-01-01"
LAST_DATE = "2025-09-15"
REQUEST_TIMEOUT = 10

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
LOG_FILE = os.path.join(SCRIPT_DIR, "error.log")


def setup_logging():
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.ERROR,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        encoding="utf-8",
    )


def report_error(message):
    print(message, file=sys.stderr)
    logging.error(message)


def read_arguments():
    parser = argparse.ArgumentParser(
        description="Получение курса валют на указанную дату через Web API.",
    )
    parser.add_argument(
        "-f", "--from-currency", required=True,
        help="код исходной валюты из трёх букв, например RON",
    )
    parser.add_argument(
        "-t", "--to-currency", required=True,
        help="код целевой валюты из трёх букв, например MDL",
    )
    parser.add_argument(
        "-d", "--date", required=True,
        help=f"дата в формате ГГГГ-ММ-ДД в пределах {FIRST_DATE} — {LAST_DATE}",
    )
    parser.add_argument(
        "-k", "--key", default=os.environ.get(API_KEY_ENV, DEFAULT_KEY),
        help=f"ключ API (по умолчанию из переменной {API_KEY_ENV} или {DEFAULT_KEY})",
    )
    parser.add_argument(
        "-u", "--url", default=API_URL,
        help=f"адрес сервиса (по умолчанию {API_URL})",
    )
    return parser.parse_args()


def check_currency(code):
    upper_code = code.strip().upper()
    if len(upper_code) == 3 and upper_code.isascii() and upper_code.isalpha():
        return upper_code
    report_error(f'Ошибка: код валюты должен состоять из трёх латинских букв (получено: "{code}").')
    return None


def check_date(date_text):
    try:
        parsed = datetime.strptime(date_text, "%Y-%m-%d").date()
    except ValueError:
        report_error(f'Ошибка: дата "{date_text}" указана в неверном формате, ожидается ГГГГ-ММ-ДД.')
        return None

    first = datetime.strptime(FIRST_DATE, "%Y-%m-%d").date()
    last = datetime.strptime(LAST_DATE, "%Y-%m-%d").date()
    if not first <= parsed <= last:
        report_error(
            f"Ошибка: дата {parsed.isoformat()} выходит за пределы доступного периода "
            f"({FIRST_DATE} — {LAST_DATE})."
        )
        return None

    return parsed.isoformat()


def request_rate(currency_from, currency_to, date_text, api_key, api_url):
    params = {"from": currency_from, "to": currency_to, "date": date_text}
    body = {"key": api_key}
    request_info = f"запрос {currency_from} -> {currency_to}, {date_text}"

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

    if response.status_code != 200:
        report_error(f"Ошибка: сервис вернул HTTP-код {response.status_code} ({request_info}).")
        return None

    try:
        result = response.json()
    except ValueError:
        report_error(f"Ошибка: сервис вернул ответ, который не является JSON ({request_info}).")
        return None

    if not isinstance(result, dict):
        report_error(f"Ошибка: сервис вернул ответ неожиданного вида ({request_info}).")
        return None

    if result.get("error"):
        report_error(f"Ошибка API: {result['error']} ({request_info})")
        return None

    if not isinstance(result.get("data"), dict) or "rate" not in result["data"]:
        report_error(f"Ошибка: в ответе сервиса нет данных о курсе ({request_info}).")
        return None

    return result


def make_file_name(currency_from, currency_to, date_text):
    return f"{currency_from}_to_{currency_to}_{date_text}.json"


def save_to_json(currency_from, currency_to, date_text, response_data):
    os.makedirs(DATA_DIR, exist_ok=True)

    file_path = os.path.join(DATA_DIR, make_file_name(currency_from, currency_to, date_text))

    content = {
        "request": {"from": currency_from, "to": currency_to, "date": date_text},
        "response": response_data,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(content, file, ensure_ascii=False, indent=4)
    except OSError as error:
        report_error(f"Ошибка: не удалось записать файл {file_path}: {error}")
        return None

    return os.path.relpath(file_path, SCRIPT_DIR)


def main():
    setup_logging()

    args = read_arguments()

    currency_from = check_currency(args.from_currency)
    if currency_from is None:
        return 1
    currency_to = check_currency(args.to_currency)
    if currency_to is None:
        return 1

    date_text = check_date(args.date)
    if date_text is None:
        return 1

    response_data = request_rate(currency_from, currency_to, date_text, args.key, args.url)
    if response_data is None:
        return 1

    saved_path = save_to_json(currency_from, currency_to, date_text, response_data)
    if saved_path is None:
        return 1

    rate = response_data["data"]["rate"]
    print(f"Курс {currency_from} -> {currency_to} на {date_text}: {rate}")
    print(f"Результат сохранён в файл: {saved_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
