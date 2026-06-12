#!/bin/bash

# Настройки логирования
LOG_FILE="/opt/autocaller/autocaller_install.log"



log_message() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $1" | tee -a "$LOG_FILE"
}

# Функция для вывода в терминал и лог
echo_and_log() {
    echo "$1"
    log_message "$1"
}

# Проверка запуска скрипта от имени администратора
if [ "$EUID" -ne 0 ]; then
  echo "Пожалуйста, запустите скрипт от имени администратора (используя sudo)."
  exit 1
fi

xdg-settings set default-web-browser firefox.desktop

# Создаем директорию если не существует
mkdir -p /opt/autocaller
if [ $? -eq 0 ]; then
    echo_and_log "УСПЕХ: Создана директория /opt/autocaller"
else
    echo_and_log "ОШИБКА: Не удалось создать директорию /opt/autocaller"
fi


# Начало установки
echo_and_log "========================================="
echo_and_log "Начало установки Autocaller"
echo_and_log "========================================="

TARGET_BROWSER="firefox.desktop"

# 1. Получаем текущий браузер по умолчанию
CURRENT_BROWSER=$(xdg-settings get default-web-browser)

echo_and_log "Текущий браузер по умолчанию: $CURRENT_BROWSER"

# 2. Проверяем, является ли он Firefox
if [ "$CURRENT_BROWSER" != "$TARGET_BROWSER" ]; then
    echo_and_log "Firefox не является браузером по умолчанию. Исправляем..."
    
    # Пытаемся установить Firefox основным браузером
    xdg-settings set default-web-browser "$TARGET_BROWSER"
    
    # Дополнительная проверка через update-alternatives (для системных вызовов в Debian/Ubuntu)
    if command -v update-alternatives >/dev/null 2>&1; then
        sudo update-alternatives --set x-www-browser /usr/bin/firefox 2>/dev/null
        sudo update-alternatives --set gnome-www-browser /usr/bin/firefox 2>/dev/null
    fi

    # Финальная проверка
    NEW_BROWSER=$(xdg-settings get default-web-browser)
    if [ "$NEW_BROWSER" == "$TARGET_BROWSER" ]; then
        echo_and_log "Успешно! Firefox теперь браузер по умолчанию."
    else
        echo_and_log "Ошибка: Не удалось изменить браузер. Возможно, Firefox не установлен или используется специфическая среда (например, KDE/Plasma)."
    fi
else
    echo_and_log "Firefox уже установлен как браузер по умолчанию. Ничего делать не нужно."
fi

PACKAGE_LIST="packages.txt" # Имя вашего файла со списками пакетов

# Проверяем, существует ли файл
if [ ! -f "$PACKAGE_LIST" ]; then
    echo_and_log "ОШИБКА: Файл '$PACKAGE_LIST' не найден!"
    exit 1
fi

echo_and_log "Начало установки RPM-пакетов..."

# Читаем файл построчно и устанавливаем пакеты
success_packages=0
failed_packages=0

while IFS= read -r package_path || [[ -n "$package_path" ]]; do
    # Убираем возможные пробелы в начале и конце строки
    package_path=$(echo "$package_path" | xargs)

    if [ -n "$package_path" ] && [ -f "$package_path" ]; then
        package_name=$(rpm -qp --queryformat '%{NAME}' "$package_path" 2>/dev/null)

        if [ -z "$package_name" ]; then
            echo_and_log "ОШИБКА: Не удалось прочитать пакет: $package_path"
            ((failed_packages++))
            continue
        fi

        if rpm -q "$package_name" >/dev/null 2>&1; then
            echo_and_log "ИНФО: Пакет '$package_name' уже установлен, пропускаем"
        else
            echo_and_log "Установка: $package_name"
            rpm -ivh "$package_path"
            if [ $? -eq 0 ]; then
                echo_and_log "УСПЕХ: Пакет '$package_name' установлен"
                ((success_packages++))
            else
                echo_and_log "ОШИБКА: Не удалось установить $package_path"
                ((failed_packages++))
            fi
        fi
    elif [ -n "$package_path" ]; then
        echo_and_log "ОШИБКА: Файл не найден: $package_path"
        ((failed_packages++))
    fi
