# Folder Tokenizer

Analyze token counts for all documents in a folder using HuggingFace tokenizers. Supports nested folders, zip files, and various document types.

## Features

- **Multiple tokenizers**: Use any HuggingFace tokenizer (GPT-2, BERT, LLaMA, etc.)
- **Recursive scanning**: Handles nested folders and zip archives
- **Wide format support**: Text, code, PDF, DOCX, images (OCR), and more
- **Interactive UI**: Streamlit-based interface for easy use
- **Detailed reports**: Export results as CSV or JSON

## Supported File Types

- **Text**: `.txt`, `.md`, `.json`, `.csv`, `.xml`, `.yaml`, `.yml`
- **Code**: `.py`, `.js`, `.ts`, `.java`, `.c`, `.cpp`, `.go`, `.rs`, `.rb`, etc.
- **Documents**: `.pdf`, `.docx`
- **Images** (OCR): `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`
- **Archives**: `.zip` (automatically extracted and processed)

## Installation

```bash
# Clone the repository
git clone https://github.com/sgciv2805/folder-tokenizer
cd folder-tokenizer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install core dependencies (CLI only)
pip install -e .

# Or install with the Streamlit web UI
pip install -e ".[ui]"
```

### OCR Support (Optional)

For image OCR support, install Tesseract:

```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

## Usage

### Web UI (Streamlit)

```bash
streamlit run src/folder_tokenizer/app.py
```

### Command Line

```bash
folder-tokenizer /path/to/folder --model gpt2
```

## License

MIT
