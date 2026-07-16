# Исследование вложенных полей research-outputs.json

## Исходный файл

`C:\Users\Janna\Projects\Pure-ETL\Data\research-outputs.json`

## Общая информация

- Количество публикаций: **1000**
- Исследуемых полей: **10**

## Заполненность ключевых полей

| Поле | Присутствует | Непустых значений | Null | Пустых | Типы |
|---|---:|---:|---:|---:|---|
| `title` | 1000 (100.00%) | 1000 (100.00%) | 0 | 0 | object: 1000 |
| `abstract` | 215 (21.50%) | 215 (21.50%) | 0 | 0 | object: 215 |
| `publicationStatuses` | 1000 (100.00%) | 1000 (100.00%) | 0 | 0 | array: 1000 |
| `personAssociations` | 1000 (100.00%) | 1000 (100.00%) | 0 | 0 | array: 1000 |
| `keywordGroups` | 991 (99.10%) | 991 (99.10%) | 0 | 0 | array: 991 |
| `managingOrganisationalUnit` | 1000 (100.00%) | 1000 (100.00%) | 0 | 0 | object: 1000 |
| `organisationalUnits` | 709 (70.90%) | 709 (70.90%) | 0 | 0 | array: 709 |
| `type` | 1000 (100.00%) | 1000 (100.00%) | 0 | 0 | object: 1000 |
| `category` | 1000 (100.00%) | 1000 (100.00%) | 0 | 0 | object: 1000 |
| `language` | 1000 (100.00%) | 1000 (100.00%) | 0 | 0 | object: 1000 |

## Поле `title`

### Первый непустой пример

```json
{
  "formatted": true,
  "value": "Новая форма приграничного сотрудничества"
}
```

### Обнаруженные вложенные пути

| JSON-путь | Публикаций с путём | Типы значений | Пример |
|---|---:|---|---|
| `title` | 1000 (100.00%) | object: 1000 | object keys: formatted, value |
| `title.formatted` | 1000 (100.00%) | boolean: 1000 | True |
| `title.value` | 1000 (100.00%) | string: 1000 | Новая форма приграничного сотрудничества |

## Поле `abstract`

### Первый непустой пример

```json
{
  "formatted": true,
  "text": [
    {
      "locale": "ru_RU",
      "value": "Рецензия на книгу Ж.Т.Тощенко \"Теократия: фантом или реальность?\""
    }
  ]
}
```

### Обнаруженные вложенные пути

| JSON-путь | Публикаций с путём | Типы значений | Пример |
|---|---:|---|---|
| `abstract` | 215 (21.50%) | object: 215 | object keys: formatted, text |
| `abstract.formatted` | 215 (21.50%) | boolean: 215 | True |
| `abstract.text` | 215 (21.50%) | array: 215 | array with 1 item(s) |
| `abstract.text[]` | 215 (21.50%) | object: 218 | object keys: locale, value |
| `abstract.text[].locale` | 215 (21.50%) | string: 218 | ru_RU |
| `abstract.text[].value` | 215 (21.50%) | string: 218 | Рецензия на книгу Ж.Т.Тощенко "Теократия: фантом или реальность?" |

## Поле `publicationStatuses`

### Размер массивов

- Минимум элементов: **1**
- Среднее количество элементов: **1.00**
- Максимум элементов: **2**

### Первый непустой пример

```json
[
  {
    "pureId": 3732230,
    "externalId": "177302",
    "externalIdSource": "researchoutputwizard",
    "current": true,
    "publicationDate": {
      "year": 2012
    },
    "publicationStatus": {
      "pureId": 957,
      "uri": "/dk/atira/pure/researchoutput/status/published",
      "term": {
        "formatted": false,
        "text": [
          {
            "locale": "en_US",
            "value": "Published"
          },
          {
            "locale": "ru_RU",
            "value": "Опубликовано"
          }
        ]
      }
    }
  }
]
```

### Обнаруженные вложенные пути

| JSON-путь | Публикаций с путём | Типы значений | Пример |
|---|---:|---|---|
| `publicationStatuses` | 1000 (100.00%) | array: 1000 | array with 1 item(s) |
| `publicationStatuses[]` | 1000 (100.00%) | object: 1002 | object keys: pureId, externalId, externalIdSource, current, publicationDate, publicationStatus |
| `publicationStatuses[].current` | 1000 (100.00%) | boolean: 1002 | True |
| `publicationStatuses[].externalId` | 1000 (100.00%) | string: 1002 | 177302 |
| `publicationStatuses[].externalIdSource` | 1000 (100.00%) | string: 1002 | researchoutputwizard |
| `publicationStatuses[].publicationDate` | 1000 (100.00%) | object: 1002 | object keys: year |
| `publicationStatuses[].publicationDate.year` | 1000 (100.00%) | integer: 1002 | 2012 |
| `publicationStatuses[].publicationStatus` | 1000 (100.00%) | object: 1002 | object keys: pureId, uri, term |
| `publicationStatuses[].publicationStatus.pureId` | 1000 (100.00%) | integer: 1002 | 957 |
| `publicationStatuses[].publicationStatus.term` | 1000 (100.00%) | object: 1002 | object keys: formatted, text |
| `publicationStatuses[].publicationStatus.term.formatted` | 1000 (100.00%) | boolean: 1002 | False |
| `publicationStatuses[].publicationStatus.term.text` | 1000 (100.00%) | array: 1002 | array with 2 item(s) |
| `publicationStatuses[].publicationStatus.term.text[]` | 1000 (100.00%) | object: 2004 | object keys: locale, value |
| `publicationStatuses[].publicationStatus.term.text[].locale` | 1000 (100.00%) | string: 2004 | en_US |
| `publicationStatuses[].publicationStatus.term.text[].value` | 1000 (100.00%) | string: 2004 | Published |
| `publicationStatuses[].publicationStatus.uri` | 1000 (100.00%) | string: 1002 | /dk/atira/pure/researchoutput/status/published |
| `publicationStatuses[].pureId` | 1000 (100.00%) | integer: 1002 | 3732230 |
| `publicationStatuses[].publicationDate.month` | 19 (1.90%) | integer: 19 | 3 |
| `publicationStatuses[].publicationDate.day` | 8 (0.80%) | integer: 8 | 22 |

