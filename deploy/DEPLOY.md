# Развёртывание бота на VPS (Ubuntu 24.04, без Docker)

Инструкция для сервера, где уже работает VPN. Бот работает через long polling
(только исходящие соединения, портов не открывает), поэтому **с VPN не конфликтует**.

Все команды выполняются на сервере по SSH. `sudo` — от обычного пользователя,
либо убери `sudo`, если ты root.

---

## 1. Установить системные пакеты

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

Проверь версию (должно быть 3.11+):

```bash
python3 --version
```

## 2. Создать отдельного пользователя для бота

Так бот изолирован от VPN и системы.

```bash
sudo useradd --system --create-home --home-dir /opt/barberbot --shell /usr/sbin/nologin barberbot
```

## 3. Загрузить код в /opt/barberbot/bot_manik

**Вариант А — через Git (рекомендуется):** сначала запушь проект на GitHub, затем:

```bash
sudo -u barberbot git clone https://github.com/USERNAME/REPO.git /opt/barberbot/bot_manik
```

**Вариант Б — скопировать с локального компьютера** (выполняется НА ТВОЁМ компьютере):

```bash
# заранее исключи venv и базу, чтобы не тащить лишнее
scp -r ~/Desktop/bot_manik USER@SERVER_IP:/tmp/bot_manik
# затем на сервере:
sudo mv /tmp/bot_manik /opt/barberbot/bot_manik
sudo chown -R barberbot:barberbot /opt/barberbot/bot_manik
```

## 4. Создать виртуальное окружение и установить зависимости

```bash
cd /opt/barberbot/bot_manik
sudo -u barberbot python3 -m venv venv
sudo -u barberbot venv/bin/pip install --upgrade pip
sudo -u barberbot venv/bin/pip install -r requirements.txt
```

## 5. Настроить .env

```bash
sudo -u barberbot cp .env.example .env
sudo -u barberbot nano .env      # впиши BOT_TOKEN и ADMIN_ID, сохрани (Ctrl+O, Enter, Ctrl+X)
sudo chmod 600 .env              # токен виден только владельцу
```

(Опционально) залей демо-данные для показа:

```bash
sudo -u barberbot venv/bin/python -m scripts.seed_demo
```

## 6. Установить systemd-сервис

```bash
sudo cp deploy/barberbot.service /etc/systemd/system/barberbot.service
sudo systemctl daemon-reload
sudo systemctl enable --now barberbot
```

## 7. Проверить, что работает

```bash
sudo systemctl status barberbot        # должно быть active (running)
sudo journalctl -u barberbot -f        # живые логи; ждём строку "Бот запущен"
```

Теперь напиши боту `/start` в Telegram — он ответит. VPN продолжает работать как раньше.

---

## Управление ботом

```bash
sudo systemctl restart barberbot   # перезапустить
sudo systemctl stop barberbot      # остановить
sudo systemctl start barberbot     # запустить
sudo journalctl -u barberbot -n 100 --no-pager   # последние 100 строк логов
```

## Обновление кода (если ставил через Git)

```bash
cd /opt/barberbot/bot_manik
sudo -u barberbot git pull
sudo -u barberbot venv/bin/pip install -r requirements.txt   # если менялись зависимости
sudo systemctl restart barberbot
```

---

## Заметки для слабого VPS

- 2 ГБ RAM хватает: бот в простое ест ~60–120 МБ. В юните стоит `MemoryMax=300M` как страховка.
- База `barbershop.db` лежит рядом с кодом и переживает перезапуски. Для бэкапа просто копируй этот файл:
  ```bash
  sudo cp /opt/barberbot/bot_manik/barbershop.db ~/barbershop-backup.db
  ```
- Если вдруг памяти в обрез (одновременно тяжёлый VPN), добавь swap 1 ГБ:
  ```bash
  sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile
  sudo mkswap /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  ```
