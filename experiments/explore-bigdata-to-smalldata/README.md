# Фильтрация данных SciSciNet через DuckDB

## Описание

Скрипт `build_faculty_csv.py` выполняет потоковую фильтрацию данных из датасета [Northwestern-CSSI/sciscinet-v2](https://huggingface.co/datasets/Northwestern-CSSI/sciscinet-v2) на HuggingFace напрямую через DuckDB, без полной загрузки файлов на диск.

Результат — CSV-файл со статьями сотрудников заданного университета начиная с 2015 года.

## Запуск

```bash
python build_faculty_csv.py t=hf_...
```

Токен можно получить в настройках аккаунта на [huggingface.co](https://huggingface.co/settings/tokens).

Альтернативно — задать переменную окружения `HUGGING_FACE_TOKEN` и запускать без аргумента:

```bash
# Linux / macOS
export HUGGING_FACE_TOKEN=hf_...
python build_faculty_csv.py

# Windows (PowerShell)
$env:HUGGING_FACE_TOKEN = "hf_..."
python build_faculty_csv.py
```

## Настройка

В начале скрипта задайте `INSTITUTION_ID` — идентификатор университета в OpenAlex (совпадает с SciSciNet-v2):

```python
INSTITUTION_ID = "I172901346"  # СПбГУ
```

ID можно найти на [openalex.org](https://openalex.org/institutions).

## Зависимости

```bash
pip install duckdb
```