## Поле `personAssociations`

### Размер массивов

- Минимум элементов: **1**
- Среднее количество элементов: **2.34**
- Максимум элементов: **97**

### Первый непустой пример

```json
[
  {
    "pureId": 3732233,
    "person": {
      "uuid": "c9be961a-6b7e-4381-bdd2-efb2e7cf4864",
      "link": {
        "ref": "content",
        "href": "http://localhost:8080/ws/api/522/persons/c9be961a-6b7e-4381-bdd2-efb2e7cf4864"
      },
      "externalId": "50017086",
      "externalIdSource": "synchronisedUnifiedPerson",
      "externallyManaged": true,
      "name": {
        "formatted": false,
        "text": [
          {
            "value": "Александр Иванович Кубышкин"
          }
        ]
      }
    },
    "name": {
      "firstName": "А.И.",
      "lastName": "Кубышкин"
    },
    "personRole": {
      "pureId": 16882,
      "uri": "/dk/atira/pure/researchoutput/roles/contributiontojournal/author",
      "term": {
        "formatted": false,
        "text": [
          {
            "locale": "en_US",
            "value": "Author"
          },
          {
            "locale": "ru_RU",
            "value": "автор"
          }
        ]
      }
    },
    "organisationalUnits": [
      {
        "uuid": "1e4b7829-b1ed-40be-b417-303f648cf826",
        "link": {
          "ref": "content",
          "href": "http://localhost:8080/ws/api/522/organisational-units/1e4b7829-b1ed-40be-b417-303f648cf826"
        },
        "externalId": "50069336",
        "externalIdSource": "synchronisedUnifiedOrganisation",
        "externallyManaged": true,
        "name": {
          "formatted": false,
          "text": [
            {
              "locale": "en_US",
              "value": "Department of Theory and Methodology for Teaching Arts andHumanities"
            },
            {
              "locale": "ru_RU",
              "value": "Кафедра теории и методики преподавания искусств и гуманитарных наук"
            }
          ]
        },
        "type": {
          "pureId": 17281,
          "uri": "/dk/atira/pure/organisation/organisationtypes/organisation/level_2",
          "term": {
            "formatted": false,
            "text": [
              {
                "locale": "en_US",
                "value": "Level 2"
              },
              {
                "locale": "ru_RU",
                "value": "2 уровень"
              }
            ]
          }
        }
      }
    ]
  }
]
```

### Обнаруженные вложенные пути

