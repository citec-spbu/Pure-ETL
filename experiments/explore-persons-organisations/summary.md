# Выборочное исследование данных

## Упрощение чтения

Сами по себе json'ы очень сложные для простого человеческого чтения.
Структуры очень вложенные, но хотелось бы понять, какие top level атрибуты есть у каждой сущности.

Сформируем набор файлов с постфиксом `_keys`, для того, чтобы иметь представление о том, какие атрибуты есть у каждой сущности.


```python
# imports
import os
import json
import json_utils
from pathlib import Path
```


```python
def prepare_for_serialization(value: dict) -> dict:
    serialized_data = {}

    for key, value in value.items():
        if isinstance(value, set):
            class_obj = next(iter(value))
            type_name = class_obj.__name__  # extract just 'int', 'str', etc.
            serialized_data[key] = type_name
    
    return serialized_data

def generate_compact_entity_preview(input_path: str, artifacts_path: str):
    os.makedirs(artifacts_path, exist_ok=True)
    # Get all files in folder
    for filename in os.listdir(input_path):
        file_path = os.path.join(input_path, filename)
        
        # Check if it's a file (not a subfolder)
        if os.path.isfile(file_path):
            entity_top_level_keys = json_utils.describe_entity_from_json(file_path)
            entity_keys_serialized = prepare_for_serialization(entity_top_level_keys)

            # Save to new file
            output_filename = f"{os.path.splitext(filename)[0]}_keys.json"
            output_path = os.path.join(artifacts_path, output_filename)
            
            with open(output_path, 'w') as f:
                f.write(json.dumps(entity_keys_serialized, indent=2))
            
            print(f"Processed: {filename} -> {output_filename}")
```


```python
# define path constants
INPUT_DATA_PATH = '../data'
ARTIFACTS_DATA_PATH = '../artifacts/structures'
```


```python
generate_compact_entity_preview(input_path=INPUT_DATA_PATH, artifacts_path=ARTIFACTS_DATA_PATH)
```

    Processed: datasets.json -> datasets_keys.json
    Processed: press-media.json -> press-media_keys.json
    Processed: courses.json -> courses_keys.json
    Processed: external-organisations.json -> external-organisations_keys.json
    Processed: award-milestones.json -> award-milestones_keys.json
    Processed: funding-opportunities.json -> funding-opportunities_keys.json
    Processed: author-collaborations.json -> author-collaborations_keys.json
    Processed: equipments.json -> equipments_keys.json
    Processed: curricula-vitae.json -> curricula-vitae_keys.json
    Processed: external-persons.json -> external-persons_keys.json
    Processed: impacts.json -> impacts_keys.json
    Processed: classification-schemes.json -> classification-schemes_keys.json
    Processed: journals.json -> journals_keys.json
    Processed: prizes.json -> prizes_keys.json
    Processed: awards.json -> awards_keys.json
    Processed: semantic-groups.json -> semantic-groups_keys.json
    Processed: fingerprints.json -> fingerprints_keys.json
    Processed: activities.json -> activities_keys.json
    Processed: organisational-units.json -> organisational-units_keys.json
    Processed: research-outputs.json -> research-outputs_keys.json
    Processed: applications.json -> applications_keys.json
    Processed: persons.json -> persons_keys.json
    Processed: student-theses.json -> student-theses_keys.json
    Processed: ethical-reviews.json -> ethical-reviews_keys.json
    Processed: projects.json -> projects_keys.json
    Processed: publishers.json -> publishers_keys.json
    Processed: thesauri.json -> thesauri_keys.json
    Processed: events.json -> events_keys.json
    Processed: concepts.json -> concepts_keys.json


## Постановка задачи

Сущностей очень много.
Нужно попытаться понять, можем ли мы на таком наборе данных соединять разные сущности между собой.

Анализируя вручную, было принято решение посмотреть на связку между `persons` и `organisational-units`.

### Организации

#### Подготовка данных

Начнем работать с ними, т.к. у организации меньше полей, с которыми надо разобраться.