done < "$PACKAGE_LIST"

echo_and_log "Итог установки пакетов: успешно - $success_packages, неудачно - $failed_packages"

# Определение директории рабочего стола
DESKTOP_DIR=""
USER_HOME=""

if [ -n "$SUDO_USER" ]; then
    # Находим его домашнюю директорию
    USER_HOME=$(eval echo ~"$SUDO_USER")
else
    # Если скрипт запущен не через sudo, используем обычный $HOME
    USER_HOME=$HOME
fi


for dir in "$USER_HOME/Desktop" "$USER_HOME/Рабочий стол" "$USER_HOME/desktop"; do
    if [ -d "$dir" ]; then
        DESKTOP_DIR="$dir"
        echo_and_log "Файл $dir"
        break
    fi
done

if [ -z "$DESKTOP_DIR" ]; then
    echo_and_log "ПРЕДУПРЕЖДЕНИЕ: Не удалось найти директорию рабочего стола для пользователя $USER_HOME"
fi

# Проверка и копирование
if [ -n "$DESKTOP_DIR" ] && [ -d "$DESKTOP_DIR" ]; then
    FILE_TO_COPY="autocaller.desktop"
    if [ -f "$FILE_TO_COPY" ]; then
        cp "$FILE_TO_COPY" "$DESKTOP_DIR/"
        echo_and_log "ИНФО: Файл $FILE_TO_COPY успешно скопирован в $DESKTOP_DIR"
    else
        echo_and_log "ПРЕДУПРЕЖДЕНИЕ: Файл $FILE_TO_COPY не найден в текущей директории"
    fi
else
    echo_and_log "ПРЕДУПРЕЖДЕНИЕ: Не удалось определить директорию рабочего стола"
fi

# Запуск и настройка сервисов
echo_and_log "Настройка сервисов..."

# Проверяем, существует ли systemctl
if command -v systemctl >/dev/null 2>&1; then
    # Docker
    if systemctl enable docker.service 2>/dev/null; then
        systemctl start docker.service
        echo_and_log "УСПЕХ: Docker service enabled and started"
    else
        echo_and_log "ОШИБКА: Docker service not found or failed to enable"
    fi

    # Asterisk
    if systemctl enable asterisk 2>/dev/null; then
        systemctl start asterisk
        echo_and_log "УСПЕХ: Asterisk service enabled and started"
    else
        echo_and_log "ОШИБКА: Asterisk service not found or failed to enable"
    fi
else
    echo_and_log "ПРЕДУПРЕЖДЕНИЕ: systemctl не найден (возможно, не systemd дистрибутив)"
fi

# Создание директорий и копирование файлов
echo_and_log "Копирование файлов..."

# Создаем директорию если не существует
mkdir -p /opt/autocaller
if [ $? -eq 0 ]; then
    echo_and_log "УСПЕХ: Создана директория /opt/autocaller"
else
    echo_and_log "ОШИБКА: Не удалось создать директорию /opt/autocaller"
fi

# Функция для копирования с логированием
copy_with_log() {
    local src="$1"
    local dest="$2"
    local desc="$3"
    
    if [ -e "$src" ]; then
        cp -r "$src" "$dest"
        if [ $? -eq 0 ]; then
            echo_and_log "УСПЕХ: $desc скопированы"
            return 0
        else
            echo_and_log "ОШИБКА: Не удалось скопировать $desc"
            return 1
        fi
    else
        echo_and_log "ПРЕДУПРЕЖДЕНИЕ: $desc не найдены ($src)"
        return 2
    fi
}

# Копируем файлы с проверкой их существования
copy_with_log "django-files" "/opt/autocaller/" "django-files"
copy_with_log "media" "/opt/autocaller/" "media"
copy_with_log "nginx" "/opt/autocaller/" "nginx"

