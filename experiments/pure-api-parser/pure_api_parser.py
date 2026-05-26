import requests
import pandas as pd
import json
import logging
from typing import List, Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

# Настройки API

BASE_URL = "https://pure.spbu.ru"

RESEARCH_OUTPUTS_ENDPOINT = "/research-outputs"

API_TOKEN = "YOUR_API_TOKEN"
# количество публикаций
TARGET_PUBLICATIONS = 70

PAGE_SIZE = 25

def get_headers() -> Dict[str, str]:

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    # Если API требует токен
    if API_TOKEN and API_TOKEN != "YOUR_API_TOKEN":
        headers["api-key"] = API_TOKEN

    return headers

def send_get_request(
    endpoint: str,
    params: Dict[str, Any]
) -> Dict[str, Any]:

    url = BASE_URL + endpoint

    logger.info(f"Отправка запроса: {url}")
    logger.info(f"Параметры: {params}")

    try:
        response = requests.get(
            url,
            headers=get_headers(),
            params=params,
            timeout=30
        )

        logger.info(f"HTTP Status: {response.status_code}")

        response.raise_for_status()

        return response.json()

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP ошибка: {e}")
        raise

    except requests.exceptions.ConnectionError:
        logger.error("Ошибка соединения с API")
        raise

    except requests.exceptions.Timeout:
        logger.error("Таймаут запроса")
        raise

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка запроса: {e}")
        raise

    except json.JSONDecodeError:
        logger.error("Ошибка декодирования JSON")
        raise

def parse_research_output(item: Dict[str, Any]) -> Dict[str, Any]:

    title = ""

    if "title" in item:
        title = item["title"].get("value", "")

    publication_year = ""

    if "publicationStatuses" in item and item["publicationStatuses"]:
        publication_year = item["publicationStatuses"][0].get(
            "publicationDate", {}
        ).get("year", "")

    doi = ""

    if "electronicVersions" in item:
        for version in item["electronicVersions"]:
            if version.get("doi"):
                doi = version["doi"]
                break

    abstract = ""

    if "abstract" in item:
        abstract = item["abstract"].get("value", "")

    authors = []

    if "personAssociations" in item:
        for author in item["personAssociations"]:
            person = author.get("person", {})
            name = person.get("name", {})

            full_name = " ".join(
                filter(
                    None,
                    [
                        name.get("firstName"),
                        name.get("lastName")
                    ]
                )
            )

            if full_name:
                authors.append(full_name)

    return {
        "title": title,
        "authors": ", ".join(authors),
        "publication_year": publication_year,
        "doi": doi,
        "abstract": abstract
    }

def fetch_publications(
    organisation_id: str = None,
    person_id: str = None,
    limit: int = 50
) -> List[Dict[str, Any]]:

    all_publications = []

    offset = 0

    while len(all_publications) < limit:

        params = {
            "size": PAGE_SIZE,
            "offset": offset,
            "order": "publicationYear"
        }

        if organisation_id:
            params["organisations.uuid"] = organisation_id

        if person_id:
            params["persons.uuid"] = person_id

        logger.info(
            f"Загрузка публикаций: offset={offset}"
        )

        data = send_get_request(
            RESEARCH_OUTPUTS_ENDPOINT,
            params
        )

        items = data.get("items", [])

        if not items:
            logger.info("Публикации закончились")
            break

        for item in items:

            parsed_item = parse_research_output(item)

            all_publications.append(parsed_item)

            if len(all_publications) >= limit:
                break

        offset += PAGE_SIZE

    logger.info(
        f"Всего загружено публикаций: {len(all_publications)}"
    )

    return all_publications

def save_to_json(
    data: List[Dict[str, Any]],
    filename: str
):

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )

    logger.info(f"JSON сохранён: {filename}")

def save_to_csv(
    data: List[Dict[str, Any]],
    filename: str
):

    df = pd.DataFrame(data)

    df.to_csv(
        filename,
        index=False,
        encoding="utf-8-sig"
    )

    logger.info(f"CSV сохранён: {filename}")

def main():

    # UUID подразделения
    ORGANISATION_ID = "YOUR_ORGANISATION_UUID"

    # UUID автора
    PERSON_ID = None

    publications = fetch_publications(
        organisation_id=ORGANISATION_ID,
        person_id=PERSON_ID,
        limit=TARGET_PUBLICATIONS
    )

    save_to_json(
        publications,
        "publications.json"
    )

    save_to_csv(
        publications,
        "publications.csv"
    )

    logger.info("Работа завершена")


if __name__ == "__main__":
    main()