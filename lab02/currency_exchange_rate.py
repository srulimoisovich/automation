#!/usr/bin/env python3
"""Получение курса валют через Web API (лабораторная работа №2)."""

import argparse
import json
import os
import sys
from datetime import datetime

import requests

API_URL = "http://localhost:8080"
API_KEY_ENV = "EXCHANGE_API_KEY"
DEFAULT_KEY = "EXAMPLE_API_KEY"
REQUEST_TIMEOUT = 10

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")


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
        help="дата в формате ГГГГ-ММ-ДД",
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


def request_rate(currency_from, currency_to, date_text, api_key, api_url):
    params = {"from": currency_from, "to": currency_to, "date": date_text}
    body = {"key": api_key}
    response = requests.post(api_url, params=params, data=body, timeout=REQUEST_TIMEOUT)
    result = response.json()
    if result.get("error"):
        print(f"Ошибка API: {result['error']}", file=sys.stderr)
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
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(content, file, ensure_ascii=False, indent=4)
    return os.path.relpath(file_path, SCRIPT_DIR)


def main():
    args = read_arguments()
    currency_from = args.from_currency.upper()
    currency_to = args.to_currency.upper()

    response_data = request_rate(currency_from, currency_to, args.date, args.key, args.url)
    if response_data is None:
        return 1

    saved_path = save_to_json(currency_from, currency_to, args.date, response_data)
    rate = response_data["data"]["rate"]
    print(f"Курс {currency_from} -> {currency_to} на {args.date}: {rate}")
    print(f"Результат сохранён в файл: {saved_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