if [ -d "asterisk_conf" ]; then
    mkdir -p /etc/asterisk
    cp -r asterisk_conf/* /etc/asterisk/
    echo_and_log "УСПЕХ: Конфигурация asterisk скопирована"
fi

copy_with_log "docker-compose.yml" "/opt/autocaller/" "docker-compose.yml"
copy_with_log "icon.png" "/opt/autocaller/" "иконка"

# Загрузка Docker образов
echo_and_log "Загрузка Docker образов..."

load_docker_image() {
    local image_file="$1"
    local image_name="$2"
    
    if [ -f "$image_file" ]; then
        docker load -i "$image_file"
        if [ $? -eq 0 ]; then
            echo_and_log "УСПЕХ: $image_name образ загружен"
            return 0
        else
            echo_and_log "ОШИБКА: Не удалось загрузить $image_name образ"
            return 1
        fi
    else
        echo_and_log "ОШИБКА: Файл $image_file не найден"
        return 2
    fi
}

load_docker_image "redis.tar" "Redis"
load_docker_image "nginx.tar" "Nginx"
load_docker_image "postgres.tar" "Postgres"
load_docker_image "autocaller.tar" "Autocaller"

# Запуск docker-compose
echo_and_log "Запуск docker-compose..."
cd /opt/autocaller || {
    echo_and_log "ОШИБКА: Не удалось перейти в /opt/autocaller"
    exit 1
}

# Проверяем наличие docker-compose.yml
if [ -f "docker-compose.yml" ]; then
    # Проверяем, установлен ли docker-compose
    if command -v docker-compose >/dev/null 2>&1; then
        docker-compose up -d
        if [ $? -eq 0 ]; then
            echo_and_log "УСПЕХ: Docker-compose успешно запущен"
        else
            echo_and_log "ОШИБКА: Не удалось запустить docker-compose"
        fi
    elif command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
        docker compose up -d
        if [ $? -eq 0 ]; then
            echo_and_log "УСПЕХ: Docker compose успешно запущен"
        else
            echo_and_log "ОШИБКА: Не удалось запустить docker compose"
        fi
    else
        echo_and_log "ОШИБКА: Docker-compose не найден"
    fi
else
    echo_and_log "ОШИБКА: Файл docker-compose.yml не найден"
fi

# Ожидание запуска базы данных и выполнение миграций
echo_and_log "Ожидание запуска базы данных для выполнения миграций..."
sleep 10 # Даем время Postgres инициализироваться

if docker compose exec -T autocaller python3 manage.py migrate --no-input; then
    echo_and_log "УСПЕХ: Миграции базы данных выполнены"
else
    echo_and_log "ОШИБКА: Не удалось выполнить миграции"
fi

# Создание суперпользователя (администратора)
echo_and_log "Создание администратора Django..."

# Задаем данные админа (можно вынести в .env)
ADMIN_USER="admin"
ADMIN_EMAIL="admin@example.com"
ADMIN_PASS="12345root"
ADMIN_DEPARTMENT="ALL"

docker compose exec -T autocaller python3 manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(username='$ADMIN_USER').exists():
    User.objects.create_superuser(
        username='$ADMIN_USER', 
        email='$ADMIN_EMAIL', 
        password='$ADMIN_PASS',
    )
    print('Суперпользователь успешно создан.')
else:
    print('Суперпользователь уже существует.')
" | tee -a "$LOG_FILE"

echo_and_log "Сбор статики Django..."
docker compose exec -T autocaller python3 manage.py collectstatic --no-input

# Изменение прав
echo_and_log "Изменение прав для папки autocaller..."
chmod -R 777 /opt/autocaller
if [ $? -eq 0 ]; then
    echo_and_log "УСПЕХ: Права изменены для папки autocaller"
else
    echo_and_log "ОШИБКА: Не удалось изменить права для папки autocaller"
fi

# Запрос перезагрузки
echo ""
echo "========================================="
echo "Установка завершена!"
echo "Лог сохранен в: $LOG_FILE"
echo "========================================="
echo ""
echo "Требуется перезагрузка системы для применения всех изменений."
read -p "Перезагрузить сейчас? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Перезагрузка через 10 секунд... Нажмите Ctrl+C для отмены."
    for i in {10..1}; do
        echo -ne "Перезагрузка через $i секунд...\r"
        sleep 1
    done
    echo_and_log "Инициирована перезагрузка системы"
    systemctl reboot
else
    echo "Перезагрузка отменена. Не забудьте перезагрузить систему вручную."
    echo_and_log "Перезагрузка отменена пользователем"
fi
