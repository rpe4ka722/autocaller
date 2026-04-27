#!/bin/bash

# Настройки логирования
LOG_FILE="/opt/autocaller/autocaller_patch.log"
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ASTERISK_DIR="/etc/asterisk/"
TARGET_DIR="/opt/autocaller"

mkdir -p "$TARGET_DIR"

log_message() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $1" | tee -a "$LOG_FILE"
}

echo_and_log() {
    echo "$1"
    log_message "$1"
}

# Проверка прав администратора
if [ "$EUID" -ne 0 ]; then
  echo "Пожалуйста, запустите скрипт от имени администратора (sudo)."
  exit 1
fi

echo_and_log "========================================="
echo_and_log "Начало обновления Autocaller"
echo_and_log "========================================="

# 1. Настройка браузера (Firefox)
TARGET_BROWSER="firefox.desktop"
CURRENT_BROWSER=$(xdg-settings get default-web-browser 2>/dev/null)

if [ "$CURRENT_BROWSER" != "$TARGET_BROWSER" ]; then
    echo_and_log "Установка Firefox браузером по умолчанию..."
    xdg-settings set default-web-browser "$TARGET_BROWSER" 2>/dev/null
    if command -v update-alternatives >/dev/null 2>&1; then
        update-alternatives --set x-www-browser /usr/bin/firefox 2>/dev/null
        update-alternatives --set gnome-www-browser /usr/bin/firefox 2>/dev/null
    fi
fi

# 2. Подготовка файлов
cd "$TARGET_DIR" || { echo_and_log "ОШИБКА: Не удалось перейти в $TARGET_DIR"; exit 1; }

copy_with_log() {
    if [ -e "$1" ]; then
        cp -r "$1" "$2" && echo_and_log "УСПЕХ: $3 скопированы" || echo_and_log "ОШИБКА: Копирование $3"
    else
        echo_and_log "ПРЕДУПРЕЖДЕНИЕ: $3 не найдены ($1)"
    fi
}

# copy_with_log "$SCRIPT_DIR/db.sqlite3" "$TARGET_DIR/django-files" "база данных"
copy_with_log "$SCRIPT_DIR/django-files/.env" "$TARGET_DIR/django-files" "файл окружения"
copy_with_log "$SCRIPT_DIR/docker-compose.yml" "$TARGET_DIR/" "docker-compose.yml"

# 3. Работа с Docker образами
if [ -f "$SCRIPT_DIR/autocaller.tar" ]; then
    echo_and_log "Загрузка нового образа..."
    docker load -i "$SCRIPT_DIR/autocaller.tar" || { echo_and_log "ОШИБКА: Образ не загружен"; exit 1; }
    
    echo_and_log "Очистка старых образов..."
    IMAGE_IDS=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep "autocaller" | grep "<none>" || true)
    [ -n "$IMAGE_IDS" ] && docker rmi -f $IMAGE_IDS >/dev/null 2>&1
else
    echo_and_log "ОШИБКА: Файл autocaller.tar не найден!"
    exit 1
fi

if [ -f "$SCRIPT_DIR/postgres.tar" ]; then
    echo_and_log "Загрузка нового образа..."
    docker load -i "$SCRIPT_DIR/postgres.tar" || { echo_and_log "ОШИБКА: Образ не загружен"; exit 1; }

else
    echo_and_log "ОШИБКА: Файл postgres.tar не найден!"
    exit 1
fi

chmod -R 777 "$TARGET_DIR"

# 4. Запуск Docker Compose
if [ -f "docker-compose.yml" ]; then
    # Определяем команду
    if docker compose version >/dev/null 2>&1; then
        DOCKER_CMD="docker compose"
    elif command -v docker-compose >/dev/null 2>&1; then
        DOCKER_CMD="docker-compose"
    else
        echo_and_log "ОШИБКА: Docker Compose не найден"
        exit 1
    fi

    echo_and_log "Полная очистка контейнеров и томов статики..."
    $DOCKER_CMD down -v 2>/dev/null

    echo_and_log "Запуск сервисов..."
    $DOCKER_CMD up -d
    if [ $? -eq 0 ]; then
        echo_and_log "УСПЕХ: Контейнеры запущены"
        # echo_and_log "Обновление статики (collectstatic)..."
        # sleep 5 # Даем Django время проснуться
        # if docker exec django-app python3 manage.py collectstatic --noinput --clear; then
        #     echo_and_log "УСПЕХ: Статика обновлена"
        # else
        #     echo_and_log "ОШИБКА: Не удалось обновить статику"
        # fi
    else
        echo_and_log "ОШИБКА: Не удалось запустить Docker"
    fi
else
    echo_and_log "ОШИБКА: docker-compose.yml не найден"
fi

echo_and_log "========================================="
echo_and_log "Обновление завершено! Лог: $LOG_FILE"
echo_and_log "========================================="

read -p "Перезагрузить систему сейчас? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Перезагрузка..."
    sleep 2
    systemctl reboot
fi