| JSON-путь | Публикаций с путём | Типы значений | Пример |
|---|---:|---|---|
| `personAssociations` | 1000 (100.00%) | array: 1000 | array with 1 item(s) |
| `personAssociations[]` | 1000 (100.00%) | object: 2338 | object keys: pureId, person, name, personRole, organisationalUnits |
| `personAssociations[].name` | 1000 (100.00%) | object: 2338 | object keys: firstName, lastName |
| `personAssociations[].name.firstName` | 1000 (100.00%) | string: 2338 | А.И. |
| `personAssociations[].name.lastName` | 1000 (100.00%) | string: 2338 | Кубышкин |
| `personAssociations[].person` | 1000 (100.00%) | object: 1420 | object keys: uuid, link, externalId, externalIdSource, externallyManaged, name |
| `personAssociations[].person.externalId` | 1000 (100.00%) | string: 1420 | 50017086 |
| `personAssociations[].person.externalIdSource` | 1000 (100.00%) | string: 1420 | synchronisedUnifiedPerson |
| `personAssociations[].person.link` | 1000 (100.00%) | object: 1420 | object keys: ref, href |
| `personAssociations[].person.link.href` | 1000 (100.00%) | string: 1420 | http://localhost:8080/ws/api/522/persons/c9be961a-6b7e-4381-bdd2-efb2e7cf4864 |
| `personAssociations[].person.link.ref` | 1000 (100.00%) | string: 1420 | content |
| `personAssociations[].person.name` | 1000 (100.00%) | object: 1420 | object keys: formatted, text |
| `personAssociations[].person.name.formatted` | 1000 (100.00%) | boolean: 1420 | False |
| `personAssociations[].person.name.text` | 1000 (100.00%) | array: 1420 | array with 1 item(s) |
| `personAssociations[].person.name.text[]` | 1000 (100.00%) | object: 1420 | object keys: value |
| `personAssociations[].person.name.text[].value` | 1000 (100.00%) | string: 1420 | Александр Иванович Кубышкин |
| `personAssociations[].person.uuid` | 1000 (100.00%) | string: 1420 | c9be961a-6b7e-4381-bdd2-efb2e7cf4864 |
| `personAssociations[].personRole` | 1000 (100.00%) | object: 2338 | object keys: pureId, uri, term |
| `personAssociations[].personRole.pureId` | 1000 (100.00%) | integer: 2338 | 16882 |
| `personAssociations[].personRole.term` | 1000 (100.00%) | object: 2338 | object keys: formatted, text |
| `personAssociations[].personRole.term.formatted` | 1000 (100.00%) | boolean: 2338 | False |
| `personAssociations[].personRole.term.text` | 1000 (100.00%) | array: 2338 | array with 2 item(s) |
| `personAssociations[].personRole.term.text[]` | 1000 (100.00%) | object: 4676 | object keys: locale, value |
| `personAssociations[].personRole.term.text[].locale` | 1000 (100.00%) | string: 4676 | en_US |
| `personAssociations[].personRole.term.text[].value` | 1000 (100.00%) | string: 4676 | Author |
| `personAssociations[].personRole.uri` | 1000 (100.00%) | string: 2338 | /dk/atira/pure/researchoutput/roles/contributiontojournal/author |
| `personAssociations[].pureId` | 1000 (100.00%) | integer: 2338 | 3732233 |
| `personAssociations[].organisationalUnits` | 709 (70.90%) | array: 1078 | array with 1 item(s) |
| `personAssociations[].organisationalUnits[]` | 709 (70.90%) | object: 1103 | object keys: uuid, link, externalId, externalIdSource, externallyManaged, name, type |
| `personAssociations[].organisationalUnits[].externalId` | 709 (70.90%) | string: 1103 | 50069336 |
| `personAssociations[].organisationalUnits[].externalIdSource` | 709 (70.90%) | string: 1103 | synchronisedUnifiedOrganisation |
| `personAssociations[].organisationalUnits[].link` | 709 (70.90%) | object: 1103 | object keys: ref, href |
| `personAssociations[].organisationalUnits[].link.href` | 709 (70.90%) | string: 1103 | http://localhost:8080/ws/api/522/organisational-units/1e4b7829-b1ed-40be-b417-303f648cf826 |
| `personAssociations[].organisationalUnits[].link.ref` | 709 (70.90%) | string: 1103 | content |
| `personAssociations[].organisationalUnits[].name` | 709 (70.90%) | object: 1103 | object keys: formatted, text |
| `personAssociations[].organisationalUnits[].name.formatted` | 709 (70.90%) | boolean: 1103 | False |
| `personAssociations[].organisationalUnits[].name.text` | 709 (70.90%) | array: 1103 | array with 2 item(s) |
| `personAssociations[].organisationalUnits[].name.text[]` | 709 (70.90%) | object: 2203 | object keys: locale, value |
| `personAssociations[].organisationalUnits[].name.text[].locale` | 709 (70.90%) | string: 2203 | en_US |
| `personAssociations[].organisationalUnits[].name.text[].value` | 709 (70.90%) | string: 2203 | Department of Theory and Methodology for Teaching Arts andHumanities |
| `personAssociations[].organisationalUnits[].type` | 709 (70.90%) | object: 1103 | object keys: pureId, uri, term |
| `personAssociations[].organisationalUnits[].type.pureId` | 709 (70.90%) | integer: 1103 | 17281 |
| `personAssociations[].organisationalUnits[].type.term` | 709 (70.90%) | object: 1103 | object keys: formatted, text |
| `personAssociations[].organisationalUnits[].type.term.formatted` | 709 (70.90%) | boolean: 1103 | False |
| `personAssociations[].organisationalUnits[].type.term.text` | 709 (70.90%) | array: 1103 | array with 2 item(s) |
| `personAssociations[].organisationalUnits[].type.term.text[]` | 709 (70.90%) | object: 2206 | object keys: locale, value |
| `personAssociations[].organisationalUnits[].type.term.text[].locale` | 709 (70.90%) | string: 2206 | en_US |
| `personAssociations[].organisationalUnits[].type.term.text[].value` | 709 (70.90%) | string: 2206 | Level 2 |
| `personAssociations[].organisationalUnits[].type.uri` | 709 (70.90%) | string: 1103 | /dk/atira/pure/organisation/organisationtypes/organisation/level_2 |
| `personAssociations[].organisationalUnits[].uuid` | 709 (70.90%) | string: 1103 | 1e4b7829-b1ed-40be-b417-303f648cf826 |
| `personAssociations[].person.externallyManaged` | 706 (70.60%) | boolean: 949 | True |
| `personAssociations[].organisationalUnits[].externallyManaged` | 692 (69.20%) | boolean: 1050 | True |
| `personAssociations[].externalOrganisations` | 611 (61.10%) | array: 1353 | array with 1 item(s) |
| `personAssociations[].externalOrganisations[]` | 611 (61.10%) | object: 1505 | object keys: uuid, link, externalId, externalIdSource, name, type |
| `personAssociations[].externalOrganisations[].link` | 611 (61.10%) | object: 1505 | object keys: ref, href |
| `personAssociations[].externalOrganisations[].link.href` | 611 (61.10%) | string: 1505 | http://localhost:8080/ws/api/522/external-organisations/88ad36ec-b7d4-46c9-bbb5-fe3e3bd5e7cf |
| `personAssociations[].externalOrganisations[].link.ref` | 611 (61.10%) | string: 1505 | content |
| `personAssociations[].externalOrganisations[].name` | 611 (61.10%) | object: 1505 | object keys: formatted, text |
| `personAssociations[].externalOrganisations[].name.formatted` | 611 (61.10%) | boolean: 1505 | False |
| `personAssociations[].externalOrganisations[].name.text` | 611 (61.10%) | array: 1505 | array with 2 item(s) |
| `personAssociations[].externalOrganisations[].name.text[]` | 611 (61.10%) | object: 2913 | object keys: locale, value |
| `personAssociations[].externalOrganisations[].name.text[].locale` | 611 (61.10%) | string: 2913 | en_US |
| `personAssociations[].externalOrganisations[].name.text[].value` | 611 (61.10%) | string: 2913 | unknown |
| `personAssociations[].externalOrganisations[].type` | 611 (61.10%) | object: 1505 | object keys: pureId, uri, term |
| `personAssociations[].externalOrganisations[].type.pureId` | 611 (61.10%) | integer: 1505 | 996 |
| `personAssociations[].externalOrganisations[].type.term` | 611 (61.10%) | object: 1505 | object keys: formatted, text |
| `personAssociations[].externalOrganisations[].type.term.formatted` | 611 (61.10%) | boolean: 1505 | False |
| `personAssociations[].externalOrganisations[].type.term.text` | 611 (61.10%) | array: 1505 | array with 2 item(s) |
| `personAssociations[].externalOrganisations[].type.term.text[]` | 611 (61.10%) | object: 3010 | object keys: locale, value |
| `personAssociations[].externalOrganisations[].type.term.text[].locale` | 611 (61.10%) | string: 3010 | en_US |
| `personAssociations[].externalOrganisations[].type.term.text[].value` | 611 (61.10%) | string: 3010 | Unknown |
| `personAssociations[].externalOrganisations[].type.uri` | 611 (61.10%) | string: 1505 | /dk/atira/pure/ueoexternalorganisation/ueoexternalorganisationtypes/ueoexternalorganisation/unknown |
| `personAssociations[].externalOrganisations[].uuid` | 611 (61.10%) | string: 1505 | 88ad36ec-b7d4-46c9-bbb5-fe3e3bd5e7cf |
| `personAssociations[].externalOrganisations[].externalId` | 610 (61.00%) | string: 1500 | 655395 |
| `personAssociations[].externalOrganisations[].externalIdSource` | 610 (61.00%) | string: 1500 | researchoutputwizard |
| `personAssociations[].externalPerson` | 334 (33.40%) | object: 918 | object keys: uuid, link, name, type |
| `personAssociations[].externalPerson.link` | 334 (33.40%) | object: 918 | object keys: ref, href |
| `personAssociations[].externalPerson.link.href` | 334 (33.40%) | string: 918 | http://localhost:8080/ws/api/522/external-persons/476f6cdd-1887-4595-8389-517015b17486 |
| `personAssociations[].externalPerson.link.ref` | 334 (33.40%) | string: 918 | content |
| `personAssociations[].externalPerson.name` | 334 (33.40%) | object: 918 | object keys: formatted, text |
| `personAssociations[].externalPerson.name.formatted` | 334 (33.40%) | boolean: 918 | False |
| `personAssociations[].externalPerson.name.text` | 334 (33.40%) | array: 918 | array with 1 item(s) |
| `personAssociations[].externalPerson.name.text[]` | 334 (33.40%) | object: 918 | object keys: value |
| `personAssociations[].externalPerson.name.text[].value` | 334 (33.40%) | string: 918 | В. В. Орлов |
| `personAssociations[].externalPerson.type` | 334 (33.40%) | object: 918 | object keys: pureId, uri, term |
| `personAssociations[].externalPerson.type.pureId` | 334 (33.40%) | integer: 918 | 16827 |
| `personAssociations[].externalPerson.type.term` | 334 (33.40%) | object: 918 | object keys: formatted, text |
| `personAssociations[].externalPerson.type.term.formatted` | 334 (33.40%) | boolean: 918 | False |
| `personAssociations[].externalPerson.type.term.text` | 334 (33.40%) | array: 918 | array with 2 item(s) |
| `personAssociations[].externalPerson.type.term.text[]` | 334 (33.40%) | object: 1836 | object keys: locale, value |
| `personAssociations[].externalPerson.type.term.text[].locale` | 334 (33.40%) | string: 1836 | en_US |
| `personAssociations[].externalPerson.type.term.text[].value` | 334 (33.40%) | string: 1836 | External person |
| `personAssociations[].externalPerson.type.uri` | 334 (33.40%) | string: 918 | /dk/atira/pure/externalperson/externalpersontypes/externalperson/externalperson |
| `personAssociations[].externalPerson.uuid` | 334 (33.40%) | string: 918 | 476f6cdd-1887-4595-8389-517015b17486 |
| `personAssociations[].country` | 3 (0.30%) | object: 5 | object keys: pureId, uri, term |
| `personAssociations[].country.pureId` | 3 (0.30%) | integer: 5 | 597 |
| `personAssociations[].country.term` | 3 (0.30%) | object: 5 | object keys: formatted, text |
| `personAssociations[].country.term.formatted` | 3 (0.30%) | boolean: 5 | False |
| `personAssociations[].country.term.text` | 3 (0.30%) | array: 5 | array with 2 item(s) |
| `personAssociations[].country.term.text[]` | 3 (0.30%) | object: 10 | object keys: locale, value |
| `personAssociations[].country.term.text[].locale` | 3 (0.30%) | string: 10 | en_US |
| `personAssociations[].country.term.text[].value` | 3 (0.30%) | string: 10 | Russian Federation |
| `personAssociations[].country.uri` | 3 (0.30%) | string: 5 | /dk/atira/pure/core/countries/ru |
| `personAssociations[].externalPerson.externalId` | 1 (0.10%) | string: 1 | 50017043 |
| `personAssociations[].externalPerson.externalIdSource` | 1 (0.10%) | string: 1 | researchoutputwizard |

