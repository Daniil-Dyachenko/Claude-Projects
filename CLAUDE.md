# Energy_System_Diploma — Система моніторингу енергоспоживання

## Опис проєкту
### Тема: 
Система моніторингу та оптимізації енергоспоживання з клієнт-серверною 
архітектурою та використання веб інтерфейсу.

### Вимоги, які повинні бути реалізовані:
Реалізація програмного забезпечення, архітектури клієнт-сервер,(взаємодія компонентів між собою)  API, 
бази даних(зберігання та обробка даних), безпека та контроль доступу(щоб зловмисник не міг вмикати або вимакати якісь прибори, перехоплювати дані. 
IoT(плата STM32 яка через MQTT передає дані на сервер).

### Фукнціонал:

1. Апаратний модуль (ESP32 у Wokwi)
IoT-плата (ESP32/Wokwi) через HTTP передає дані на Django-сервер.
Цей модуль відповідає за взаємодію з фізичним світом (сенсорами та виконавчими пристроями).

- Збір телеметрії: Безперервне зчитування аналогового сигналу (емуляція датчика струму через потенціометр) та конвертація його у значення спожитої потужності (Ватти).

- Відправка даних (Uplink): Формування JSON-пакетів із поточним споживанням та їх відправка на сервер через HTTP POST-запити кожні 3-5 секунд.

- Прийом команд (Downlink): Періодичне опитування сервера (GET-запити) для отримання актуального стану реле.

- Керування навантаженням: Увімкнення або вимкнення відповідних пінів (світлодіодів/реле) на основі отриманих від сервера команд.

2. Серверний модуль та API (Backend на Django)
Це "мозок" системи, який забезпечує організацію обчислювальних процесів та взаємодію компонентів мережі.

- REST API для IoT: Прийом телеметрії від мікроконтролера, її валідація та збереження в базу даних.
- REST API для Клієнта: Віддача агрегованих історичних даних для побудови графіків та прийом нових налаштувань (лімітів, пріоритетів) від користувача.
- Модуль безпеки: Перевірка статичних API-ключів (токенів) пристроїв для захисту від несанкціонованої відправки даних.
- Робота з Базою Даних (PostgreSQL): Збереження конфігурацій пристроїв та масивів часових рядів (логів споживання) для ІТ-інфраструктури.

3. Модуль бізнес-логіки (Алгоритм балансування)
Виконується на сервері при кожному отриманні нових даних від ESP32.

- Розрахунок загального навантаження: Сумування поточного споживання всіх активних пристроїв у мережі.
- Порівняння з лімітом: Перевірка, чи не перевищує сумарне навантаження заданий користувачем або системою поріг (наприклад, 3000 Вт).
- Пріоритетне відключення: Якщо виявлено перевантаження, алгоритм знаходить увімкнений прилад із найнижчим пріоритетом і автоматично змінює його статус у базі даних на "Вимкнено", щоб при наступному запиті ESP32 фізично розірвала ланцюг живлення.

4. Клієнтський веб-інтерфейс (Frontend)
Інтерфейс для візуалізації даних та моніторингу. Користувач керує пристроями через веб-інтерфейс.

- Дашборд реального часу: Відображення поточного загального споживання енергії (цифровий індикатор, що оновлюється асинхронно через JS Fetch).
- Графіки споживання: Побудова лінійних графіків (за допомогою Chart.js) на основі історії за останні хвилини/години для наочного аналізу навантаження.
- Керування конфігурацією: Форма, де користувач може встановити глобальний ліміт споживання (наприклад, "Режим роботи від генератора: Макс 2 кВт").
- Керування приладами: Список підключених пристроїв, де користувач може вручну їх вмикати/вимикати, а також змінювати їхній пріоритет (наприклад, призначити холодильнику пріоритет "1", а бойлеру "3").

5. Панель адміністратора (Back-office)
Вбудований функціонал Django для керування системою на рівні інженера.

- CRUD пристроїв: Можливість додавати нові мікроконтролери та реле в систему, редагувати їхні унікальні ідентифікатори.

- Аудит телеметрії: Перегляд "сирих" логів (Raw Data), які надсилає ESP32, для діагностики помилок та тестування.

- Керування користувачами: Створення акаунтів доступу до веб-інтерфейсу, скидання паролів.

## Стек
- Python 3.10 + Django 5 + Django REST Framework
- PostgreSQL  + Django ORM
- Контейнеризація: Docker та Docker Compose
- HTML/CSS + vanilla JS + Chart.js
- ESP32 емульований у Wokwi (C++)
- Ngrok для публічного доступу до localhost
- python-dotenv для зберігання секретних ключів та паролів до бази даних у файлі .env, щоб вони не потрапили у відкритий код.
- Тестування API: Postman
- Проєктування БД: DBeaver або вбудовані засоби IDE для генерації красивих ER-діаграм, які підуть у пояснювальну записку.
- 
## Структура проєкт
- `config/` — налаштування Django (settings, urls, wsgi, asgi)
- `main/` — головний додаток (моделі, API, бізнес-логіка)
- `templates/` — HTML шаблони
- `static/` — CSS, JS
- `tests/` — стрес-тести

## Моделі БД
- `Device` — пристрій (назва, пріоритет 1-10, статус увімк/вимк)
- `Telemetry` — лог вимірювань (device FK, потужність у Ватах, timestamp)
- `SystemSettings` — глобальні налаштування (ліміт потужності у Ватах)

## API ендпоінти
### Для ESP32:
- POST /api/telemetry/ — надсилання даних з датчика кожні 5 сек
- GET /api/device-state/ — перевірка статусу реле

### Для веб-інтерфейсу:
- GET /api/chart-data/ — дані для графіків Chart.js
- POST /api/settings/ — зміна лімітів та пріоритетів

## Безпека
- Статичний API-токен у заголовку X-API-Key для запитів від ESP32
- Перевірка токена у permissions.py

## Головна бізнес-логіка (services.py)
Алгоритм балансування навантаження:
1. При отриманні телеметрії — рахуємо сумарну потужність всіх пристроїв
2. Якщо сума > ліміт — вимикаємо пристрій з найнижчим пріоритетом
3. Якщо сума < ліміт і є вимкнені пристрої — вмикаємо найвищий пріоритет

## Правила розробки
- Всі коментарі та назви змінних — англійською
- Міграції тільки через python manage.py makemigrations
- Секрети тільки через .env файл (не хардкодити!)ы

## Етапи розробки
Етап 1 — Інфраструктура та база даних (Docker, PostgreSQL, Django)
Етап 2 - REST API та бізнес-логіка
Етап 3 - IoT (ESP32, Wokwi)
Етап 4 - Фронтенд, інтерфейс користувача (Chart.js, панель керування)
Етап 5 - Безпека та тестування

## Поточний етап
Етап 3 - IoT (ESP32, Wokwi)

### Що зробили на Етапі 1
Сервер працює, адмінка піднята на http://localhost:8000/admin/.

  Credentials суперюзера:
  - Username: admin
  - Password: admin
  - Email: daniil.dyachenko.2018@gmail.com

  - Django_Claude_Project/ → config/ (відповідно до CLAUDE.md)
  - Створено main додаток, моделі Device, Telemetry, SystemSettings (main/models.py:1)
  - Зареєстровано в адмінці з list_filter, list_editable, date_hierarchy (main/admin.py:1)
  - requirements.txt (Django 5.2, DRF, psycopg2, dotenv, gunicorn)
  - Dockerfile (Python 3.10-slim) + .dockerignore
  - .env з усіма секретами + .env.example як шаблон
  - settings.py повністю переписано: env-driven SECRET_KEY/DEBUG/ALLOWED_HOSTS/DB, PostgreSQL замість SQLite, додані rest_framework + main, TIME_ZONE='Europe/Kyiv'
  - Міграції згенеровано (main/migrations/0001_initial.py) і накочено в Postgres
  - Зробили відповідний коміт по Етапу 1.

### Що зробили на Етапі 2
REST API + бізнес-логіка готові. Усі ендпоінти відповідають через `docker compose`.

  Що було додано:
  - **Модель Device** розширена двома полями: `last_power_watts` (останнє значення з телеметрії) та `last_seen_at` (час останнього пакета). Міграція `main/migrations/0002_device_last_power_watts_device_last_seen_at.py`.
  - **main/serializers.py** — DeviceSerializer (CRUD), DeviceStateSerializer (downlink для ESP32 — тільки `device_id` + `is_on`), TelemetryIngestSerializer (uplink з валідацією device_id → Device), TelemetryReadSerializer, SystemSettingsSerializer, ChartDataPointSerializer, CurrentLoadSerializer.
  - **main/permissions.py** — `HasDeviceApiKey` з constant-time `hmac.compare_digest` перевіркою заголовка `X-API-Key` проти `settings.DEVICE_API_KEY`.
  - **main/services.py** — алгоритм балансування:
    - `record_telemetry()` — з `select_for_update`, оновлює `last_power_watts`/`last_seen_at` атомарно.
    - `rebalance_load()` — у транзакції: спочатку shed-фаза (вимикає найнижчий пріоритет поки total > limit), потім restore-фаза з гістерезисом (вмикає back-on вимкнений пристрій ТІЛЬКИ якщо це не штовхне знову за ліміт).
    - `ingest_and_rebalance()` — комбінований entry-point для view.
    - Повертає `BalancingReport` (total, is_overloaded, shed_devices, restored_devices) для діагностики.
    - Логування через `main` logger (INFO/WARNING).
  - **main/views.py**:
    - `POST /api/telemetry/` (X-API-Key required) — приймає uplink + запускає балансування.
    - `GET /api/device-state/` (X-API-Key required) — список усіх або `?device_id=xxx` для одного.
    - `GET /api/chart-data/?minutes=N` — Telemetry агрегована по хвилинам через `TruncMinute` + `Sum`.
    - `GET/POST /api/settings/` — singleton SystemSettings.
    - `GET /api/current-load/` — snapshot для dashboard.
    - `DeviceViewSet` (`/api/devices/`) — повний CRUD + custom action `POST /api/devices/{pk}/toggle/`.
  - **main/urls.py** — DefaultRouter для DeviceViewSet + explicit paths. Підключено в `config/urls.py` під `/api/`.
  - **settings.py**: блок `REST_FRAMEWORK` (JSON+Browsable renderers, PageNumberPagination 50, SessionAuthentication), `LOGGING` для `main`.
  - **main/tests.py** — 14 тестів, усі проходять:
    - TelemetryIngest: відмова без/із неправильним X-API-Key, успішний прийом, валідація device_id/power.
    - DeviceState: lookup single, lookup unknown (404), list all.
    - BalancingAlgorithm: shed-1, shed-багатьох, restore-найвищого-пріоритету, skip-overload-restore, inactive-settings-pause.
    - CurrentLoad: snapshot.
  - Команда тестів: `docker exec energy_web python manage.py test main`.

### API ендпоінти (фінальний контракт Етапу 2)
| Метод | URL | Auth | Призначення |
|---|---|---|---|
| POST | `/api/telemetry/` | X-API-Key | ESP32 надсилає `{device_id, power_watts}`. Відповідь містить `telemetry` + `balancing` звіт. |
| GET | `/api/device-state/?device_id=` | X-API-Key | ESP32 опитує стан реле (один або всі). |
| GET | `/api/chart-data/?minutes=30` | open | Агреговані дані для Chart.js (timestamp + total_power_watts). |
| GET | `/api/current-load/` | open | Snapshot для дашборда (total, limit, is_overloaded, devices). |
| GET, POST | `/api/settings/` | open | Глобальний ліміт потужності. |
| GET, POST, PUT, PATCH, DELETE | `/api/devices/` | open | CRUD пристроїв. |
| POST | `/api/devices/{pk}/toggle/` | open | Ручне перемикання реле з UI. |

> Open-ендпоінти будуть закриті session/token-auth на Етапі 5.


