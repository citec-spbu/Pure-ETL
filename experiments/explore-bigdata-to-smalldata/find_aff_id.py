#  id университета в OpenAlex(совпадает с SciSciNet-v2): i172901346
import duckdb
import requests
import time
import pyarrow.parquet as pq

con = duckdb.connect()

schema = pq.read_schema('./sciscinet_papers.parquet')
print("Схема таблицы:")
print(schema)

INSTITUTION_ID = "I172901346"  # ваш ID

# Шаг 1: достаём paper_id из локального файла
paper_ids = con.execute(f"""
    SELECT *
    FROM read_parquet('./data/sciscinet_paper_author_affiliation.parquet')
    WHERE institutionid = '{INSTITUTION_ID}'
""").fetchdf()

print(f"Найдено paper_id: {len(paper_ids)}")
ids = paper_ids['paperid'].tolist()

# Шаг 2: обогащаем через OpenAlex API батчами по 100
# results = []

# for i in range(0, len(ids), 100):
#     batch = ids[i:i+100]
#     short_ids = [x.replace('https://openalex.org/', '') for x in batch]
#     filter_str = '|'.join(short_ids)

#     resp = requests.get(
#         "https://api.openalex.org/works",
#         params={
#             "filter": f"openalex_id:{filter_str}",
#             "select": "id,doi,title,publication_year,cited_by_count",
#             "per-page": 100,
#         },
#         headers={"User-Agent": "mailto:ngannou252@mail.ru"}
#     )

#     if resp.status_code == 200:
#         results.extend(resp.json().get('results', []))

#     if i % 1000 == 0:
#         print(f"Обработано {i}/{len(ids)}...")
#     time.sleep(0.1)

# Шаг 3: фильтруем по году и сохраняем

# Группируем в DuckDB и джойним с sciscinet_papers.parquet — без загрузки всего файла в память
con.execute("CREATE TEMP TABLE aff AS SELECT * FROM read_parquet('./data/sciscinet_paper_author_affiliation.parquet') WHERE institutionid = '" + INSTITUTION_ID + "'")

df = con.execute("""
    SELECT
        aff.paperid,
        aff.institutionid,
        list(aff.authorid) AS authorids,
        sp.year
    FROM aff
    LEFT JOIN read_parquet('./sciscinet_papers.parquet') AS sp
        ON aff.paperid = sp.paperid
    GROUP BY aff.paperid, aff.institutionid, sp.year
    HAVING sp.year >= 2015
""").fetchdf()
df.to_csv('faculty_papers.csv', index=False)
print(f"Готово: {len(df)} статей сохранено в faculty_papers.csv")