import re
import csv
from pathlib import Path
import json

import pypdfium2 as pdfium
from rapidocr import RapidOCR  # jeśli nie działa, spróbuj: from rapidocr_onnxruntime import RapidOCR


# ========= USTAWIENIA =========

# Główny folder z podfolderami "wypadek 1", "wypadek 2", ...
SCRIPT_DIR = Path(__file__).resolve().parent      # ...\HackNation\Python
BASE_DIR = SCRIPT_DIR.parent / "PDF"             # ...\HackNation\PDF

# Katalog wyjściowy na teksty (powstanie automatycznie)
OUTPUT_DIR = SCRIPT_DIR.parent / "OCR_OUTPUT"

# Minimalny próg pewności OCR – niższe linie odrzucamy (często pismo odręczne / szum)
MIN_SCORE = 0.70

OCR_ENGINE = RapidOCR(
    params={
        "Global.text_score": MIN_SCORE,     # globalny próg
        "Global.log_level": "error",        # mniej logów
    }
)
# Skala renderu PDF -> obraz (1 ≈ 72 dpi, 2 ≈ 144 dpi) – 2.0 jest szybkie, 2.5–3.0 dokładniejsze
RENDER_SCALE = 3.0


# ========= INICJALIZACJA OCR =========


# ========= FUNKCJE POMOCNICZE =========

def get_case_number(case_id: str) -> str:
    """
    Z nazwy folderu 'wypadek 10' wyciąga '10'.
    Jak nic nie znajdzie, zwraca oryginalny case_id.
    """
    m = re.search(r"\d+", case_id)
    return m.group(0) if m else case_id


def infer_output_filename(pdf_path: Path, case_number: str) -> str:
    """
    Na podstawie nazwy pliku PDF i numeru sprawy określa
    docelową nazwę pliku TXT.
    """
    name = pdf_path.stem.lower()

    if "opinia" in name:
        base = f"opinia {case_number}"
    elif "wyja" in name or "poszkodowan" in name:
        base = f"wyjaśnienia poszkodowanego {case_number}"
    elif "zawiadom" in name:
        base = f"zawiadomienie o wypadku {case_number}"
    else:
        # fallback – oryginalna nazwa + numer
        base = f"{pdf_path.stem} {case_number}"

    return base + ".txt"


def ocr_page_image(image):
    """
    Wykonuje OCR jednej strony (PIL Image) przy użyciu RapidOCR v3.x.
    Zwraca tekst z odfiltrowaniem niskich score'ów.
    """
    # NOWY sposób wywołania – jedno 'result', bez rozpakowywania
    result = OCR_ENGINE(image)

    # RapidOCROutput ma metodę to_json(), która zwraca listę słowników
    # w stylu: [{'box': [...], 'txt': 'tekst', 'score': 0.98}, ...]
    try:
        data = result.to_json()
    except AttributeError:
        # awaryjnie – jakby API się zmieniło, zwróć po prostu tekst z print(result)
        return str(result)

    # to_json może zwrócić listę lub stringa JSON – zabezpieczamy się na oba przypadki
    if isinstance(data, str):
        data = json.loads(data)

    lines = []
    for item in data:
        txt = item.get("txt", "").strip()
        score = item.get("score", 0.0)
        if txt and score >= MIN_SCORE:
            lines.append(txt)

    return "\n".join(lines)



def ocr_pdf(pdf_path: Path):
    """
    Renderuje PDF stronami -> obrazy (pypdfium2),
    robi OCR RapidOCR na każdej stronie,
    zwraca:
      - full_text: cały tekst dokumentu
      - rows: lista wierszy per strona (do CSV)
    """
    pdf = pdfium.PdfDocument(str(pdf_path))
    n_pages = len(pdf)

    all_text_parts = []
    rows = []

    for i in range(n_pages):
        page_index = i + 1
        page = pdf[i]

        # render strony -> PIL Image
        pil_image = page.render(scale=RENDER_SCALE).to_pil()

        # OCR strony
        page_text = ocr_page_image(pil_image)

        all_text_parts.append(f"\n\n===== STRONA {page_index} =====\n\n{page_text}")

        rows.append({
            "page": page_index,
            "text": page_text,
        })

    pdf.close()

    full_text = "".join(all_text_parts)
    return full_text, rows


def process_pdf(pdf_path: Path, case_id: str, case_number: str, case_output_dir: Path):
    """
    Przetwarza pojedynczy PDF:
    - OCR stron
    - zapis pliku TXT o nazwie typu:
        opinia {nr}.txt
        wyjaśnienia poszkodowanego {nr}.txt
        zawiadomienie o wypadku {nr}.txt
    - zwraca wiersze do zbiorczego CSV.
    """
    print(f"  Przetwarzam PDF: {pdf_path.name}")

    full_text, page_rows = ocr_pdf(pdf_path)
    out_filename = infer_output_filename(pdf_path, case_number)
    txt_output_path = case_output_dir / out_filename

    with open(txt_output_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"    Zapisano: {txt_output_path}")

    # Przygotuj wiersze do CSV (dodaj case_id, pdf_file)
    csv_rows = []
    for row in page_rows:
        csv_rows.append({
            "case_id": case_id,
            "pdf_file": pdf_path.name,
            "page": row["page"],
            "text": row["text"],
        })

    return csv_rows


def walk_cases(base_dir: Path):
    """
    Chodzi po wszystkich folderach spraw:
      PDF/wypadek 10, PDF/wypadek 11, ...
    Tworzy dla każdej sprawy:
      OCR_OUTPUT/wypadek 10/...
    Zwraca wszystkie wiersze do CSV.
    """
    all_rows = []

    OUTPUT_DIR.mkdir(exist_ok=True)

    for item in sorted(base_dir.iterdir()):
        if not item.is_dir():
            continue

        case_id = item.name  # np. "wypadek 10"
        case_number = get_case_number(case_id)

        print(f"\n==== Przetwarzam sprawę: {case_id} (nr: {case_number}) ====")

        pdf_files = list(item.glob("*.pdf"))
        if not pdf_files:
            print(f"  Brak plików PDF w folderze {item}")
            continue

        # Katalog wyjściowy dla tej sprawy
        case_output_dir = OUTPUT_DIR / case_id
        case_output_dir.mkdir(exist_ok=True)

        for pdf_path in pdf_files:
            try:
                rows = process_pdf(pdf_path, case_id, case_number, case_output_dir)
                all_rows.extend(rows)
            except Exception as e:
                print(f"  BŁĄD przy pliku {pdf_path.name}: {e}")

    return all_rows


def main():
    if not BASE_DIR.exists():
        raise FileNotFoundError(f"Katalog BASE_DIR nie istnieje: {BASE_DIR}")

    all_rows = walk_cases(BASE_DIR)

    if not all_rows:
        print("Nie zebrano żadnych danych OCR – sprawdź strukturę folderów i PDF-y.")
        return

    # Zapis zbiorczego CSV (do trenowania modelu później)
    output_csv = OUTPUT_DIR / "ocr_wyniki_szybki.csv"
    fieldnames = ["case_id", "pdf_file", "page", "text"]

    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print("\n=== GOTOWE (RapidOCR + pypdfium2, szybki OCR) ===")
    print(f"Zapisano zbiorczy plik z OCR: {output_csv}")


if __name__ == "__main__":
    main()