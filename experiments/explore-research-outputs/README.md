# Анализ Research Outputs

## Описание

Данный репозиторий содержит код, написанный в ходе изучения данных из `research-outputs`, с использованием Swagger документации инстанса Pure API в СПБГУ.

Основная цель - сопоставить поля, указанные в схеме спецификации, с фактически получаемыми, которые есть в тестовой выгрузке GET-запроса на `/research-outputs`.

Весь отчет (текст + код) представлен в трех Jupyter-ноутбуках, расположенных в папке `notebooks`:

- `res-output-freqs.ipynb` можно расценивать как входную точку; описывает основной процесс изучения данных из `research-outputs.json`
- `classification.ipynb` содержит быструю разведку классификаций из `classification-schemes.json`, с упором на определение связей с `research-outputs.json`
- `person-org-associations.ipynb` содержит быструю разведку связей `research-output` с `person` и `organisational-unit`, используя описания схем swagger-файла

Дополнительные функции для переиспользования размещены в `notebooks/utils.py`.
