#  id университета в OpenAlex(совпадает с SciSciNet-v2): i172901346
import os
import sys
import duckdb

hf_token = next(
    (arg.split("=", 1)[1] for arg in sys.argv[1:] if arg.startswith("t=")),
    os.environ.get("HUGGING_FACE_TOKEN"),
)
if not hf_token:
    raise SystemExit("Укажите токен: python build_faculty_csv.py t=<TOKEN>  или задайте HUGGING_FACE_TOKEN в окружении")

con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")
con.execute("SET VARIABLE hf_token = ?", [hf_token])
con.execute("CREATE SECRET (TYPE HUGGINGFACE, TOKEN getvariable('hf_token'));")
 
INSTITUTION_ID = "I172901346"
HF_DATASET = "Northwestern-CSSI/sciscinet-v2"

AFFILIATION_URL = f"hf://datasets/{HF_DATASET}/sciscinet_paper_author_affiliation.parquet"
PAPERS_URL = f"hf://datasets/{HF_DATASET}/sciscinet_papers.parquet"

# Шаг 1: фильтруем аффилиации — DuckDB тянет только нужные row groups через HTTP range requests
con.execute(
    f"CREATE TEMP TABLE aff AS SELECT paperid, institutionid, authorid FROM read_parquet('{AFFILIATION_URL}') WHERE institutionid = ?",
    [INSTITUTION_ID],
)

print(f"Найдено paper_id: {con.execute('SELECT COUNT(*) FROM aff').fetchone()[0]}")

# ids = con.execute("SELECT paperid FROM aff").fetchdf()['paperid'].tolist()

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
df = con.execute(f"""
    SELECT
        aff.paperid,
        aff.institutionid,
        list(aff.authorid) AS authorids,
        sp.year
    FROM aff
    LEFT JOIN read_parquet('{PAPERS_URL}') AS sp
        ON aff.paperid = sp.paperid
    GROUP BY aff.paperid, aff.institutionid, sp.year
    HAVING sp.year >= 2015
""").fetchdf()
df.to_csv('faculty_papers.csv', index=False)
print(f"Готово: {len(df)} статей сохранено в faculty_papers.csv")