## Поле `keywordGroups`

### Размер массивов

- Минимум элементов: **1**
- Среднее количество элементов: **1.28**
- Максимум элементов: **3**

### Первый непустой пример

```json
[
  {
    "pureId": 3794845,
    "logicalName": "/dk/atira/pure/keywords/esi_plus",
    "type": {
      "uri": "/dk/atira/pure/keywords/esi_plus",
      "term": {
        "formatted": false,
        "text": [
          {
            "locale": "en_US",
            "value": "ESI extended"
          },
          {
            "locale": "ru_RU",
            "value": "Область знаний WoS"
          }
        ]
      }
    },
    "keywordContainers": [
      {
        "pureId": 3794846,
        "structuredKeyword": {
          "pureId": 513805,
          "uri": "/dk/atira/pure/keywords/esi_plus/6491",
          "term": {
            "formatted": false,
            "text": [
              {
                "locale": "en_US",
                "value": "SOCIAL SCIENCES, GENERAL"
              },
              {
                "locale": "ru_RU",
                "value": "Общественные науки"
              }
            ]
          }
        }
      }
    ]
  },
  {
    "pureId": 3794842,
    "logicalName": "keywordContainers",
    "type": {
      "term": {
        "formatted": false,
        "text": [
          {
            "locale": "en_US",
            "value": "Keywords"
          },
          {
            "locale": "ru_RU",
            "value": "Ключевые слова"
          }
        ]
      }
    },
    "keywordContainers": [
      {
        "pureId": 3794843,
        "freeKeywords": [
          {
            "pureId": 3794844,
            "locale": "en_US",
            "freeKeywords": [
              "Приграничное сотрудничество",
              "Северная Европа",
              "города -партнеры."
            ]
          }
        ]
      }
    ]
  }
]
```

