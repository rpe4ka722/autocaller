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

# Настройка браузера (Firefox)
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



# Переход в целевую директорию
cd "$TARGET_DIR" || { echo_and_log "ОШИБКА: Не удалось перейти в $TARGET_DIR"; exit 1; }

# Функция копирования с логгированием
copy_with_log() {
    if [ -e "$1" ]; then
        cp -r "$1" "$2" && echo_and_log "УСПЕХ: $3 скопированы" || echo_and_log "ОШИБКА: Копирование $3"
    else
        echo_and_log "ПРЕДУПРЕЖДЕНИЕ: $3 не найдены ($1)"
    fi
}



# --- ЭКСПОРТ ДАННЫХ ИЗ СТАРОГО КОНТЕЙНЕРА ---
OLD_CONTAINER_ID=$(docker ps -q --filter "name=django-app" | head -n 1)

if [ -n "$OLD_CONTAINER_ID" ]; then
    echo_and_log "Старый контейнер обнаружен (ID: $OLD_CONTAINER_ID). Делаем дамп..."
    
    # Выполняем дамп. Используем -i для сохранения потока данных
    docker exec -i "$OLD_CONTAINER_ID" python3 manage.py dumpdata \
        --exclude auth.permission \
        --exclude contenttypes \
        --exclude admin.logentry \
        --exclude sessions \
        > "$TARGET_DIR/data.json"

    # Проверяем: успешно ли завершилась команда и не пустой ли файл
    if [ $? -eq 0 ] && [ -s "$TARGET_DIR/data.json" ]; then
        echo_and_log "УСПЕХ: Дамп базы сохранен в $TARGET_DIR/data.json"
    else
        echo_and_log "ОШИБКА: Дамп создать не удалось или данных нет. Проверьте логи контейнера."
        # Удаляем пустой файл, чтобы он не мешал импорту
        rm -f "$TARGET_DIR/data.json"
    fi
else
    echo_and_log "ПРЕДУПРЕЖДЕНИЕ: Работающий контейнер 'django-app' не найден."
fi


# Добавление настроек подключения к базе данных в .env
ENV_FILE="/opt/autocaller/django-files/.env"

if ! grep -q "POSTGRES_DB" "$ENV_FILE"; then
    echo "POSTGRES_DB=autocaller_db" >> "$ENV_FILE"
    echo "POSTGRES_USER=autocaller" >> "$ENV_FILE"
    echo "POSTGRES_PASSWORD=autocaller" >> "$ENV_FILE"
    echo "POSTGRES_HOST=db" >> "$ENV_FILE"
    echo "POSTGRES_PORT=5432" >> "$ENV_FILE"
    echo_and_log "Параметры базы данных внесены в конфиг."
else
    echo_and_log "Параметры базы данных уже присутствуют в конфиге."
fi

# Добавление настроек config.ini
CONF_FILE="/opt/autocaller/django-files/config.ini"

if ! grep -q "list_call_time_limit" "$CONF_FILE"; then
    echo "list_call_time_limit = 1200" >> "$CONF_FILE"
    echo_and_log "Параметры приложения внесены в конфиг."
else
    echo_and_log "Параметры приложения уже присутствуют в конфиге."
fi

# Копирование нового файла docker-compose.yml
copy_with_log "$SCRIPT_DIR/docker-compose.yml" "$TARGET_DIR/" "docker-compose.yml"


# 3. Работа с Docker образами
if [ -f "$SCRIPT_DIR/autocaller.tar" ]; then
    echo_and_log "Загрузка нового образа autocaller"
    docker load -i "$SCRIPT_DIR/autocaller.tar" || { echo_and_log "ОШИБКА: Образ не загружен"; exit 1; }
    
    echo_and_log "Очистка старых образов..."
    docker image prune -f >/dev/null 2>&1
else
    echo_and_log "ОШИБКА: Файл autocaller.tar не найден!"
    exit 1
fi

if [ -f "$SCRIPT_DIR/postgres.tar" ]; then
    if docker images --format "{{.Repository}}" | grep -q "postgres"; then
        echo_and_log "Загрузка образа postgres не требуется"
    else 
        echo_and_log "Загрузка нового образа postgres"
        docker load -i "$SCRIPT_DIR/postgres.tar" || { echo_and_log "ОШИБКА: Образ не загружен"; exit 1; }
    fi
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

    # Дополнительная проверка: если папка тома все еще существует, удаляем её принудительно
    if [ -d "/var/lib/docker/volumes/autocaller_static_volume" ]; then
        echo_and_log "ПРЕДУПРЕЖДЕНИЕ: Том не удалился автоматически. Принудительная очистка..."
        sudo rm -rf /var/lib/docker/volumes/autocaller_static_volume
    fi

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
$DOCKER_CMD exec -T autocaller python3 manage.py shell -c "from django.contrib.auth import get_user_model; get_user_model().objects.all().delete()"

# 3. Загружаем данные в новую базу
echo_and_log "Загрузка данных из JSON..."

if [ -f "$TARGET_DIR/data.json" ]; then
    # Передаем содержимое файла через пайп прямо в команду внутри контейнера
    cat "$TARGET_DIR/data.json" | $DOCKER_CMD exec -i -T autocaller python3 manage.py loaddata --format=json -
    
    if [ $? -eq 0 ]; then
        echo_and_log "УСПЕХ: Данные из JSON загружены в базу."
    else
        echo_and_log "ОШИБКА: loaddata не смогла обработать данные. Проверьте JSON."
    fi
else
    echo_and_log "ОШИБКА: Файл $TARGET_DIR/data.json не найден на хосте!"
fi

# 4. Сброс последовательностей ID (исправлено для автоматического определения приложений)
echo_and_log "Сброс последовательностей ID..."
RESET_SCRIPT="
from django.core.management.color import no_style
from django.db import connection
from django.apps import apps

# Явно берем конфиги нужных приложений
labels = ['auth', 'autocaller']
app_configs = [apps.get_app_config(l) for l in labels if apps.is_installed(l)]

statements = connection.ops.sequence_reset_sql(no_style(), app_configs)
with connection.cursor() as cursor:
    for sql in statements:
        cursor.execute(sql)
"
$DOCKER_CMD exec -i autocaller python3 manage.py shell -c "$RESET_SCRIPT"

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