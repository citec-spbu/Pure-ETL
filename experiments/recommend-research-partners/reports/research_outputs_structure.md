# Исследование структуры research-outputs.json

## Исходный файл

`C:\Users\Janna\Projects\Pure-ETL\Data\research-outputs.json`

## Общая информация

- Расположение массива записей: `field "items"`
- Количество записей: **1000**

- JSON-объектов: **1000**
- Записей другого типа: **0**

## Поля первой публикации

| Поле | Описание значения |
|---|---|
| `pureId` | int: 3732230 |
| `externalId` | str: 177302 |
| `externalIdSource` | str: researchoutputwizard |
| `uuid` | str: ad1188e7-9b4c-409f-8717-9be5eb1b9d41 |
| `title` | object; keys: formatted, value |
| `peerReview` | bool: False |
| `managingOrganisationalUnit` | object; keys: uuid, link, externalId, externalIdSource, externallyManaged, name, type |
| `confidential` | bool: False |
| `info` | object; keys: createdBy, createdDate, modifiedBy, modifiedDate, portalUrl, prettyURLIdentifiers, additionalExternalIds, previousUuids |
| `pages` | str: 169-171 |
| `journalAssociation` | object; keys: pureId, title, issn, journal |
| `journalNumber` | str: 3(13) |
| `type` | object; keys: pureId, uri, term |
| `category` | object; keys: pureId, uri, term |
| `language` | object; keys: pureId, uri, term |
| `totalNumberOfAuthors` | int: 1 |
| `openAccessPermission` | object; keys: pureId, uri, term |
| `visibility` | object; keys: key, value |
| `workflow` | object; keys: workflowStep, value |
| `publicationStatuses` | list with 1 item(s); first item type: dict |
| `personAssociations` | list with 1 item(s); first item type: dict |
| `organisationalUnits` | list with 1 item(s); first item type: dict |
| `keywordGroups` | list with 2 item(s); first item type: dict |

## Частота присутствия полей

| Поле | Записей с полем | Доля |
|---|---:|---:|
| `pureId` | 1000 из 1000 | 100.00% |
| `externalId` | 1000 из 1000 | 100.00% |
| `externalIdSource` | 1000 из 1000 | 100.00% |
| `uuid` | 1000 из 1000 | 100.00% |
| `title` | 1000 из 1000 | 100.00% |
| `managingOrganisationalUnit` | 1000 из 1000 | 100.00% |
| `confidential` | 1000 из 1000 | 100.00% |
| `info` | 1000 из 1000 | 100.00% |
| `type` | 1000 из 1000 | 100.00% |
| `category` | 1000 из 1000 | 100.00% |
| `language` | 1000 из 1000 | 100.00% |
| `totalNumberOfAuthors` | 1000 из 1000 | 100.00% |
| `openAccessPermission` | 1000 из 1000 | 100.00% |
| `visibility` | 1000 из 1000 | 100.00% |
| `workflow` | 1000 из 1000 | 100.00% |
| `publicationStatuses` | 1000 из 1000 | 100.00% |
| `personAssociations` | 1000 из 1000 | 100.00% |
| `keywordGroups` | 991 из 1000 | 99.10% |
| `journalAssociation` | 969 из 1000 | 96.90% |
| `pages` | 873 из 1000 | 87.30% |
| `organisationalUnits` | 709 из 1000 | 70.90% |
| `externalOrganisations` | 611 из 1000 | 61.10% |
| `electronicVersions` | 527 из 1000 | 52.70% |
| `peerReview` | 367 из 1000 | 36.70% |
| `totalScopusCitations` | 357 из 1000 | 35.70% |
| `fieldWeightedCitationImpact` | 357 из 1000 | 35.70% |
| `scopusMetrics` | 357 из 1000 | 35.70% |
| `volume` | 340 из 1000 | 34.00% |
| `journalNumber` | 244 из 1000 | 24.40% |
| `abstract` | 215 из 1000 | 21.50% |
| `internationalPeerReview` | 147 из 1000 | 14.70% |
| `numberOfPages` | 127 из 1000 | 12.70% |
| `number` | 49 из 1000 | 4.90% |
| `additionalLinks` | 40 из 1000 | 4.00% |
| `bibliographicalNote` | 36 из 1000 | 3.60% |
| `hostPublicationTitle` | 31 из 1000 | 3.10% |
| `publisher` | 28 из 1000 | 2.80% |
| `isbns` | 25 из 1000 | 2.50% |
| `event` | 16 из 1000 | 1.60% |
| `translatedTitle` | 13 из 1000 | 1.30% |
| `articleNumber` | 10 из 1000 | 1.00% |
| `publicationSeries` | 7 из 1000 | 0.70% |
| `relatedResearchOutputs` | 6 из 1000 | 0.60% |
| `electronicIsbns` | 6 из 1000 | 0.60% |
| `hostPublicationEditors` | 5 из 1000 | 0.50% |
| `relatedProjects` | 5 из 1000 | 0.50% |
| `additionalFiles` | 3 из 1000 | 0.30% |
| `relatedActivities` | 3 из 1000 | 0.30% |
| `subTitle` | 1 из 1000 | 0.10% |
| `articleProcessingChargePaid` | 1 из 1000 | 0.10% |

## Следующие действия

1. Определить поле идентификатора публикации
2. Исследовать структуру авторов
3. Найти названия, аннотации и годы публикаций
4. Найти ключевые слова и классификации
5. Оценить количество пропущенных значений
6. Подготовить таблицу связей «исследователь — публикация»