### Обнаруженные вложенные пути

| JSON-путь | Публикаций с путём | Типы значений | Пример |
|---|---:|---|---|
| `keywordGroups` | 991 (99.10%) | array: 991 | array with 2 item(s) |
| `keywordGroups[]` | 991 (99.10%) | object: 1267 | object keys: pureId, logicalName, type, keywordContainers |
| `keywordGroups[].keywordContainers` | 991 (99.10%) | array: 1267 | array with 1 item(s) |
| `keywordGroups[].keywordContainers[]` | 991 (99.10%) | object: 1293 | object keys: pureId, structuredKeyword |
| `keywordGroups[].keywordContainers[].pureId` | 991 (99.10%) | integer: 1293 | 3794846 |
| `keywordGroups[].logicalName` | 991 (99.10%) | string: 1267 | /dk/atira/pure/keywords/esi_plus |
| `keywordGroups[].pureId` | 991 (99.10%) | integer: 1267 | 3794845 |
| `keywordGroups[].type` | 991 (99.10%) | object: 1267 | object keys: uri, term |
| `keywordGroups[].type.term` | 991 (99.10%) | object: 1267 | object keys: formatted, text |
| `keywordGroups[].type.term.formatted` | 991 (99.10%) | boolean: 1267 | False |
| `keywordGroups[].type.term.text` | 991 (99.10%) | array: 1267 | array with 2 item(s) |
| `keywordGroups[].type.term.text[]` | 991 (99.10%) | object: 2534 | object keys: locale, value |
| `keywordGroups[].type.term.text[].locale` | 991 (99.10%) | string: 2534 | en_US |
| `keywordGroups[].type.term.text[].value` | 991 (99.10%) | string: 2534 | ESI extended |
| `keywordGroups[].keywordContainers[].structuredKeyword` | 988 (98.80%) | object: 1055 | object keys: pureId, uri, term |
| `keywordGroups[].keywordContainers[].structuredKeyword.pureId` | 988 (98.80%) | integer: 1055 | 513805 |
| `keywordGroups[].keywordContainers[].structuredKeyword.term` | 988 (98.80%) | object: 1055 | object keys: formatted, text |
| `keywordGroups[].keywordContainers[].structuredKeyword.term.formatted` | 988 (98.80%) | boolean: 1055 | False |
| `keywordGroups[].keywordContainers[].structuredKeyword.term.text` | 988 (98.80%) | array: 1055 | array with 2 item(s) |
| `keywordGroups[].keywordContainers[].structuredKeyword.term.text[]` | 988 (98.80%) | object: 2110 | object keys: locale, value |
| `keywordGroups[].keywordContainers[].structuredKeyword.term.text[].locale` | 988 (98.80%) | string: 2110 | en_US |
| `keywordGroups[].keywordContainers[].structuredKeyword.term.text[].value` | 988 (98.80%) | string: 2110 | SOCIAL SCIENCES, GENERAL |
| `keywordGroups[].keywordContainers[].structuredKeyword.uri` | 988 (98.80%) | string: 1055 | /dk/atira/pure/keywords/esi_plus/6491 |
| `keywordGroups[].type.uri` | 988 (98.80%) | string: 1029 | /dk/atira/pure/keywords/esi_plus |
| `keywordGroups[].keywordContainers[].freeKeywords` | 238 (23.80%) | array: 238 | array with 1 item(s) |
| `keywordGroups[].keywordContainers[].freeKeywords[]` | 238 (23.80%) | object: 241 | object keys: pureId, locale, freeKeywords |
| `keywordGroups[].keywordContainers[].freeKeywords[].freeKeywords` | 238 (23.80%) | array: 241 | array with 3 item(s) |
| `keywordGroups[].keywordContainers[].freeKeywords[].freeKeywords[]` | 238 (23.80%) | string: 1043 | Приграничное сотрудничество |
| `keywordGroups[].keywordContainers[].freeKeywords[].locale` | 238 (23.80%) | string: 241 | en_US |
| `keywordGroups[].keywordContainers[].freeKeywords[].pureId` | 238 (23.80%) | integer: 241 | 3794844 |

