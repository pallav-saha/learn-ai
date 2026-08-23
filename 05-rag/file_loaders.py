"""
File Loaders — Extract text from any file type for RAG

This script shows how to load text from:
1. PDF files (pdfplumber)
2. Word documents (.docx)
3. Excel / CSV files
4. Images (OCR - extract text from photos)
5. Audio files (transcribe with Whisper on Groq)

Each loader returns plain text that you can then chunk → embed → store in ChromaDB.

Run: python3 file_loaders.py
"""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


# ============================================================
# 1. PDF LOADER
# ============================================================

def load_pdf(filepath: str) -> str:
    """
    Extract text from a PDF file.
    
    Library: pdfplumber (better than PyPDF2 for tables and formatting)
    Install: pip install pdfplumber
    
    How it works:
    - Opens the PDF
    - Iterates through each page
    - Extracts all text from each page
    - Joins them together
    """
    import pdfplumber

    text_pages = []
    with pdfplumber.open(filepath) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                text_pages.append(f"--- Page {i + 1} ---\n{page_text}")

    full_text = "\n\n".join(text_pages)
    return full_text


# ============================================================
# 2. WORD DOCUMENT LOADER (.docx)
# ============================================================

def load_docx(filepath: str) -> str:
    """
    Extract text from a Word document (.docx).
    
    Library: python-docx
    Install: pip install python-docx
    
    How it works:
    - Opens the .docx file
    - Reads each paragraph
    - Joins them with newlines
    """
    from docx import Document

    doc = Document(filepath)
    paragraphs = []

    for para in doc.paragraphs:
        if para.text.strip():  # Skip empty paragraphs
            paragraphs.append(para.text)

    # Also extract text from tables (if any)
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells)
            if row_text.strip():
                paragraphs.append(row_text)

    return "\n\n".join(paragraphs)


# ============================================================
# 3. EXCEL / CSV LOADER
# ============================================================

def load_excel(filepath: str) -> str:
    """
    Convert Excel/CSV rows into natural language text.
    
    Library: pandas
    Install: pip install pandas openpyxl
    
    How it works:
    - Reads the spreadsheet into a DataFrame
    - Converts each row into a sentence
    - This makes it searchable by meaning (not just keywords)
    
    Example:
        Row: | Name: Alice | Age: 32 | Dept: Engineering |
        Text: "Alice is 32 years old and works in the Engineering department."
    """
    import pandas as pd

    # Detect file type
    if filepath.endswith(".csv"):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath)

    texts = []

    # Method 1: Convert each row to a descriptive sentence
    columns = df.columns.tolist()
    for _, row in df.iterrows():
        parts = [f"{col}: {row[col]}" for col in columns if pd.notna(row[col])]
        sentence = ", ".join(parts)
        texts.append(sentence)

    # Also add a summary header
    header = f"This data has {len(df)} rows and columns: {', '.join(columns)}"
    texts.insert(0, header)

    return "\n".join(texts)


def load_excel_as_summary(filepath: str) -> str:
    """
    Alternative: Give the LLM a summary + sample of the data.
    Better for analytical questions like "what's the total sales?"
    """
    import pandas as pd

    if filepath.endswith(".csv"):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath)

    summary = f"""Dataset Overview:
- Rows: {len(df)}
- Columns: {', '.join(df.columns.tolist())}
- Numeric columns summary:
{df.describe().to_string()}

First 10 rows:
{df.head(10).to_string()}
"""
    return summary


# ============================================================
# 4. IMAGE LOADER (OCR - Extract text from images)
# ============================================================

def load_image_ocr(filepath: str) -> str:
    """
    Extract text from an image using OCR (Optical Character Recognition).
    
    Library: pytesseract + Pillow
    Install: 
        pip install pytesseract Pillow
        brew install tesseract  (the OCR engine itself)
    
    How it works:
    - Opens the image
    - Runs Tesseract OCR to detect text in the image
    - Returns the detected text
    
    Good for: Screenshots, scanned documents, photos of whiteboards
    """
    from PIL import Image
    import pytesseract

    image = Image.open(filepath)
    text = pytesseract.image_to_string(image)

    return text.strip()


