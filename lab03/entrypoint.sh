#!/bin/sh
# Запуск контейнера: часовой пояс, журнал, задания cron, cron

set_timezone() {
    TZ="${TZ:-Europe/Chisinau}"
    ln -snf "/usr/share/zoneinfo/$TZ" /etc/localtime
    echo "$TZ" > /etc/timezone
    echo "Часовой пояс: $TZ, текущее время: $(date '+%Y-%m-%d %H:%M:%S %Z')"
}

create_log_file() {
    echo "Создаём файл журнала /var/log/cron.log..."
    touch /var/log/cron.log
    chmod 666 /var/log/cron.log
    echo "Журнал /var/log/cron.log готов, сюда будут дописывать вывод задания cron"
}

install_cronjob() {
    cp /lab03/cronjob /etc/cron.d/currency_rates
    chmod 0644 /etc/cron.d/currency_rates
    echo "Задания cron установлены в /etc/cron.d/currency_rates"
}

monitor_logs() {
    echo "=== Следим за журналом cron ==="
    tail -f /var/log/cron.log
}

run_cron() {
    echo "=== Запускаем демон cron в режиме переднего плана... ==="
    exec cron -f
}

set_timezone
# окружение для заданий cron
env > /etc/environment
create_log_file
install_cronjob
monitor_logs &
run_cron