## Поле `managingOrganisationalUnit`

### Первый непустой пример

```json
{
  "uuid": "09971b19-384c-4b78-b17c-6ea2921a31a7",
  "link": {
    "ref": "content",
    "href": "http://localhost:8080/ws/api/522/organisational-units/09971b19-384c-4b78-b17c-6ea2921a31a7"
  },
  "externalId": "50110267",
  "externalIdSource": "synchronisedUnifiedOrganisation",
  "externallyManaged": true,
  "name": {
    "formatted": false,
    "text": [
      {
        "locale": "en_US",
        "value": "Directorate on Human Resources"
      },
      {
        "locale": "ru_RU",
        "value": "Главное управление по организации работы с персоналом"
      }
    ]
  },
  "type": {
    "pureId": 17281,
    "uri": "/dk/atira/pure/organisation/organisationtypes/organisation/level_2",
    "term": {
      "formatted": false,
      "text": [
        {
          "locale": "en_US",
          "value": "Level 2"
        },
        {
          "locale": "ru_RU",
          "value": "2 уровень"
        }
      ]
    }
  }
}
```

### Обнаруженные вложенные пути

| JSON-путь | Публикаций с путём | Типы значений | Пример |
|---|---:|---|---|
| `managingOrganisationalUnit` | 1000 (100.00%) | object: 1000 | object keys: uuid, link, externalId, externalIdSource, externallyManaged, name, type |
| `managingOrganisationalUnit.externalId` | 1000 (100.00%) | string: 1000 | 50110267 |
| `managingOrganisationalUnit.externalIdSource` | 1000 (100.00%) | string: 1000 | synchronisedUnifiedOrganisation |
| `managingOrganisationalUnit.link` | 1000 (100.00%) | object: 1000 | object keys: ref, href |
| `managingOrganisationalUnit.link.href` | 1000 (100.00%) | string: 1000 | http://localhost:8080/ws/api/522/organisational-units/09971b19-384c-4b78-b17c-6ea2921a31a7 |
| `managingOrganisationalUnit.link.ref` | 1000 (100.00%) | string: 1000 | content |
| `managingOrganisationalUnit.name` | 1000 (100.00%) | object: 1000 | object keys: formatted, text |
| `managingOrganisationalUnit.name.formatted` | 1000 (100.00%) | boolean: 1000 | False |
| `managingOrganisationalUnit.name.text` | 1000 (100.00%) | array: 1000 | array with 2 item(s) |
| `managingOrganisationalUnit.name.text[]` | 1000 (100.00%) | object: 2000 | object keys: locale, value |
| `managingOrganisationalUnit.name.text[].locale` | 1000 (100.00%) | string: 2000 | en_US |
| `managingOrganisationalUnit.name.text[].value` | 1000 (100.00%) | string: 2000 | Directorate on Human Resources |
| `managingOrganisationalUnit.type` | 1000 (100.00%) | object: 1000 | object keys: pureId, uri, term |
| `managingOrganisationalUnit.type.pureId` | 1000 (100.00%) | integer: 1000 | 17281 |
| `managingOrganisationalUnit.type.term` | 1000 (100.00%) | object: 1000 | object keys: formatted, text |
| `managingOrganisationalUnit.type.term.formatted` | 1000 (100.00%) | boolean: 1000 | False |
| `managingOrganisationalUnit.type.term.text` | 1000 (100.00%) | array: 1000 | array with 2 item(s) |
| `managingOrganisationalUnit.type.term.text[]` | 1000 (100.00%) | object: 2000 | object keys: locale, value |
| `managingOrganisationalUnit.type.term.text[].locale` | 1000 (100.00%) | string: 2000 | en_US |
| `managingOrganisationalUnit.type.term.text[].value` | 1000 (100.00%) | string: 2000 | Level 2 |
| `managingOrganisationalUnit.type.uri` | 1000 (100.00%) | string: 1000 | /dk/atira/pure/organisation/organisationtypes/organisation/level_2 |
| `managingOrganisationalUnit.uuid` | 1000 (100.00%) | string: 1000 | 09971b19-384c-4b78-b17c-6ea2921a31a7 |
| `managingOrganisationalUnit.externallyManaged` | 997 (99.70%) | boolean: 997 | True |

