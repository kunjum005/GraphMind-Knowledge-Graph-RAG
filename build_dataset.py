import os, zipfile, requests

OUT_DIR = "dataset"
ZIP_NAME = "dataset.zip"

FILES = [
    ("01_Microsoft_10K_2025.html", "https://www.sec.gov/Archives/edgar/data/789019/000095017025100235/msft-20250630.htm"),
    ("02_Microsoft_Ex21_Subsidiaries_2025.html", "https://www.sec.gov/Archives/edgar/data/789019/000095017025100235/msft-ex21.htm"),
    ("03_Microsoft_8K_OpenAI_Partnership_2025.html", "https://www.sec.gov/Archives/edgar/data/789019/000119312525256310/msft-20251028.htm"),
    ("04_Activision_8K_Microsoft_Merger_2022.html", "https://www.sec.gov/Archives/edgar/data/718877/000110465922004729/tm223212d1_8k.htm"),
    ("05_Activision_10K_2022.html", "https://www.sec.gov/Archives/edgar/data/718877/000162828023004842/atvi-20221231.htm"),
    ("06_Activision_Ex21_Subsidiaries_2022.html", "https://www.sec.gov/Archives/edgar/data/718877/000162828023004842/atvi123122ex211.htm"),
    ("07_Amazon_10K_2025.html", "https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm"),
    ("08_Amazon_Ex21_Subsidiaries_2025.html", "https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231xex211.htm"),
    ("09_Flex_8K_Amazon_Transaction_2025.html", "https://www.sec.gov/Archives/edgar/data/866374/000110465925079795/tm2523681d1_8k.htm"),
    ("10_Flex_Ex10_1_Amazon_Transaction_Agreement_2025.html", "https://www.sec.gov/Archives/edgar/data/866374/000110465925079795/tm2523681d1_ex10-1.htm"),
]

os.makedirs(OUT_DIR, exist_ok=True)

headers = {
    "User-Agent": "GraphMind dataset research contact@example.com",
    "Accept-Encoding": "gzip, deflate",
}

for filename, url in FILES:
    r = requests.get(url, headers=headers, timeout=60)
    r.raise_for_status()
    with open(os.path.join(OUT_DIR, filename), "wb") as f:
        f.write(r.content)
    print(f"Downloaded: {filename} ({len(r.content):,} bytes)")

with zipfile.ZipFile(ZIP_NAME, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for filename, _ in FILES:
        z.write(os.path.join(OUT_DIR, filename), arcname=f"dataset/{filename}")

print(f"\nCreated {ZIP_NAME} with exactly {len(FILES)} source documents.")
