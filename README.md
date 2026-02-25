# Folder Tokenizer

Analyze token counts for all documents in a folder. Supports nested folders, zip files, and various document types.

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

## Tokenizer Accuracy

Different LLMs use different tokenization mechanisms. Token counts are model-specific:

| Model | Accuracy | Notes |
|---|---|---|
| **LLaMA 2/3, Mistral, Gemma** | Accurate | Official tokenizer repos from Meta, Mistral, Google |
| **GPT-4o** | Close | Community HuggingFace port of OpenAI's tiktoken vocabulary |
| **Claude** | Approximate | Anthropic hasn't published their tokenizer; counts are estimated |

**Important notes:**
- LLaMA and Gemma models require a HuggingFace access token (gated models)
- GPT-3.5 is not in the supported list; use GPT-4o for OpenAI model counts

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

### Web UI

**Streamlit** (cross-platform):
```bash
streamlit run src/folder_tokenizer/app.py
```

**Node.js** (macOS, includes native folder picker):
```bash
node server.js  # opens http://localhost:3000
```

### Command Line

Basic usage:
```bash
folder-tokenizer /path/to/folder --model gpt2
```

Common options:
```bash
# Show top 10 files by token count
folder-tokenizer /path/to/folder --verbose

# Quiet mode: output only the integer token count (useful for scripts)
folder-tokenizer /path/to/folder -q

# Export results as JSON or CSV
folder-tokenizer /path/to/folder --output results.json
folder-tokenizer /path/to/folder --csv results.csv

# Example: pipe token count to a variable
TOKEN_COUNT=$(folder-tokenizer /path/to/folder -q)
echo "Total tokens: $TOKEN_COUNT"
```

### Python API

Use folder-tokenizer as a library:
```python
from folder_tokenizer import FolderTokenizer

tokenizer = FolderTokenizer(model_name="gpt2")
result = tokenizer.process_folder("/path/to/folder")

print(f"Total tokens: {result.total_tokens}")
print(f"Total characters: {result.total_chars}")
print(f"Files processed: {len(result.files)}")
```

### When You're Over the Context Window

If a corpus is too large for your context window, use `--verbose` to identify the heaviest files, then:
- Exclude large generated files: `node_modules/`, `dist/`, `.git/`
- Exclude lock files: `*.lock`, `yarn.lock`, `package-lock.json`
- Use `--csv` to export results and manually select the most relevant files in a spreadsheet

## License

MIT