## Поле `organisationalUnits`

### Размер массивов

- Минимум элементов: **1**
- Среднее количество элементов: **1.23**
- Максимум элементов: **4**

### Первый непустой пример

```json
[
  {
    "uuid": "1e4b7829-b1ed-40be-b417-303f648cf826",
    "link": {
      "ref": "content",
      "href": "http://localhost:8080/ws/api/522/organisational-units/1e4b7829-b1ed-40be-b417-303f648cf826"
    },
    "externalId": "50069336",
    "externalIdSource": "synchronisedUnifiedOrganisation",
    "externallyManaged": true,
    "name": {
      "formatted": false,
      "text": [
        {
          "locale": "en_US",
          "value": "Department of Theory and Methodology for Teaching Arts andHumanities"
        },
        {
          "locale": "ru_RU",
          "value": "Кафедра теории и методики преподавания искусств и гуманитарных наук"
        }
      ]
    },
    "type": {
      "pureId": 17281,
      "uri": "/dk/atira/pure/organisation/organisationtypes/organisation/level_2",
      "term": {
        "formatted": false,
        "text": [
          {
            "locale": "en_US",
            "value": "Level 2"
          },
          {
            "locale": "ru_RU",
            "value": "2 уровень"
          }
        ]
      }
    }
  }
]
```

### Обнаруженные вложенные пути

| JSON-путь | Публикаций с путём | Типы значений | Пример |
|---|---:|---|---|
| `organisationalUnits` | 709 (70.90%) | array: 709 | array with 1 item(s) |
| `organisationalUnits[]` | 709 (70.90%) | object: 870 | object keys: uuid, link, externalId, externalIdSource, externallyManaged, name, type |
| `organisationalUnits[].externalId` | 709 (70.90%) | string: 870 | 50069336 |
| `organisationalUnits[].externalIdSource` | 709 (70.90%) | string: 870 | synchronisedUnifiedOrganisation |
| `organisationalUnits[].link` | 709 (70.90%) | object: 870 | object keys: ref, href |
| `organisationalUnits[].link.href` | 709 (70.90%) | string: 870 | http://localhost:8080/ws/api/522/organisational-units/1e4b7829-b1ed-40be-b417-303f648cf826 |
| `organisationalUnits[].link.ref` | 709 (70.90%) | string: 870 | content |
| `organisationalUnits[].name` | 709 (70.90%) | object: 870 | object keys: formatted, text |
| `organisationalUnits[].name.formatted` | 709 (70.90%) | boolean: 870 | False |
| `organisationalUnits[].name.text` | 709 (70.90%) | array: 870 | array with 2 item(s) |
| `organisationalUnits[].name.text[]` | 709 (70.90%) | object: 1737 | object keys: locale, value |
| `organisationalUnits[].name.text[].locale` | 709 (70.90%) | string: 1737 | en_US |
| `organisationalUnits[].name.text[].value` | 709 (70.90%) | string: 1737 | Department of Theory and Methodology for Teaching Arts andHumanities |
| `organisationalUnits[].type` | 709 (70.90%) | object: 870 | object keys: pureId, uri, term |
| `organisationalUnits[].type.pureId` | 709 (70.90%) | integer: 870 | 17281 |
| `organisationalUnits[].type.term` | 709 (70.90%) | object: 870 | object keys: formatted, text |
| `organisationalUnits[].type.term.formatted` | 709 (70.90%) | boolean: 870 | False |
| `organisationalUnits[].type.term.text` | 709 (70.90%) | array: 870 | array with 2 item(s) |
| `organisationalUnits[].type.term.text[]` | 709 (70.90%) | object: 1740 | object keys: locale, value |
| `organisationalUnits[].type.term.text[].locale` | 709 (70.90%) | string: 1740 | en_US |
| `organisationalUnits[].type.term.text[].value` | 709 (70.90%) | string: 1740 | Level 2 |
| `organisationalUnits[].type.uri` | 709 (70.90%) | string: 870 | /dk/atira/pure/organisation/organisationtypes/organisation/level_2 |
| `organisationalUnits[].uuid` | 709 (70.90%) | string: 870 | 1e4b7829-b1ed-40be-b417-303f648cf826 |
| `organisationalUnits[].externallyManaged` | 692 (69.20%) | boolean: 824 | True |