Согласно [документации Pure](https://helpcenter.pure.elsevier.com/organisational-unit):

> Organisational units are a research institution’s schools, faculties, institutes, departments, and so on; any type of unit that makes up an organisation.
> If these units are organised hierarchically, you can model the structure in Pure.


```python
# load items from json
organizations = json_utils.load_from_json(os.path.join(INPUT_DATA_PATH, 'organisational-units.json'))
organizations[0]
```




    {'pureId': 19926,
     'externalId': '50000001',
     'externalIdSource': 'synchronisedUnifiedOrganisation',
     'externallyManaged': True,
     'uuid': 'abf8fae5-478f-4b63-8a8c-944750655c44',
     'period': {'startDate': '1900-01-01T12:00:00.000+02:30'},
     'info': {'createdBy': 'sync_user',
      'createdDate': '2017-05-11T15:49:21.344+0300',
      'modifiedBy': 'sync_user',
      'modifiedDate': '2025-03-01T11:28:34.778+0300',
      'portalUrl': 'https://pureportal.spbu.ru/en/organisations/federal-state-budgetary-educational-institution-of-higher-educationsaint-petersburg-state-university(abf8fae5-478f-4b63-8a8c-944750655c44).html',
      'prettyURLIdentifiers': ['федеральное-государственное-бюджетное-образовательное-учреждение-',
       'federal-state-budgetary-educational-institution-of-higher-educati']},
     'name': {'formatted': False,
      'text': [{'locale': 'en_US',
        'value': 'Federal State Budgetary Educational Institution of Higher Education"Saint Petersburg State University"'},
       {'locale': 'ru_RU',
        'value': 'Федеральное государственное бюджетное образовательное учреждение высшего образования "Санкт-Петербургский государственный университет"'}]},
     'type': {'pureId': 17276,
      'uri': '/dk/atira/pure/organisation/organisationtypes/organisation/level_0',
      'term': {'formatted': False,
       'text': [{'locale': 'en_US', 'value': 'Level 0'},
        {'locale': 'ru_RU', 'value': 'Уровень организации'}]}},
     'visibility': {'key': 'FREE',
      'value': {'formatted': False,
       'text': [{'locale': 'en_US', 'value': 'Public - No restriction'},
        {'locale': 'ru_RU', 'value': 'Публичная - без ограничений'}]}},
     'ids': [{'pureId': 28145406,
       'value': {'formatted': False, 'value': '60031888'},
       'type': {'pureId': 28135348,
        'uri': '/dk/atira/pure/organisation/organisationsources/scopus_affiliation_id',
        'term': {'formatted': False,
         'text': [{'locale': 'en_US', 'value': 'Scopus affiliation ID'},
          {'locale': 'ru_RU', 'value': 'ID аффилиации в Scopus'}]}}},
      {'pureId': 28145408,
       'value': {'formatted': False, 'value': '115124736'},
       'type': {'pureId': 28135348,
        'uri': '/dk/atira/pure/organisation/organisationsources/scopus_affiliation_id',
        'term': {'formatted': False,
         'text': [{'locale': 'en_US', 'value': 'Scopus affiliation ID'},
          {'locale': 'ru_RU', 'value': 'ID аффилиации в Scopus'}]}}},
      {'pureId': 35693622,
       'externalId': '108181118',
       'externalIdSource': 'Scopus',
       'value': {'formatted': False, 'value': '108181118'},
       'type': {'pureId': 28135348,
        'uri': '/dk/atira/pure/organisation/organisationsources/scopus_affiliation_id',
        'term': {'formatted': False,
         'text': [{'locale': 'en_US', 'value': 'Scopus affiliation ID'},
          {'locale': 'ru_RU', 'value': 'ID аффилиации в Scopus'}]}}}]}



Смотря на результаты `organisational-units_keys.json` и на данные в `organisational-units.json`, можно проигнорировать некоторые поля на данный момент.

Интересуют следующие поля - `uuid`, `level`, `parents`.

`uuid` - уникальный идентификатор сущности.
По всей видимости, можно вытаскивать связи между сущностями при помощи `uuid`, а не по `pureId`.

Про это написано в [документации Pure](https://helpcenter.pure.elsevier.com/understanding-dependents-in-the-api):

> - UUIDs are always present in content and serve as unique identifiers.
> - The API does not use traditional database constraints like primary and foreign keys.
> - Instead, relationships are retrieved dynamically through the DEPENDENTS endpoints, which identify content that relies on a given record.
> This helps you understand dependencies between content types and how they are connected. 
> This allows you to create logical associations.

`level`, по всей видимости, указывает на место в иерархии.

`parents`, по всей видимости, содержит `uuid` родительских отделений.


```python
def extract_organization_data(organizations: list) -> list:
    # Return a list of organizational units (a more compact one)
    # basically we reduce the amount of fields we want to explore

    result = list()

    for organization in organizations:
        organization_unit = dict()

        organization_unit['uuid'] = organization['uuid'] # unit uuid

        # organization_unit['name'] = organization['name']['text'][0]['value'] # unit name (ru locale)
        # CAUTION: works if we are sure that there will always be ru_RU locale
        organization_names = organization['name']['text']
        for name in organization_names:
            if name['locale'] == 'ru_RU':
                organization_unit['name'] = name['value']
        
        organization_unit['level'] = organization['type']['term']['text'][0]['value'] # unit level

        # if we have parents, should add them:
        if 'parents' in organization.keys():
            parents = list()
            for parent in organization['parents']:
                parents.append(parent['uuid'])
            organization_unit['parents'] = parents
        
        result.append(organization_unit)
    
    return result
```

Т.к. мы сжимаем количество данных до формата, который удобно представить в виде читаемой в Jupyter Notebook структуры, подключим `pandas` для построения датафрейма.

Будем использовать это как in-memory альтернативу для построения запросов к нашей "базе данных".


```python
# imports
import pandas as pd
```


```python
organizations_reduced = extract_organization_data(organizations)
organization_df = pd.DataFrame(organizations_reduced)
```


```python
# use to see column types and memory usage
organization_df.info(verbose=True, show_counts=True)
```

    <class 'pandas.DataFrame'>
    RangeIndex: 1000 entries, 0 to 999
    Data columns (total 4 columns):
     #   Column   Non-Null Count  Dtype 
    ---  ------   --------------  ----- 
     0   uuid     1000 non-null   str   
     1   name     1000 non-null   str   
     2   level    1000 non-null   str   
     3   parents  999 non-null    object
    dtypes: object(1), str(3)
    memory usage: 31.4+ KB



```python
# take random sample of 7 elements too see the data
organization_df.sample(7)
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>uuid</th>
      <th>name</th>
      <th>level</th>
      <th>parents</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>196</th>
      <td>0841a346-979a-400c-93ce-0124ff3ba7e8</td>
      <td>Кафедра осадочной геологии</td>
      <td>Level 2</td>
      <td>[436337a2-0866-4388-9baf-340bd3a55aae]</td>
    </tr>
    <tr>
      <th>209</th>
      <td>841bc901-edad-46b5-a95d-09dbe33332e6</td>
      <td>Кафедра геофизики</td>
      <td>Level 2</td>
      <td>[436337a2-0866-4388-9baf-340bd3a55aae]</td>
    </tr>
    <tr>
      <th>417</th>
      <td>4727c0db-5596-4e97-adb7-30e54c90a3b8</td>
      <td>Учебное управление</td>
      <td>Level 3</td>
      <td>[4891599d-ebbb-465a-a1ba-5e4cb5f1cf24]</td>
    </tr>
    <tr>
      <th>605</th>
      <td>88c60099-cd50-45ee-8f07-a0947e75008a</td>
      <td>Кафедра американских исследований</td>
      <td>Level 2</td>
      <td>[076ea2c3-3f32-418e-b15d-1e7d45cdcaf9]</td>
    </tr>
    <tr>
      <th>958</th>
      <td>8a923d6e-eebd-41b7-867d-a8aab512f359</td>
      <td>P2.2964.2017 Стоматология терапевтическая</td>
      <td>Level 3</td>
      <td>[922afd72-43e6-4c48-b450-62385d5e18c6]</td>
    </tr>
    <tr>
      <th>926</th>
      <td>73205f33-fa78-4f17-9a01-c35d15ecc32a</td>
      <td>P2.2698.2015 Неврология</td>
      <td>Level 3</td>
      <td>[a2daf17f-f2ea-4b6a-a05f-a4948c0db9f6]</td>
    </tr>
    <tr>
      <th>458</th>
      <td>bf6043ae-7ecb-4032-bfc7-1a9c056d5766</td>
      <td>Кафедра математической теории игр и статистиче...</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
  </tbody>
</table>
</div>



Посмотрим, за что отвечает `level`.

Из каждой группы `level` вытащим по 3 записи, чтобы почитать их названия.


```python
# show 3 organizational units per level
organization_df.groupby('level').head(3)
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>uuid</th>
      <th>name</th>
      <th>level</th>
      <th>parents</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>abf8fae5-478f-4b63-8a8c-944750655c44</td>
      <td>Федеральное государственное бюджетное образова...</td>
      <td>Level 0</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>1</th>
      <td>48d3663f-c069-4000-bb53-efeec4d313b2</td>
      <td>аспирантура</td>
      <td>Level 1</td>
      <td>[abf8fae5-478f-4b63-8a8c-944750655c44]</td>
    </tr>
    <tr>
      <th>2</th>
      <td>65666392-9044-41de-aebd-3f58d14f5679</td>
      <td>ординатура</td>
      <td>Level 1</td>
      <td>[abf8fae5-478f-4b63-8a8c-944750655c44]</td>
    </tr>
    <tr>
      <th>3</th>
      <td>436337a2-0866-4388-9baf-340bd3a55aae</td>
      <td>Институт наук о Земле СПбГУ</td>
      <td>Level 1</td>
      <td>[abf8fae5-478f-4b63-8a8c-944750655c44]</td>
    </tr>
    <tr>
      <th>39</th>
      <td>32fa2285-42f1-42c0-8ed1-7ef03a75fe77</td>
      <td>MK.2503 Теория, методология и история социологии</td>
      <td>Level 2</td>
      <td>[48d3663f-c069-4000-bb53-efeec4d313b2]</td>
    </tr>
    <tr>
      <th>40</th>
      <td>754dba6e-4686-46e2-baa0-adb0bba2edd1</td>
      <td>MK.2506 Экономическая теория</td>
      <td>Level 2</td>
      <td>[48d3663f-c069-4000-bb53-efeec4d313b2]</td>
    </tr>
    <tr>
      <th>41</th>
      <td>49250bba-7f2e-45b3-8f41-41f46edcd5de</td>
      <td>MK.2508 Финансы, денежное обращение и кредит</td>
      <td>Level 2</td>
      <td>[48d3663f-c069-4000-bb53-efeec4d313b2]</td>
    </tr>
    <tr>
      <th>417</th>
      <td>4727c0db-5596-4e97-adb7-30e54c90a3b8</td>
      <td>Учебное управление</td>
      <td>Level 3</td>
      <td>[4891599d-ebbb-465a-a1ba-5e4cb5f1cf24]</td>
    </tr>
    <tr>
      <th>426</th>
      <td>56fbb52a-3ddb-4469-a7ab-7db6abe717b6</td>
      <td>Управление образовательных программ</td>
      <td>Level 3</td>
      <td>[4891599d-ebbb-465a-a1ba-5e4cb5f1cf24]</td>
    </tr>
    <tr>
      <th>644</th>
      <td>b0dab385-587f-46ec-b8ae-af46f53a1b95</td>
      <td>MK.2503.2010 Теория, методология и история соц...</td>
      <td>Level 3</td>
      <td>[32fa2285-42f1-42c0-8ed1-7ef03a75fe77]</td>
    </tr>
  </tbody>
</table>
</div>



`Level 0` есть только у одной сущности из присланной выборки.
И это сам СПБГУ.

Выборочно посмотрим на каждые из `level`, которые у нас есть в выборке.


```python
filtered_by_level = organization_df[organization_df['level'] == 'Level 1']
filtered_by_level.head(10)
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>uuid</th>
      <th>name</th>
      <th>level</th>
      <th>parents</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>1</th>
      <td>48d3663f-c069-4000-bb53-efeec4d313b2</td>
      <td>аспирантура</td>
      <td>Level 1</td>
      <td>[abf8fae5-478f-4b63-8a8c-944750655c44]</td>
    </tr>
    <tr>
      <th>2</th>
      <td>65666392-9044-41de-aebd-3f58d14f5679</td>
      <td>ординатура</td>
      <td>Level 1</td>
      <td>[abf8fae5-478f-4b63-8a8c-944750655c44]</td>
    </tr>
    <tr>
      <th>3</th>
      <td>436337a2-0866-4388-9baf-340bd3a55aae</td>
      <td>Институт наук о Земле СПбГУ</td>
      <td>Level 1</td>
      <td>[abf8fae5-478f-4b63-8a8c-944750655c44]</td>
    </tr>
    <tr>
      <th>4</th>
      <td>823e3ac7-e97a-42ce-8678-59b721259afb</td>
      <td>Специализированный учебно-научный центр "Акаде...</td>
      <td>Level 1</td>
      <td>[abf8fae5-478f-4b63-8a8c-944750655c44]</td>
    </tr>
    <tr>
      <th>5</th>
      <td>d6fddcd6-444c-4113-938a-facd8c032b6e</td>
      <td>Биологический факультет</td>
      <td>Level 1</td>
      <td>[abf8fae5-478f-4b63-8a8c-944750655c44]</td>
    </tr>
    <tr>
      <th>6</th>
      <td>b239ccdd-36c9-4f7a-8c0f-63a973167aa6</td>
      <td>Восточный факультет</td>
      <td>Level 1</td>
      <td>[abf8fae5-478f-4b63-8a8c-944750655c44]</td>
    </tr>
    <tr>
      <th>7</th>
      <td>84b6b9ba-35db-44c2-8ca2-6f50edc771c3</td>
      <td>Высшая школа менеджмента</td>
      <td>Level 1</td>
      <td>[abf8fae5-478f-4b63-8a8c-944750655c44]</td>
    </tr>
    <tr>
      <th>8</th>
      <td>1249292b-434e-4ea8-9d38-879f8ae406ef</td>
      <td>Институт "Высшая школа журналистики и массовых...</td>
      <td>Level 1</td>
      <td>[abf8fae5-478f-4b63-8a8c-944750655c44]</td>
    </tr>
    <tr>
      <th>9</th>
      <td>4c45cb39-1632-49a0-b4a6-44b6d08d49da</td>
      <td>Институт химии Санкт-Петербургского государств...</td>
      <td>Level 1</td>
      <td>[abf8fae5-478f-4b63-8a8c-944750655c44]</td>
    </tr>
    <tr>
      <th>10</th>
      <td>dc1e6e64-b14c-4129-91d0-71aa5168da69</td>
      <td>Институт философии СПбГУ</td>
      <td>Level 1</td>
      <td>[abf8fae5-478f-4b63-8a8c-944750655c44]</td>
    </tr>
  </tbody>
</table>
</div>



Что можно сказать про последующие уровни?

`level 1` - факультеты и аспирантура / ординатура (почему?), их `parent` - спбгу

`level 2` - кафедры и общие названия программ (?)

`level 3` - какие-то сектора и более детализированные образовательные программы

**Скорее всего тут можно выстроить иерархию, древовидную структуру с корнем в спбгу!**

#### Выбор более узкой задачи

Поскольку у нас есть ПМ-ПУ в выгрузке, можем задаться более конкретной задачей: получить все организации, которые связаны с пм-пу в данной выборке.


```python
apmath_uuid = '0435d70c-2eef-4944-90ed-649c9118ccac'
apmath_units = organization_df[
        organization_df['parents']
        .apply(
            lambda x: isinstance(x, list) and apmath_uuid in x
        )
    ]
apmath_units
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>uuid</th>
      <th>name</th>
      <th>level</th>
      <th>parents</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>447</th>
      <td>3343d1c4-5fda-4eeb-b8b7-99b4d0486dd7</td>
      <td>Кафедра моделирования электромеханических и ко...</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
    <tr>
      <th>448</th>
      <td>11caa15b-33da-4386-a6f7-29f247d59ede</td>
      <td>Кафедра высшей математики</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
    <tr>
      <th>449</th>
      <td>f5159fdf-72d8-4c07-ac04-a2577e85535b</td>
      <td>Кафедра вычислительных методов механики деформ...</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
    <tr>
      <th>450</th>
      <td>df048f85-9f98-44d0-ab7f-8c6ca7ba6481</td>
      <td>Кафедра диагностики функциональных систем</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
    <tr>
      <th>451</th>
      <td>1a947b4c-6f8c-42ef-b3d8-9e20c3c29ed8</td>
      <td>Кафедра информационных систем</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
    <tr>
      <th>452</th>
      <td>18e307e1-04a2-46eb-a50e-9975b0c7d452</td>
      <td>Кафедра компьютерного моделирования и многопро...</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
    <tr>
      <th>453</th>
      <td>786faf0d-4b5e-41b1-aa8e-1c7da0ac1d80</td>
      <td>Кафедра компьютерных технологий и систем</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
    <tr>
      <th>454</th>
      <td>1fffa552-7fe9-4e35-96d4-12ac1cfd03a9</td>
      <td>Кафедра космических технологий и прикладной ас...</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
    <tr>
      <th>455</th>
      <td>3672f23a-61a7-4189-8869-6384cc2ee273</td>
      <td>Кафедра математической теории микропроцессорны...</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
    <tr>
      <th>456</th>
      <td>5d649981-51f1-4792-b407-cf01c50f5c8d</td>
      <td>Кафедра математической теории моделирования си...</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
    <tr>
      <th>457</th>
      <td>813a4900-f5da-4667-bead-59a224b4bcd2</td>
      <td>Кафедра математического моделирования энергети...</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
    <tr>
      <th>458</th>
      <td>bf6043ae-7ecb-4032-bfc7-1a9c056d5766</td>
      <td>Кафедра математической теории игр и статистиче...</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
    <tr>
      <th>459</th>
      <td>6d20a14d-5b1f-46bb-a9f5-d121ab6df366</td>
      <td>Кафедра математической теории экономических ре...</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
    <tr>
      <th>460</th>
      <td>4924bfe6-518d-45f4-898a-5e95f90ee518</td>
      <td>Кафедра механики управляемого движения</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
    <tr>
      <th>461</th>
      <td>d9ad6da8-cb58-40f4-a062-81695011b49d</td>
      <td>Кафедра моделирования социально-экономических ...</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
    <tr>
      <th>462</th>
      <td>652ed6df-9d33-409c-add5-1406d63ef348</td>
      <td>Кафедра моделирования экономических систем</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
    <tr>
      <th>463</th>
      <td>f9a1a426-d4fd-46f2-aef6-74cadd686665</td>
      <td>Кафедра теории систем управления электрофизиче...</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
    <tr>
      <th>464</th>
      <td>489d6770-fff8-41b1-be91-34f1002e9c22</td>
      <td>Кафедра теории управления</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
    <tr>
      <th>465</th>
      <td>5c4f14e3-7d56-4253-8a18-a0b82d10e363</td>
      <td>Кафедра технологии программирования</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
    <tr>
      <th>466</th>
      <td>00605c7b-5200-48e9-83e4-b40461c1fdfa</td>
      <td>Кафедра управления медико-биологическими систе...</td>
      <td>Level 2</td>
      <td>[0435d70c-2eef-4944-90ed-649c9118ccac]</td>
    </tr>
  </tbody>
</table>
</div>




```python
# save apmath units uuids to use them with persons
apmath_units_uuid = apmath_units['uuid']
apmath_units_uuid_list = apmath_units_uuid.tolist()
```

### Люди

#### Подготовка данных

Согласно [документации Pure](https://helpcenter.pure.elsevier.com/take-advantage-of-the-person-profile):

> Contains a researcher's name, name variants, titles, IDs, links and more.


```python
# load items from json
persons = json_utils.load_from_json(os.path.join(INPUT_DATA_PATH, 'persons.json'))
persons[0]
```




    {'pureId': 143835,
     'externalId': '50063896',
     'externalIdSource': 'synchronisedUnifiedPerson',
     'uuid': '2b5c936a-4af4-44f9-9cc3-4e47a2cf4ba2',
     'name': {'firstName': 'Евгений Александрович', 'lastName': 'Поляков'},
     'orcid': '0000-0001-9850-5370',
     'fte': 0.0,
     'isExpert': False,
     'info': {'createdBy': 'sync_user',
      'createdDate': '2017-05-11T19:40:46.645+0300',
      'modifiedBy': 'root',
      'modifiedDate': '2018-06-09T04:50:41.314+0300',
      'portalUrl': 'https://pureportal.spbu.ru/en/persons/--(2b5c936a-4af4-44f9-9cc3-4e47a2cf4ba2).html',
      'prettyURLIdentifiers': ['евгений-александрович-поляков']},
     'visibility': {'key': 'BACKEND',
      'value': {'formatted': False,
       'text': [{'locale': 'en_US', 'value': 'Backend - Restricted to Pure users'},
        {'locale': 'ru_RU',
         'value': 'Сервер - доступно только пользователям Pure'}]}},
     'nameVariants': [{'pureId': 11328091,
       'externalId': '50063896',
       'externalIdSource': 'synchronisedUnifiedPerson',
       'name': {'firstName': 'Evgenii', 'lastName': 'Poliakov'},
       'type': {'pureId': 16224,
        'uri': '/dk/atira/pure/person/names/translated',
        'term': {'formatted': False,
         'text': [{'locale': 'en_US', 'value': 'Transcribed name'},
          {'locale': 'ru_RU', 'value': 'переведённое имя'}]}}}],
     'ids': [{'pureId': 9521366,
       'externalId': '5006389603',
       'externalIdSource': 'synchronisedUnifiedPerson',
       'value': {'formatted': False, 'value': 'M-9021-2013'},
       'type': {'pureId': 16252,
        'uri': '/dk/atira/pure/person/personsources/researcher',
        'term': {'formatted': False,
         'text': [{'locale': 'en_US', 'value': 'Researcher ID'},
          {'locale': 'ru_RU',
           'value': 'авторский идентификатор Web of Science'}]}}},
      {'pureId': 28171907,
       'externalId': '36673543300',
       'externalIdSource': 'Scopus',
       'value': {'formatted': False, 'value': '36673543300'},
       'type': {'pureId': 6536,
        'uri': '/dk/atira/pure/person/personsources/scopusauthor',
        'term': {'formatted': False,
         'text': [{'locale': 'en_US', 'value': 'Scopus Author ID'},
          {'locale': 'ru_RU', 'value': 'ID автора в Scopus'}]}}}],
     'staffOrganisationAssociations': [{'pureId': 143840,
       'externalId': '107879',
       'externalIdSource': 'synchronisedUnifiedPerson',
       'person': {'uuid': '2b5c936a-4af4-44f9-9cc3-4e47a2cf4ba2',
        'link': {'ref': 'content',
         'href': 'http://localhost:8080/ws/api/522/persons/2b5c936a-4af4-44f9-9cc3-4e47a2cf4ba2'},
        'externalId': '50063896',
        'externalIdSource': 'synchronisedUnifiedPerson',
        'name': {'formatted': False,
         'text': [{'value': 'Евгений Александрович Поляков'}]}},
       'affiliationId': '107879',
       'period': {'startDate': '2017-03-15T12:00:00.000+03:00',
        'endDate': '2017-12-28T12:00:00.000+03:00'},
       'isPrimaryAssociation': False,
       'fte': 0.0,
       'employmentType': {'pureId': 16544,
        'uri': '/dk/atira/pure/person/employmenttypes/researchsupport',
        'term': {'formatted': False,
         'text': [{'locale': 'en_US', 'value': 'Research Support'},
          {'locale': 'ru_RU', 'value': 'научно-технический персонал'}]}},
       'organisationalUnit': {'uuid': '3c70bc8d-1758-41dd-b716-5c21d94bd23f',
        'link': {'ref': 'content',
         'href': 'http://localhost:8080/ws/api/522/organisational-units/3c70bc8d-1758-41dd-b716-5c21d94bd23f'},
        'externalId': '50116349',
        'externalIdSource': 'synchronisedUnifiedOrganisation',
        'externallyManaged': True,
        'name': {'formatted': False,
         'text': [{'locale': 'en_US',
           'value': 'Department of Molecular Biophysics and Polymer Physics'},
          {'locale': 'ru_RU',
           'value': 'Кафедра молекулярной биофизики и физики полимеров'}]},
        'type': {'pureId': 17281,
         'uri': '/dk/atira/pure/organisation/organisationtypes/organisation/level_2',
         'term': {'formatted': False,
          'text': [{'locale': 'en_US', 'value': 'Level 2'},
           {'locale': 'ru_RU', 'value': '2 уровень'}]}}},
       'staffType': {'pureId': 6614,
        'uri': '/dk/atira/pure/person/personstafftype/nonacademic',
        'term': {'formatted': False,
         'text': [{'locale': 'en_US', 'value': 'Non-academic'},
          {'locale': 'ru_RU', 'value': 'Не научные'}]}},
       'jobTitle': {'pureId': 16380,
        'uri': '/dk/atira/pure/person/jobtitles/50000843',
        'term': {'formatted': False,
         'text': [{'locale': 'en_US', 'value': 'Research Engineer'},
          {'locale': 'ru_RU', 'value': 'инженер-исследователь'}]}}}]}



Согласно документации Pure, имя человека можно выделить из объекта `name`.

Посмотрим на структуру объекта для первого человека из выборки


```python
# take name
persons[0]['name']
```




    {'firstName': 'Евгений Александрович', 'lastName': 'Поляков'}



Хотелось бы узнать, как связаны между собой человек и организация.

Видимо, есть 2 основных типа организаций, к которым может принадлежать человек - `staffOrganisationAssociations` и `studentOrganisationAssociations`.
Предположительно, первый атрибут обозначает принадлежность человека к организации как сотрудника.

Это подтверждается [спецификацией Pure](https://api.elsevierpure.com/ws/api/api-docs/index.html?url=/ws/api/openapi.yaml#/person/person_get):

> Organizations that the person is associated with as 'Staff'

Исходя из результатов в `persons_keys.json`, таких организаций у одного пользователя может быть несколько.
Посмотрим, как это можно вызвать из кода:


```python
# can take uuid of organisation
persons[0]['staffOrganisationAssociations'][0]['organisationalUnit']
```




    {'uuid': '3c70bc8d-1758-41dd-b716-5c21d94bd23f',
     'link': {'ref': 'content',
      'href': 'http://localhost:8080/ws/api/522/organisational-units/3c70bc8d-1758-41dd-b716-5c21d94bd23f'},
     'externalId': '50116349',
     'externalIdSource': 'synchronisedUnifiedOrganisation',
     'externallyManaged': True,
     'name': {'formatted': False,
      'text': [{'locale': 'en_US',
        'value': 'Department of Molecular Biophysics and Polymer Physics'},
       {'locale': 'ru_RU',
        'value': 'Кафедра молекулярной биофизики и физики полимеров'}]},
     'type': {'pureId': 17281,
      'uri': '/dk/atira/pure/organisation/organisationtypes/organisation/level_2',
      'term': {'formatted': False,
       'text': [{'locale': 'en_US', 'value': 'Level 2'},
        {'locale': 'ru_RU', 'value': '2 уровень'}]}}}



Получается, `person` содержит в себе довольно подробную информацию об организации, а не только ее `uuid`.

Опять же, все поля сейчас просматривать не имеет смысла.
Ограничимся `uuid`, `name` и `uuid` организаций, с которыми связан пользователь.


```python
def extract_person_data(persons: list) -> list:
    # i want to take person uuid, name, organizational unit
    result = list()

    for person in persons:
        person_unit = dict()

        person_unit['uuid'] = person['uuid'] # unit uuid
        person_unit['name'] = f"{person['name']['lastName']} {person['name']['firstName']}"
        
        person_organizations = person['staffOrganisationAssociations']
        organization_uuids = list()
        organization_jobs = list()

        for organization in person_organizations:
            organization_uuids.append(organization['organisationalUnit']['uuid'])

            # CAUTION: doesn't work since jobTitle is not a required field
            # job_title_names = organization['jobTitle']['term']['text']
            # print(job_title_names)
            # for job in job_title_names:
            #     if job['locale'] == 'ru_RU':
            #         organization_jobs.append(job['value'])

        person_unit['organizations'] = organization_uuids
        result.append(person_unit)
    
    return result
```

Сформируем pandas dataframe для дальнейшей работы


```python
persons_reduced = extract_person_data(persons)
person_df = pd.DataFrame(persons_reduced)
```


```python
# get random sample of persons
person_df.sample(7)
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>uuid</th>
      <th>name</th>
      <th>organizations</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>16</th>
      <td>e92c6ee3-5065-4fd9-9092-ee88c797d5b6</td>
      <td>Мишенев Сергей Викторович</td>
      <td>[92c68aa8-3698-44da-a21e-12641e088085, 92c68aa...</td>
    </tr>
    <tr>
      <th>769</th>
      <td>ff329f84-dd91-40a9-b7f1-d057dce04424</td>
      <td>Потапчук Светлана Александровна</td>
      <td>[5dbfbf1e-b259-46bf-8881-005d97ddeb47, 5dbfbf1...</td>
    </tr>
    <tr>
      <th>67</th>
      <td>31ea911e-fd9d-426f-9949-6c2b15610ef9</td>
      <td>Бобков Андрей Анатольевич</td>
      <td>[0a36a32b-6ab7-42e8-bb2a-61979d1d95d5]</td>
    </tr>
    <tr>
      <th>59</th>
      <td>ec49c69f-0138-4f9a-bd77-2271abe29933</td>
      <td>Кучеров Дмитрий Геннадьевич</td>
      <td>[92e8d89f-8cf5-4627-8a17-fc74aa8f10e3]</td>
    </tr>
    <tr>
      <th>218</th>
      <td>f07b5902-7b18-4c17-8d22-c1b941e15957</td>
      <td>Кузьменко Александр Валентинович</td>
      <td>[aed53f98-ba8d-4a19-b12c-447f51180d05, aed53f9...</td>
    </tr>
    <tr>
      <th>46</th>
      <td>23240dfc-72e8-4830-9684-7f5f40cafb6c</td>
      <td>Яковлев Игорь Петрович</td>
      <td>[165829bb-1450-449e-9f4f-b0905ff440b3]</td>
    </tr>
    <tr>
      <th>527</th>
      <td>7c172cf4-6b2f-483a-b121-2f5a9bc41858</td>
      <td>Чичайкин Валерий Алексеевич</td>
      <td>[020e835c-b2ba-455c-aa07-9152baf09c57]</td>
    </tr>
  </tbody>
</table>
</div>



#### Выбор более узкой задачи

Ранее мы уже нашли `uuid`s, которые относятся к подразделениям пм-пу.
Теперь посмотрим, есть ли в нашей выборке сотрудники из этих подразделений.


```python
apmath_persons = person_df[
        person_df['organizations']
        .apply(
            lambda x: isinstance(x, list) and any(uuid in x for uuid in apmath_units_uuid_list)
        )
    ]
apmath_persons
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>uuid</th>
      <th>name</th>
      <th>organizations</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>159</th>
      <td>b11c249c-18ee-4494-a897-3966da97064d</td>
      <td>Балыкина Юлия Ефимовна</td>
      <td>[813a4900-f5da-4667-bead-59a224b4bcd2, 813a490...</td>
    </tr>
    <tr>
      <th>163</th>
      <td>fa04ec63-d948-435a-aaff-fbc46255ec84</td>
      <td>Александрова Ирина Васильевна</td>
      <td>[489d6770-fff8-41b1-be91-34f1002e9c22, 489d677...</td>
    </tr>
    <tr>
      <th>204</th>
      <td>699e6dfa-251b-44f9-8599-8c99ff069e52</td>
      <td>Смирнов Николай Васильевич</td>
      <td>[652ed6df-9d33-409c-add5-1406d63ef348, 652ed6d...</td>
    </tr>
    <tr>
      <th>205</th>
      <td>1a34decc-5009-4cdb-a37f-f59eadc44494</td>
      <td>Кузютин Денис Вячеславович</td>
      <td>[bf6043ae-7ecb-4032-bfc7-1a9c056d5766, bf6043a...</td>
    </tr>
    <tr>
      <th>223</th>
      <td>250c452b-d714-44d5-bccb-c44e077aac77</td>
      <td>Парфенов Андрей Павлович</td>
      <td>[df048f85-9f98-44d0-ab7f-8c6ca7ba6481, df048f8...</td>
    </tr>
    <tr>
      <th>243</th>
      <td>b4146396-6229-4b37-92f3-433b8485e875</td>
      <td>Никитин Александр Владимирович</td>
      <td>[3672f23a-61a7-4189-8869-6384cc2ee273]</td>
    </tr>
    <tr>
      <th>255</th>
      <td>a63ef843-db4e-4738-a720-07fc04e27875</td>
      <td>Чашников Михаил Викторович</td>
      <td>[489d6770-fff8-41b1-be91-34f1002e9c22, 489d677...</td>
    </tr>
    <tr>
      <th>353</th>
      <td>2f974cbd-2f8d-4b16-b690-277feb6a2f52</td>
      <td>Зенкевич Николай Анатольевич</td>
      <td>[d97a9c77-1d9c-44c8-85c7-ad928ff3182c, d97a9c7...</td>
    </tr>
    <tr>
      <th>385</th>
      <td>14bbd794-9b4a-46cc-8820-529398a81c83</td>
      <td>Курбатова Галина Ибрагимовна</td>
      <td>[3343d1c4-5fda-4eeb-b8b7-99b4d0486dd7, 3343d1c...</td>
    </tr>
    <tr>
      <th>403</th>
      <td>bdf2ff2d-f1fc-435f-ad99-70707041cf7a</td>
      <td>Зубов Афанасий Владимирович</td>
      <td>[3672f23a-61a7-4189-8869-6384cc2ee273]</td>
    </tr>
    <tr>
      <th>450</th>
      <td>3f691d8a-bed9-42a4-91e8-05b7f3b02228</td>
      <td>Олемской Игорь Владимирович</td>
      <td>[1a947b4c-6f8c-42ef-b3d8-9e20c3c29ed8, 1a947b4...</td>
    </tr>
    <tr>
      <th>451</th>
      <td>c1c65cb9-e4b5-479e-a0b3-3fcf951d81ca</td>
      <td>Смирнова Мария Александровна</td>
      <td>[786faf0d-4b5e-41b1-aa8e-1c7da0ac1d80, 786faf0...</td>
    </tr>
    <tr>
      <th>471</th>
      <td>11751111-a0c9-4bf4-b0f4-6905f50a7594</td>
      <td>Макаров Авинир Геннадьевич</td>
      <td>[f9a1a426-d4fd-46f2-aef6-74cadd686665]</td>
    </tr>
    <tr>
      <th>494</th>
      <td>6ddffafa-f0a2-477e-9972-a91ed91aae1f</td>
      <td>Малинин Константин Александрович</td>
      <td>[5c4f14e3-7d56-4253-8a18-a0b82d10e363]</td>
    </tr>
    <tr>
      <th>534</th>
      <td>5d46c6b2-104c-485a-81cd-5ef2967f253c</td>
      <td>Соловьев Павел Алексеевич</td>
      <td>[5c4f14e3-7d56-4253-8a18-a0b82d10e363]</td>
    </tr>
    <tr>
      <th>537</th>
      <td>6a971fe7-b986-400d-b0b0-681a3b1fec36</td>
      <td>Волкова Марина Владимировна</td>
      <td>[6d20a14d-5b1f-46bb-a9f5-d121ab6df366]</td>
    </tr>
    <tr>
      <th>563</th>
      <td>91c67561-9259-4402-911a-221ee11edd55</td>
      <td>Минеев Анатолий Борисович</td>
      <td>[f9a1a426-d4fd-46f2-aef6-74cadd686665, f9a1a42...</td>
    </tr>
    <tr>
      <th>572</th>
      <td>d0cb4a4d-2b38-436f-929d-7712f34ec844</td>
      <td>Мельник Анна Владимировна</td>
      <td>[f5159fdf-72d8-4c07-ac04-a2577e85535b]</td>
    </tr>
    <tr>
      <th>601</th>
      <td>f336fdf4-10ff-4ed8-8fa6-4abe90639045</td>
      <td>Моисеев Игорь Анатольевич</td>
      <td>[786faf0d-4b5e-41b1-aa8e-1c7da0ac1d80]</td>
    </tr>
    <tr>
      <th>606</th>
      <td>8d864980-9363-44ab-8a28-82d5a5f1cc1f</td>
      <td>Должиков Владимир Васильевич</td>
      <td>[5c4f14e3-7d56-4253-8a18-a0b82d10e363]</td>
    </tr>
    <tr>
      <th>811</th>
      <td>9fbeedef-87c7-4b4d-827c-4f7f2878c6d0</td>
      <td>Гурьянов Анатолий Евсеевич</td>
      <td>[11caa15b-33da-4386-a6f7-29f247d59ede]</td>
    </tr>
    <tr>
      <th>813</th>
      <td>f87315df-f7dc-4189-a870-90333557e254</td>
      <td>Новожилова Лидия Михайловна</td>
      <td>[d9ad6da8-cb58-40f4-a062-81695011b49d, d9ad6da...</td>
    </tr>
    <tr>
      <th>937</th>
      <td>d693d4f1-e043-43c4-8e12-73e26a76fe07</td>
      <td>Виноградова Екатерина Михайловна</td>
      <td>[3343d1c4-5fda-4eeb-b8b7-99b4d0486dd7, 3343d1c...</td>
    </tr>
    <tr>
      <th>990</th>
      <td>0ecdff85-a0d0-4861-9a82-c6931ba5541d</td>
      <td>Коровкин Максим Васильевич</td>
      <td>[786faf0d-4b5e-41b1-aa8e-1c7da0ac1d80, 786faf0...</td>
    </tr>
  </tbody>
</table>
</div>



## Выводы

### Ценность текущих результатов

Как видно, на полученной выборке можно получать агрегированные данные.

Структура сущностей получается довольно громоздкой, потому что при наличии связей с другими сущностями включается не только связка в виде `uuid`, но и более подробная информация, которая затрудняет быстрый разбор и интерпретацию атрибутов, особенно при отсутствии документации.

В спецификации, представленной в вики репозитория, отсутствует описание ответов с сервера, поэтому изначально пришлось выстраивать предположения о том, что значит тот или иной атрибут, исходя из информации на Pure Helpdesk.

Лишь в конце исследования удалось найти общую спецификацию к Pure, которая довольно подробно описывает ответы в Pure API - [ссылка](https://api.elsevierpure.com/ws/api/api-docs/index.html?url=/ws/api/openapi.yaml).

**Поскольку это общая документация к версии API, которая выше версии в вики (5.22 vs 5.35), то к ней надо относиться с настороженностью.**
**Однако, это может сильно помочь для дальнейшего понимания.**

Из-за отсутствия спецификации на конкретную имплементацию сервиса, неясно, какие атрибуты будут присутствовать всегда (т.е. они `required`), а какие - нет (`optional`).
По этой причине не удалось вытащить должность сотрудника для подразделения - у кого-то такая информация есть, а у кого-то ее нет!

### Проблема ручного парсинга

Ручной парсинг json'ов - неприятное занятие.
Если хочется и дальше получать ответы с сервера, то нужно точно определить, какие поля нам нужно оставлять, а от каких отказываться.

Исходя из этого понимания, можно будет использовать методы, предоставляемые различными библиотеками.
Возможно, это позволит создать более fault tolerant решение.

### Что делать дальше?

Пока ручное построение запросов в pandas работает, оно не очень удобно для дальнейшей работы - держать несколько pandas dataframes одновременно в ram может быть проблематичным.
Возможно, стоит перейти к связке "бд + сервис запроса"

В целом, реляционная бд может подойти, но требуется понять, как организовать схему БД для укладывания существующих сущностей.
Исходя из увиденнного, один человек может принадлежать нескольким организационным подразделениям.
А организационные подразделения выстраивают иерархию.

Надо более подробно изучить ВСЕ сущности и понять связи между ними (напр. найти или сформировать ERM-диаграмму), определить, от каких атрибутов можно отказаться.

Наверное, это позволить сделать сущности более плоскими и удобными для укладки в БД и дальнейшего исследования данных.

## Источники для дальнейшего изучения

### Интернет-ресурсы

Список ресурсов, которые можно использовать для дальнейшей работы:

- [Pure Help Center: Documentation](https://helpcenter.pure.elsevier.com/en_US/documentation)
- [Pure API User Guide](https://helpcenter.pure.elsevier.com/pure-api-home)
- [Understanding Dependents in the Pure API](https://helpcenter.pure.elsevier.com/understanding-dependents-in-the-api)
- [Differences Between UUID and Pure ID](https://helpcenter.pure.elsevier.com/difference-between-uuid-and-pure-id)
- [Swagger: Pure API Specification](https://api.elsevierpure.com/ws/api/api-docs/index.html?url=/ws/api/openapi.yaml)
- [Overview of Content Types](https://helpcenter.pure.elsevier.com/overview-of-content-types)
- [Organisational Unit](https://helpcenter.pure.elsevier.com/organisational-unit)

### Литература и общение с AI по теме задачи

#### Pure от Elseveir - это CRIS / RIMS

Некоторые заметки по тому, что такое Pure в принципе.
Это будет полезно для поиска статей, посвященных таким системам.

Согласно [Википедии](https://en.wikipedia.org/wiki/Current_research_information_system):

> CRIS — это база данных или иная информационная система для хранения, управления и обмена контекстными метаданными об исследовательской деятельности, финансируемой исследовательским фондом или проводимой в организации, выполняющей исследования (или их объединении).

CRIS — это синоним RIMS (Research Information Management System, Система управления исследовательской информацией).
Pure — одна из таких систем.

### BI для RIMS

Википедия также дает краткую информацию о стороне Business Intelligence для RIMS:

> Благодаря комплексной агрегации контекстной исследовательской информации CRIS являются очень подходящими инструментами для извлечения показателей бизнес-аналитики для принятия решений в учреждениях и за их пределами.

Таким образом, мы можем попытаться найти статьи о принятии решений с использованием RIMS/CRIS.
Кроме того, я полагаю, что [SciVal](https://www.scival.com/landing) от Elsevier существует именно для этой цели.

Нашла немного литературы по этой теме:

- Статья Никифоровой с элементами предиктивного анализа (машинное обучение и статистика)
- Нашла обзорный PDF по Scival; предлагает несколько use cases для применения метрик

SciVal похож на то, что хотелось бы получить на выходе.
Вот что Gemini говорит о Scival:

> SciVal — это веб-аналитическое решение от Elsevier, использующее данные Scopus для визуализации, анализа и бенчмаркинга исследовательской эффективности более 20 000 учреждений, 10 000+ исследовательских тем и связанных с ними исследователей из более чем 230 стран.
>
> Оно обеспечивает стратегическое принятие решений, выявление партнеров и отслеживание тенденций, например, в области ЦУР (SDGs) и научных направлениях.
>
> Ключевые особенности и возможности:
>
> - **Бенчмаркинг (Сравнительный анализ):** Сравнивайте исследовательскую эффективность (публикационная активность, цитируемость, влияние) учреждений, команд или отдельных лиц с конкурентами, используя такие показатели, как FWCI (Field-Weighted Citation Impact — взвешенный по области науки показатель цитирования).
> - **Сотрудничество:** Определяйте существующих или потенциальных партнеров путем анализа сетей соавторства и поиска ведущих экспертов в конкретных областях.
> - **Анализ трендов:** Изучайте исследовательские тренды, тематические кластеры и актуальные темы для выявления новых областей исследований.
> - **Отчетность:** Создавайте настраиваемые отчеты для демонстрации научного влияния (research impact) в целях получения финансирования, найма сотрудников или участия в рейтингах.
> - **Источники данных:** Использует данные Scopus, охватывающие период с 1996 года по настоящее время и включающие более 80 миллионов записей от 7000+ издателей.

Итак... еще одна тема для ресерча: что такое бенчмаркинг и какие метрики существуют в области CRIS и академической среды.