# ============================================================
# 5. AUDIO LOADER (Transcribe speech to text)
# ============================================================

def load_audio(filepath: str) -> str:
    """
    Transcribe audio to text using Groq's Whisper API (free!).
    
    Install: pip install openai (already installed)
    
    Supported formats: mp3, mp4, mpeg, mpga, m4a, wav, webm
    Max file size: 25MB on Groq's free tier
    
    How it works:
    - Sends audio file to Groq's Whisper model
    - Whisper converts speech to text
    - Returns the transcript
    
    Good for: Meeting recordings, podcasts, voice notes
    """
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )

    with open(filepath, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-large-v3",  # Free on Groq!
            file=audio_file,
        )

    return transcript.text


# ============================================================
# UNIVERSAL LOADER — Detects file type automatically
# ============================================================

def load_file(filepath: str) -> str:
    """
    Automatically detect file type and extract text.
    Just pass any file — it figures out which loader to use.
    """
    ext = os.path.splitext(filepath)[1].lower()

    loaders = {
        ".txt": lambda f: open(f).read(),
        ".pdf": load_pdf,
        ".docx": load_docx,
        ".doc": load_docx,
        ".xlsx": load_excel,
        ".xls": load_excel,
        ".csv": load_excel,
        ".png": load_image_ocr,
        ".jpg": load_image_ocr,
        ".jpeg": load_image_ocr,
        ".mp3": load_audio,
        ".wav": load_audio,
        ".m4a": load_audio,
        ".mp4": load_audio,
        ".webm": load_audio,
    }

    loader = loaders.get(ext)
    if loader is None:
        raise ValueError(f"Unsupported file type: {ext}")

    return loader(filepath)


# ============================================================
# DEMO — Show how each loader works
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  📁 FILE LOADERS — Extract text from any file type")
    print("=" * 60)

    print("""
This script provides loaders for:

  📄 PDF     → load_pdf("file.pdf")
  📝 Word    → load_docx("file.docx")
  📊 Excel   → load_excel("file.xlsx")
  🖼️  Images  → load_image_ocr("photo.png")
  🎙️  Audio   → load_audio("recording.mp3")
  🔄 Auto    → load_file("anything.xyz")  ← detects type automatically

Usage in your RAG pipeline:
    
    from file_loaders import load_file
    
    text = load_file("report.pdf")      # Extract text from PDF
    chunks = chunk_text(text)            # Split into chunks  
    collection.add(documents=chunks)     # Store in ChromaDB
    
Required packages (install as needed):
    
    pip install pdfplumber        # For PDFs
    pip install python-docx       # For Word docs
    pip install pandas openpyxl   # For Excel (pandas already installed)
    pip install pytesseract Pillow  # For OCR (also: brew install tesseract)
    # Audio uses Groq Whisper — already set up via openai package
""")

    # Try loading sample_docs if available
    sample_dir = os.path.join(os.path.dirname(__file__), "..", "sample_docs")
    if os.path.exists(sample_dir):
        print("-" * 60)
        print("📂 Loading files from sample_docs/:\n")
        for filename in sorted(os.listdir(sample_dir)):
            filepath = os.path.join(sample_dir, filename)
            try:
                text = load_file(filepath)
                preview = text[:150].replace("\n", " ") + "..."
                print(f"  ✅ {filename} ({len(text)} chars)")
                print(f"     Preview: {preview}\n")
            except ValueError as e:
                print(f"  ⚠️  {filename} — {e}\n")
            except ImportError as e:
                print(f"  ⚠️  {filename} — Missing library: {e}\n")
            except Exception as e:
                print(f"  ❌ {filename} — Error: {e}\n")