## Поле `type`

### Первый непустой пример

```json
{
  "pureId": 3985,
  "uri": "/dk/atira/pure/researchoutput/researchoutputtypes/contributiontojournal/book",
  "term": {
    "formatted": false,
    "text": [
      {
        "locale": "en_US",
        "value": "Book/Film/Article review"
      },
      {
        "locale": "ru_RU",
        "value": "рецензия"
      }
    ]
  }
}
```

### Обнаруженные вложенные пути

| JSON-путь | Публикаций с путём | Типы значений | Пример |
|---|---:|---|---|
| `type` | 1000 (100.00%) | object: 1000 | object keys: pureId, uri, term |
| `type.pureId` | 1000 (100.00%) | integer: 1000 | 3985 |
| `type.term` | 1000 (100.00%) | object: 1000 | object keys: formatted, text |
| `type.term.formatted` | 1000 (100.00%) | boolean: 1000 | False |
| `type.term.text` | 1000 (100.00%) | array: 1000 | array with 2 item(s) |
| `type.term.text[]` | 1000 (100.00%) | object: 2000 | object keys: locale, value |
| `type.term.text[].locale` | 1000 (100.00%) | string: 2000 | en_US |
| `type.term.text[].value` | 1000 (100.00%) | string: 2000 | Book/Film/Article review |
| `type.uri` | 1000 (100.00%) | string: 1000 | /dk/atira/pure/researchoutput/researchoutputtypes/contributiontojournal/book |

## Поле `category`

### Первый непустой пример

```json
{
  "pureId": 3937,
  "uri": "/dk/atira/pure/researchoutput/category/research",
  "term": {
    "formatted": false,
    "text": [
      {
        "locale": "en_US",
        "value": "Research"
      },
      {
        "locale": "ru_RU",
        "value": "научная"
      }
    ]
  }
}
```

### Обнаруженные вложенные пути

| JSON-путь | Публикаций с путём | Типы значений | Пример |
|---|---:|---|---|
| `category` | 1000 (100.00%) | object: 1000 | object keys: pureId, uri, term |
| `category.pureId` | 1000 (100.00%) | integer: 1000 | 3937 |
| `category.term` | 1000 (100.00%) | object: 1000 | object keys: formatted, text |
| `category.term.formatted` | 1000 (100.00%) | boolean: 1000 | False |
| `category.term.text` | 1000 (100.00%) | array: 1000 | array with 2 item(s) |
| `category.term.text[]` | 1000 (100.00%) | object: 2000 | object keys: locale, value |
| `category.term.text[].locale` | 1000 (100.00%) | string: 2000 | en_US |
| `category.term.text[].value` | 1000 (100.00%) | string: 2000 | Research |
| `category.uri` | 1000 (100.00%) | string: 1000 | /dk/atira/pure/researchoutput/category/research |

## Поле `language`

### Первый непустой пример

```json
{
  "pureId": 189,
  "uri": "/dk/atira/pure/core/languages/en_GB",
  "term": {
    "formatted": false,
    "text": [
      {
        "locale": "en_US",
        "value": "English"
      },
      {
        "locale": "ru_RU",
        "value": "Английский"
      }
    ]
  }
}
```

### Обнаруженные вложенные пути

| JSON-путь | Публикаций с путём | Типы значений | Пример |
|---|---:|---|---|
| `language` | 1000 (100.00%) | object: 1000 | object keys: pureId, uri, term |
| `language.pureId` | 1000 (100.00%) | integer: 1000 | 189 |
| `language.term` | 1000 (100.00%) | object: 1000 | object keys: formatted, text |
| `language.term.formatted` | 1000 (100.00%) | boolean: 1000 | False |
| `language.term.text` | 1000 (100.00%) | array: 1000 | array with 2 item(s) |
| `language.term.text[]` | 1000 (100.00%) | object: 2000 | object keys: locale, value |
| `language.term.text[].locale` | 1000 (100.00%) | string: 2000 | en_US |
| `language.term.text[].value` | 1000 (100.00%) | string: 2000 | English |
| `language.uri` | 1000 (100.00%) | string: 1000 | /dk/atira/pure/core/languages/en_GB |

## Как использовать результат

После анализа отчёта нужно определить точные пути к следующим значениям:

1. UUID исследователя.
2. Имя исследователя.
3. Роль автора.
4. Год публикации.
5. Название публикации.
6. Текст аннотации.
7. Ключевые слова.
8. Научные классификации.
9. Организационное подразделение.
