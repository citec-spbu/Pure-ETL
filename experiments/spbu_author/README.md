# Анализ публикаций преподавателей СПбГУ

Jupyter-ноутбук для библиометрического анализа публикационной активности 8 преподавателей СПбГУ. Данные получены из [OpenAlex.org](https://openalex.org) и загружаются через библиотеку `litstudy`. Ноутбук строит граф соавторства и выделяет топ тем исследований.

---

## Структура проекта

+```text
project/
└── experiments/
    └── spbu_author/
        ├── spbu_author.ipynb
        └── data/            
           ├── works-csv-Drivotin.csv  
           ├── works-csv-Blekanov.csv
           ├── works-csv-Vakaeva.csv  
           ├── works-csv-Kostyrko.csv   
           ├── works-csv-Grekov.csv  
           ├── works-csv-Lejnina.csv   
           ├── works-csv-Krylatov.csv  
           └── works-csv-Kizhaeva.csv  
```

Все CSV-файлы должны лежать **в папке data**.

---

## Зависимости

```bash
pip install litstudy pyvis pandas matplotlib numpy
```

| Библиотека | Назначение                                 |
|---|--------------------------------------------|
| `litstudy` | загрузка CSV, построение графа соавторства |
| `pyvis` | интерактивная визуализация графа в Jupyter |
| `pandas` | чтение и объединение CSV-файлов            |
| `matplotlib` | построение графика тем                     |
| `numpy` | генерация цветовой шкалы для графика тем   |

---

## Структура ноутбука

### Ячейка 1 — Импорт библиотек
Подключает `pandas`, `matplotlib`, `litstudy`, `Counter`, `numpy`.

### Ячейка 2 — Загрузка данных

Определяет список из 8 преподавателей и соответствующих CSV-файлов. Каждый CSV читается **отдельно** через `pd.read_csv()` в словарь `dfs_per_author` — это позволяет корректно считать число публикаций каждого автора без потерь.

Затем каждый файл загружается через `litstudy.load_csv()` с явным указанием полей:

```python
litstudy.load_csv(f,
    title_field='display_name',
    authors_field='authorships.author.display_name',
    citation_field='cited_by_count',
    date_field='publication_date',
    source_field='primary_location.source.display_name'
)
```

Все `DocumentSet`-ы объединяются оператором `|` в один `combined`.

### Ячейка 3 — Граф соавторства (текстовый вывод)

Строит граф через `litstudy.build_coauthor_network(combined)` и выводит топ-15 пар авторов по числу совместных публикаций:

```text
Blekanov - Bodrunova  24 совм. публ.
Zakharov - Krylatov  20 совм. публ.
...
```

### Ячейка 4 — Граф соавторства (визуализация)

Рендерит интерактивный граф через `litstudy.plot_network()` — отображается прямо в Jupyter. Узлы можно перетаскивать и масштабировать колёсиком мыши.

Параметры:

| Параметр | Значение | Описание |
|---|---|---|
| `height` | `'600px'` | высота области графа |
| `max_node_size` | `60` | максимальный размер узла |
| `min_node_size` | `10` | минимальный размер узла |
| `largest_component` | `False` | показывать все компоненты |
| `gravity` | `2` | сила притяжения узлов |

> Граф работает только в браузере (Jupyter Notebook / JupyterLab). В PyCharm нужно запустить `jupyter notebook` и открыть ноутбук по адресу `http://localhost:8888`.

### Ячейка 5 — Тематический анализ

Объединяет все CSV через `pd.concat` + `drop_duplicates` и считает частоту поля `primary_topic.display_name` — готовой темы, которую OpenAlex присвоил каждой статье. Выводит:

- топ-10 тем по всем 8 преподавателям
- топ-3 темы отдельно для каждого автора
- горизонтальный график топ-10 тем, сохранённый в `topics_openalex.png`

---

## Выходные файлы

| Файл | Описание |
|---|---|
| `topics_openalex.png` | график топ-10 тем преподавателей |

---

## Анализируемые преподаватели

| Автор |
|---|
| Oleg I. Drivotin |
| Ivan S. Blekanov |
| Aleksandra B. Vakaeva |
| Sergey A. Kostyrko |
| Mikhail A. Grekov |
| E. A. Lejnina |
| Alexander Krylatov |
| Natalia Kizhaeva |

**Источник данных:** [OpenAlex.org](https://openalex.org) — открытая база научных публикаций.
