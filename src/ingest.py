import os
import asyncio
from docling.chunking import HybridChunker
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, PictureDescriptionApiOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer
from loguru import logger
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from embed import embed_chunks
from config import LITELLM_API_KEY, LITELLM_BASE_URL

CHUNKER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

class FileObserver(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.converter = build_converter()
        self.chunker = build_chunker()

    def on_created(self, event):
        if event.is_directory:
            return

        print(f" New file detected: {event.src_path}")
        asyncio.run(self._handle(event.src_path))

    async def _handle(self, path):
        try:
            print(f"Processing content of {os.path.basename(path)}...")
            result = self.converter.convert(path)
            logger.info("chunking...")
            texts = [self.chunker.contextualize(chunk) for chunk in self.chunker.chunk(result.document)]
            await embed_chunks(texts, path)
            print(result.document.export_to_markdown())
            print(f"✅ Successfully processed {os.path.basename(path)}")
        except Exception as e:
            print(f"Error processing file: {e}")


def start_file_observer(watch_directory):
    print("file-observer running...")
    # Ensure the directory exists
    os.makedirs(watch_directory, exist_ok=True)

    event_handler = FileObserver()
    observer = Observer()
    observer.schedule(event_handler, path=watch_directory, recursive=False)

    print(f"🚀 Starting file observer on {watch_directory}...")
    observer.start()
    return observer

def build_converter():
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_picture_description = True
    pipeline_options.generate_picture_images = True
    # Required to use LiteLLM running remotely in docker container
    pipeline_options.enable_remote_services=True
    pipeline_options.picture_description_options = PictureDescriptionApiOptions(
        url=f"{LITELLM_BASE_URL}/chat/completions",
        params={"model": "qwen2.5vl"},
        headers={"Authorization": f"Bearer {LITELLM_API_KEY}"},
        prompt="Describe this image in 1-2 sentences, focusing on any data, diagrams, or text it contains.",
        timeout=90,
    )

    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )


def build_chunker():
    # Passing max_tokens directly to HybridChunker still calls
    # get_default_tokenizer() internally to fetch sentence_bert_config.json
    # from the HF Hub, even when overridden. Building the tokenizer ourselves
    # with max_tokens set avoids that Hub call so this works with
    # HF_HUB_OFFLINE=1.
    hf_tokenizer = HuggingFaceTokenizer(
        tokenizer=AutoTokenizer.from_pretrained(CHUNKER_MODEL),
        max_tokens=512,
    )
    return HybridChunker(tokenizer=hf_tokenizer)
