import os, zipfile, requests

OUT_DIR = "dataset_2"
ZIP_NAME = "dataset_2.zip"

FILES = [
("11_Alphabet_10K_2025.html","https://www.sec.gov/Archives/edgar/data/1652044/000165204426000018/goog-20251231.htm"),
("12_Alphabet_Ex21_Subsidiaries_2025.html","https://www.sec.gov/Archives/edgar/data/1652044/000165204426000018/googexhibit2101q42025.htm"),
("13_Alphabet_8K_Wiz_Acquisition_2025.html","https://www.sec.gov/Archives/edgar/data/1652044/000165204425000027/goog-20250318.htm"),
("14_Alphabet_Ex991_Wiz_Acquisition_2025.html","https://www.sec.gov/Archives/edgar/data/1652044/000165204425000027/googexhibit99131825.htm"),
("15_NVIDIA_10K_2026.html","https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm"),
("16_NVIDIA_Ex21_Subsidiaries_2026.html","https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/subsidiariesofregistrantfy.htm"),
("17_CoreWeave_8K_Meta_Agreement_2025.html","https://www.sec.gov/Archives/edgar/data/1769628/000176962825000050/crwv-20250925.htm"),
("18_CoreWeave_8K_NVIDIA_Agreement_2025.html","https://www.sec.gov/Archives/edgar/data/1769628/000176962825000047/crwv-20250909.htm"),
("19_CoreWeave_8K_NVIDIA_Investment_2026.html","https://www.sec.gov/Archives/edgar/data/1769628/000176962826000044/crwv-20260123.htm"),
("20_Meta_10K_2025.html","https://www.sec.gov/Archives/edgar/data/1326801/000162828026003942/meta-20251231.htm"),
]

headers={"User-Agent":"GraphMind dataset research contact@example.com","Accept-Encoding":"gzip, deflate"}
os.makedirs(OUT_DIR, exist_ok=True)

for filename,url in FILES:
    r=requests.get(url,headers=headers,timeout=90)
    r.raise_for_status()
    with open(os.path.join(OUT_DIR,filename),"wb") as f:
        f.write(r.content)
    print("Downloaded:",filename)

with zipfile.ZipFile(ZIP_NAME,"w",zipfile.ZIP_DEFLATED) as z:
    for filename,_ in FILES:
        z.write(os.path.join(OUT_DIR,filename),arcname=f"dataset_2/{filename}")

print("Created",ZIP_NAME,"with exactly",len(FILES),"new SEC source documents.")
