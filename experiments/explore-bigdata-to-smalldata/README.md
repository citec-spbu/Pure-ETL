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

## Запуск

```bash
python build_faculty_csv.py
```
