# Фильтрация данных SciSciNet через DuckDB

## Описание

Скрипт `build_faculty_csv.py` выполняет потоковую фильтрацию данных из датасета [Northwestern-CSSI/sciscinet-v2](https://huggingface.co/datasets/Northwestern-CSSI/sciscinet-v2) на HuggingFace напрямую через DuckDB, без полной загрузки файлов на диск.

Результат — CSV-файл со статьями сотрудников заданного университета начиная с 2015 года.

## Настройка

В файле `build_faculty_csv.py` на строке 6 необходимо вставить свой HuggingFace токен:

```python
con.execute("CREATE SECRET (TYPE HUGGINGFACE, TOKEN 'ваш_токен_здесь');")
```

Токен можно получить в настройках аккаунта на [huggingface.co](https://huggingface.co/settings/tokens).
# find_aff_id.py

Скрипт извлекает статьи, опубликованные авторами заданного университета, из локального среза базы SciSciNet-v2 и сохраняет результат в CSV.

## Что делает

1. Читает `data/sciscinet_paper_author_affiliation.parquet` и оставляет только записи с нужным `institutionid`.
2. Группирует авторов: одна строка на пару `(paperid, institutionid)`, все `authorid` собираются в список.
3. Джойнит с `sciscinet_papers.parquet` по `paperid`, добавляя столбец `year`.
4. Отбирает статьи начиная с 2015 года.
5. Сохраняет результат в `faculty_papers.csv`.

## Структура выходного файла

| Столбец | Описание |
|---|---|
| `paperid` | Идентификатор статьи (OpenAlex) |
| `institutionid` | Идентификатор университета (OpenAlex) |
| `authorids` | Список авторов статьи из данного университета |
| `year` | Год публикации |

## Входные данные

| Файл | Описание |
|---|---|
| `data/sciscinet_paper_author_affiliation.parquet` | Таблица связей автор–статья–аффилиация из SciSciNet-v2 |
| `sciscinet_papers.parquet` | Метаданные статей (год, DOI, цитирования и др.) из SciSciNet-v2 |

## Настройка

В начале скрипта задайте `INSTITUTION_ID` — идентификатор университета в OpenAlex (совпадает с SciSciNet-v2):

```python
INSTITUTION_ID = "I172901346"  # СПбГУ
```

ID можно найти на [openalex.org](https://openalex.org/institutions).

## Зависимости

```
duckdb
pyarrow
requests
```

```bash
pip install duckdb pyarrow requests
```

## Запуск

```bash
cd experiments/explore-bigdata-to-smalldata
python build_faculty_csv.py
```
