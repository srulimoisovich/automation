#!/bin/bash

set -euo pipefail

DIR_SRC=${1:?"Не передан путь к папке для бэкапа. Пример: $0 /path/to/dir [/path/to/backup]"}
DIR_DST=${2:-/backup}

echo ">> Проверка входных директорий..."

if [[ ! -d "$DIR_SRC" ]]; then
  printf 'Ошибка: папка-источник "%s" не существует.\n' "$DIR_SRC" >&2
  exit 2
fi

if [[ ! -d "$DIR_DST" ]]; then
  printf 'Папка назначения "%s" не найдена, создаю новую...\n' "$DIR_DST"
  if ! mkdir -p "$DIR_DST" 2>/dev/null; then
    printf 'Ошибка: не получилось создать папку "%s".\n' "$DIR_DST" >&2
    exit 2
  fi
fi

if [[ ! -w "$DIR_DST" ]]; then
  printf 'Ошибка: нет доступа на запись в "%s".\n' "$DIR_DST" >&2
  exit 2
fi

echo ">> Подготовка архива..."

DIR_SRC_CLEAN=${DIR_SRC%/}
BASE_NAME=$(basename -- "$DIR_SRC_CLEAN")
PARENT_DIR=$(dirname -- "$DIR_SRC_CLEAN")
STAMP=$(date +'%d-%m-%Y_%H%M%S')
OUT_FILE="${DIR_DST%/}/${BASE_NAME}.${STAMP}.tar.gz"

echo ">> Создаю архив: $OUT_FILE"

pushd "$PARENT_DIR" > /dev/null
tar -czf "$OUT_FILE" "$BASE_NAME"
RESULT=$?
popd > /dev/null

if [[ $RESULT -ne 0 ]]; then
  echo "Ошибка: архивация завершилась неудачно." >&2
  rm -f "$OUT_FILE" 2>/dev/null || true
  exit 1
fi

echo ">> Готово! Резервная копия сохранена: $OUT_FILE"
