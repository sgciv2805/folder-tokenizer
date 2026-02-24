"""Core tokenizer logic for analyzing folders."""

import os
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from tqdm import tqdm
from transformers import AutoTokenizer

from .processors import DocumentProcessor, ProcessingResult


@dataclass
class FileResult:
    """Result of tokenizing a single file."""

    path: str
    tokens: int
    chars: int
    file_type: str
    success: bool
    error: str | None = None
    source_archive: str | None = None  # If extracted from a zip


@dataclass
class FolderResult:
    """Result of tokenizing an entire folder."""

    folder_path: str
    model_name: str
    total_tokens: int = 0
    total_chars: int = 0
    total_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    file_results: list[FileResult] = field(default_factory=list)
    by_type: dict[str, dict] = field(default_factory=dict)

    def add_result(self, result: FileResult) -> None:
        """Add a file result to the folder result."""
        self.file_results.append(result)
        self.total_files += 1

        if result.success:
            self.successful_files += 1
            self.total_tokens += result.tokens
            self.total_chars += result.chars

            # Track by file type
            if result.file_type not in self.by_type:
                self.by_type[result.file_type] = {"tokens": 0, "chars": 0, "files": 0}
            self.by_type[result.file_type]["tokens"] += result.tokens
            self.by_type[result.file_type]["chars"] += result.chars
            self.by_type[result.file_type]["files"] += 1
        else:
            self.failed_files += 1


# Default model to use if none specified
DEFAULT_MODEL = "gpt2"

# Common tokenizer models for UI selection
POPULAR_MODELS = [
    # OpenAI-style (BPE)
    ("gpt2", "GPT-2 (OpenAI)"),
    ("Xenova/gpt-4o", "GPT-4o (OpenAI)"),
    ("Xenova/claude-tokenizer", "Claude (Anthropic)"),
    # Meta LLaMA
    ("meta-llama/Llama-2-7b-hf", "LLaMA 2 (Meta)"),
    ("meta-llama/Meta-Llama-3-8B", "LLaMA 3 (Meta)"),
    ("meta-llama/Llama-3.2-1B", "LLaMA 3.2 (Meta)"),
    # Mistral
    ("mistralai/Mistral-7B-v0.1", "Mistral 7B"),
    ("mistralai/Mixtral-8x7B-v0.1", "Mixtral 8x7B"),
    # Google (Gemini/Gemma use same tokenizer)
    ("google/gemma-2-2b", "Gemma 2 2B (Google)"),
    ("google/gemma-2-9b", "Gemma 2 9B (Google)"),
    ("google/gemma-2-27b", "Gemma 2 27B (Google)"),
    # Other popular models
    ("Qwen/Qwen2.5-7B", "Qwen 2.5 (Alibaba)"),
    ("microsoft/phi-2", "Phi-2 (Microsoft)"),
    ("deepseek-ai/DeepSeek-V2-Lite", "DeepSeek V2"),
    ("tiiuae/falcon-7b", "Falcon 7B (TII)"),
    # Encoder models
    ("bert-base-uncased", "BERT Base"),
    ("sentence-transformers/all-MiniLM-L6-v2", "MiniLM (Embeddings)"),
]


class FolderTokenizer:
    """Tokenize all documents in a folder."""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        """Initialize with a HuggingFace tokenizer model.

        Args:
            model_name: HuggingFace model name/path for the tokenizer
        """
        self.model_name = model_name
        self._tokenizer = None
        self.processor = DocumentProcessor()

    @property
    def tokenizer(self):
        """Lazy-load the tokenizer."""
        if self._tokenizer is None:
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        return self._tokenizer

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if not text:
            return 0
        return len(self.tokenizer.encode(text))

    def _iter_files(self, folder_path: Path) -> Iterator[tuple[Path, str | None]]:
        """Iterate over all files in folder, including inside zips.

        Yields:
            Tuple of (file_path, source_archive_path or None)
        """
        for root, _, files in os.walk(folder_path):
            for filename in files:
                file_path = Path(root) / filename

                if file_path.suffix.lower() == ".zip":
                    # Extract and process zip contents
                    yield from self._iter_zip_files(file_path)
                else:
                    yield file_path, None

    def _iter_zip_files(
        self, zip_path: Path
    ) -> Iterator[tuple[Path, str]]:
        """Extract and iterate over files in a zip archive.

        Encrypted/password-protected members are skipped; only readable files
        are yielded. Corrupt or unreadable zips are skipped entirely.

        Yields:
            Tuple of (extracted_file_path, original_zip_path)
        """
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Extract members one-by-one so we can skip only encrypted entries
                    for member in zf.namelist():
                        if member.endswith("/") or ".." in member:
                            continue
                        try:
                            zf.extract(member, temp_dir)
                        except RuntimeError as e:
                            # Skip only password-protected/encrypted members
                            msg = str(e).lower()
                            if "password" in msg or "encrypted" in msg:
                                continue
                            raise

                    # Walk extracted contents
                    for root, _, files in os.walk(temp_dir):
                        for filename in files:
                            file_path = Path(root) / filename
                            if not file_path.is_file():
                                continue
                            if file_path.suffix.lower() == ".zip":
                                yield from self._iter_zip_files(file_path)
                            else:
                                yield file_path, str(zip_path)
        except zipfile.BadZipFile:
            # Skip corrupted zip files
            pass

    def process_file(self, file_path: Path, source_archive: str | None = None) -> FileResult:
        """Process a single file and return token count.

        Args:
            file_path: Path to the file
            source_archive: Path to source zip if extracted from archive

        Returns:
            FileResult with token count and metadata
        """
        result: ProcessingResult = self.processor.process(file_path)

        if not result.success:
            return FileResult(
                path=str(file_path),
                tokens=0,
                chars=0,
                file_type=result.file_type,
                success=False,
                error=result.error,
                source_archive=source_archive,
            )

        tokens = self.count_tokens(result.text)

        return FileResult(
            path=str(file_path),
            tokens=tokens,
            chars=len(result.text),
            file_type=result.file_type,
            success=True,
            source_archive=source_archive,
        )

    def process_folder(
        self,
        folder_path: str | Path,
        progress_callback: callable = None,
    ) -> FolderResult:
        """Process all files in a folder.

        Args:
            folder_path: Path to the folder to process
            progress_callback: Optional callback for progress updates

        Returns:
            FolderResult with aggregated statistics
        """
        folder_path = Path(folder_path)

        if not folder_path.exists():
            raise ValueError(f"Folder not found: {folder_path}")

        if not folder_path.is_dir():
            raise ValueError(f"Not a directory: {folder_path}")

        result = FolderResult(
            folder_path=str(folder_path),
            model_name=self.model_name,
        )

        # Collect all files first for progress bar
        files_to_process = list(self._iter_files(folder_path))

        # Process files
        iterator = tqdm(files_to_process, desc="Processing files") if not progress_callback else files_to_process

        for file_path, source_archive in iterator:
            file_result = self.process_file(file_path, source_archive)
            result.add_result(file_result)

            if progress_callback:
                progress_callback(result.total_files, len(files_to_process), file_result)

        return result
