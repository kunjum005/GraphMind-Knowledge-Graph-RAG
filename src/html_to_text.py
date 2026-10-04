from pathlib import Path
from bs4 import BeautifulSoup


RAW_FOLDER = Path("DATASET/raw")
PROCESSED_FOLDER = Path("DATASET/processed")

PROCESSED_FOLDER.mkdir(parents=True, exist_ok=True)


html_files = list(RAW_FOLDER.glob("*.html"))

print(f"Found {len(html_files)} HTML files.")


for html_file in html_files:

    print(f"Processing: {html_file.name}")

    html_content = html_file.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove unnecessary HTML elements
    for element in soup([
        "script",
        "style",
        "noscript",
        "ix:header",
        "ix:hidden"
    ]):
        element.decompose()

    # Try to find the main document body
    body = soup.body

    if body:
        text = body.get_text(separator="\n")
    else:
        text = soup.get_text(separator="\n")

    # Clean lines
    lines = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        lines.append(line)

    clean_text = "\n".join(lines)

    output_file = PROCESSED_FOLDER / f"{html_file.stem}.txt"

    output_file.write_text(
        clean_text,
        encoding="utf-8"
    )

    print(f"Saved: {output_file.name}")


print("\nDone! All HTML files have been converted to TXT.")