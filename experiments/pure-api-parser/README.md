# Парсинг научных публикаций через Pure API СПбГУ

Python-скрипт для получения и обработки научных публикаций из REST API системы Pure СПбГУ.
Программа отправляет GET-запросы к API, получает JSON-ответы с публикациями, обрабатывает данные и сохраняет результат в JSON и CSV.

---

## Зависимости

```bash
pip install requests pandas
```

| Библиотека | Назначение |
|---|---|
| `requests` | отправка HTTP GET-запросов к REST API |
| `pandas` | сохранение данных в CSV |
| `json` | работа с JSON-ответами API |
| `logging` | логирование процесса загрузки |

---

## Используемый endpoint

```text
/research-outputs
```

## Структура программы

### Блок 1 — Импорт библиотек

Подключаются:

- `requests`
- `pandas`
- `json`
- `logging`
- `typing`

---

### Блок 2 — Настройка API

Указываются:

- базовый URL API;
- endpoint;
- API token;
- размер страницы;
- количество публикаций.

```python
BASE_URL = "https://pure.spbu.ru"

RESEARCH_OUTPUTS_ENDPOINT = "/research-outputs"

TARGET_PUBLICATIONS = 50
```

---

### Блок 3 — Создание headers

Функция `get_headers()` создаёт HTTP headers для запроса.

Используются:

```python
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}
```

Если API требует авторизацию:

```python
headers["api-key"] = API_TOKEN
```

---

### Блок 4 — Отправка GET-запроса

Функция `send_get_request()`:

- отправляет GET-запрос;
- передаёт query parameters;
- проверяет status code;
- обрабатывает ошибки;
- возвращает JSON.

---

### Блок 5 

Pure API возвращает данные страницами.

Используются параметры:

```python
params = {
    "size": 25,
    "offset": 0
}
```

Следующая страница:

```python
offset += PAGE_SIZE
```

---

### Блок 6 — Разбор JSON-ответа

Функция `parse_research_output()` извлекает:

- название статьи;
- авторов;
- DOI;
- год публикации;
- аннотацию.

---

### Блок 7 — Сохранение данных

Функция `save_to_json()` сохраняет результат в JSON.

Функция `save_to_csv()` сохраняет результат в CSV через `pandas`.

## Выходные файлы

| Файл | Описание |
|---|---|
| `publications.json` | публикации в формате JSON |
| `publications.csv` | публикации в формате CSV |

---

## Настройка проекта

### API token

Во многих инсталляциях Pure API требует авторизацию.

Токен указывается в коде:

```python
API_TOKEN = "YOUR_API_TOKEN"
```

---

### UUID подразделения

Для загрузки публикаций факультета используется UUID подразделения:

```python
ORGANISATION_ID = "YOUR_ORGANISATION_UUID"
```

---

### UUID автора

Для загрузки публикаций конкретного автора:

```python
PERSON_ID = "YOUR_PERSON_UUID"
```

---

## Обработка ошибок

В проекте реализована обработка:

| Ошибка | Причина |
|---|---|
| `401 Unauthorized` | отсутствует API token |
| `404 Not Found` | неверный endpoint |
| `Timeout` | медленный ответ сервера |
| `ConnectionError` | проблемы с соединением |

---

## Особенности проекта

Во время тестирования было установлено, что Pure API СПбГУ требует закрытый API token.

Поскольку публичный доступ ограничен:

- проект реализован в универсальном виде;
- поддерживается работа с реальным API;
- при наличии token код запускается без изменений.



