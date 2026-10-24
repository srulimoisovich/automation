# Образ для запуска скрипта курса валют по расписанию cron (лабораторная работа №3).

# Берём за основу Ubuntu 24.04, как предлагается в задании
FROM ubuntu:24.04

# Отключаем вопросы apt во время установки пакетов (например, выбор часового пояса в tzdata)
ENV DEBIAN_FRONTEND=noninteractive

# Устанавливаем пакеты одной командой и сразу удаляем списки apt, чтобы образ был меньше:
# cron - планировщик заданий;
# python3 - интерпретатор для скрипта;
# python3-requests - библиотека requests из репозитория Ubuntu (версия 2.31.0 подходит под requests>=2.31);
# tzdata - база часовых поясов, нужна для Europe/Chisinau;
# procps - утилиты ps и top, чтобы проверить, что cron запущен
RUN apt-get update && apt-get install -y --no-install-recommends cron python3 python3-requests tzdata procps && rm -rf /var/lib/apt/lists/*

# Рабочий каталог внутри образа: здесь лежат скрипт и файл заданий
WORKDIR /lab03

# Копируем скрипт и список зависимостей (requirements.txt оставлен для справки)
COPY currency_exchange_rate.py requirements.txt ./

# Копируем файл заданий cron (его установит entrypoint при запуске контейнера)
COPY cronjob ./cronjob

# Копируем скрипт запуска контейнера в корень образа
COPY entrypoint.sh /entrypoint.sh

# Делаем скрипт запуска исполняемым
RUN chmod +x /entrypoint.sh

# При старте контейнера выполняется entrypoint.sh, он настраивает и запускает cron
ENTRYPOINT ["/entrypoint.sh"]
