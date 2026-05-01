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

# --- ЭКСПОРТ ДАННЫХ ИЗ СТАРОГО КОНТЕЙНЕРА ---
if [ "$(docker ps -q -f name=autocaller)" ]; then
    echo_and_log "Старый контейнер обнаружен. Делаем дамп базы SQLite..."
    
    # Делаем дамп внутри контейнера и сразу перенаправляем поток в файл на хосте
    docker compose exec -T autocaller python3 manage.py dumpdata \
        --exclude auth.permission \
        --exclude contenttypes \
        --exclude admin.logentry \
        --exclude sessions \
        > "$TARGET_DIR/data.json"

    if [ $? -eq 0 ] && [ -s "$TARGET_DIR/data.json" ]; then
        echo_and_log "УСПЕХ: Дамп базы сохранен в $TARGET_DIR/data.json"
    else
        echo_and_log "ОШИБКА: Не удалось создать дамп или файл пуст!"
        # Здесь можно добавить exit 1, если без данных обновляться нельзя
    fi
else
    echo_and_log "ПРЕДУПРЕЖДЕНИЕ: Работающий контейнер не найден, дамп пропущен."
fi

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
    $DOCKER_CMD down -v --remove-orphans

    echo_and_log "Запуск сервисов..."
    $DOCKER_CMD up -d
    if [ $? -eq 0 ]; then
        echo_and_log "УСПЕХ: Контейнеры запущены"
    else
        echo_and_log "ОШИБКА: Не удалось запустить Docker"
    fi
else
    echo_and_log "ОШИБКА: docker-compose.yml не найден"
fi

# --- ИМПОРТ В НОВЫЙ КОНТЕЙНЕР (POSTGRES) ---
echo_and_log "Ожидание инициализации базы данных (10 сек)..."
sleep 10

# 1. Применяем миграции
echo_and_log "Применение миграций в Postgres..."
$DOCKER_CMD exec -T autocaller python3 manage.py migrate --noinput

# 2. Очистка конфликтующих данных
# Удаляем записи, которые могли создаться автоматически (например, при migrate),
# чтобы они не конфликтовали с данными из дампа.
echo_and_log "Подготовка базы к импорту..."
$DOCKER_CMD exec -T autocaller python3 manage.py shell -c "from django.contrib.auth.models import User; User.objects.all().delete()"

# 3. Загружаем данные (используем поток через дефис '-')
echo_and_log "Загрузка данных из JSON..."
if [ -f "$TARGET_DIR/data.json" ]; then
    cat "$TARGET_DIR/data.json" | $DOCKER_CMD exec -T autocaller python3 manage.py loaddata --format=json -
else
    echo_and_log "ОШИБКА: Файл $TARGET_DIR/data.json не найден для импорта!"
fi

# 4. Сброс последовательностей ID (исправлено для автоматического определения приложений)
echo_and_log "Сброс последовательностей ID..."
$DOCKER_CMD exec -T autocaller /bin/bash -c "python3 manage.py sqlsequencereset auth autocaller | python3 manage.py dbshell"

echo_and_log "Сбор статики Django..."
docker compose exec -T autocaller python3 manage.py collectstatic --no-input

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