from typing import Literal, cast

import tempfile
import asyncio
from contextlib import asynccontextmanager
import shutil
from pathlib import Path
import os
import time

from fastapi import FastAPI, UploadFile, BackgroundTasks, HTTPException, Response
from fastapi.responses import FileResponse

testing = bool(os.getenv("TESTING", False))

SUBPROCESS_TIMEOUT = 60 # seconds
MAX_QUEUE_WAIT_TIME = 30 # max time to wait in queue before bailing, prevents case where queue gets so long that no requests finish before browser timeout
MAX_INPUT_SIZE = 10000000 # bytes
MAX_CONCURRENT_PANDOC_RUNS = 2
MD_FILE_NAME = "input.md"
OUTPUT_FILE_NAME_BASE = "output"
MIME_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "tex": "application/x-tex"
}

class DocConversionTask:
    def __init__(self, doc_type: Literal['docx', 'pdf', 'tex'], paper_size: Literal['letter', 'a4'], temp_dir_name: str, env: dict[str, str] | None):
        self.doc_type = doc_type
        self.paper_size: Literal['letter', 'a4'] = paper_size
        self.temp_dir_name = temp_dir_name
        self.env = env
        self.future = asyncio.get_running_loop().create_future()
        self.wait_start_time = time.monotonic()

    async def convert(self):
        output_file_name = f"{OUTPUT_FILE_NAME_BASE}.{self.doc_type}"

        match self.doc_type:
            case "pdf":
                paper_size_variable = "us-letter" if self.paper_size == "letter" else "a4"
                cmd = f"pandoc --from markdown --to pdf --standalone --embed-resources --no-highlight \
                        --pdf-engine=typst {MD_FILE_NAME} \
                        -V papersize={paper_size_variable} \
                        -o {output_file_name}"
            case "tex":
                cmd = f"pandoc --from markdown --to latex --standalone --embed-resources --no-highlight \
                       -V papersize={self.paper_size} \
                       {MD_FILE_NAME} -o {output_file_name}"
            case "docx":
                if self.paper_size == "letter":
                    reference_doc = "/code/app/reference_docs/reference_letter.docx"
                else:
                    reference_doc = "/code/app/reference_docs/reference_a4.docx"

                cmd = f"pandoc --from markdown --to {self.doc_type} --standalone --embed-resources --no-highlight \
                        --reference-doc={reference_doc} \
                        {MD_FILE_NAME} -o {output_file_name}"
            case _:
                raise HTTPException(status_code=405, detail="Unsupported document type")
            
        try:
            if (time.monotonic() - self.wait_start_time) > MAX_QUEUE_WAIT_TIME:
                raise HTTPException(status_code=503, detail="The document conversion service is currently operating at capacity, please retry later")

            proc = await asyncio.create_subprocess_shell(
                cmd=cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.temp_dir_name,
                env=self.env)

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), SUBPROCESS_TIMEOUT)
            except (TimeoutError, asyncio.exceptions.TimeoutError): # Python 3.11 uses TimeoutError instead of asyncio.exceptions.TimeoutError
                try:
                    proc.kill()
                except OSError:
                    pass
                
                if self.doc_type == "pdf":
                    raise HTTPException(status_code=504, detail="Document creation timeout, trying again may work or consider generating a .docx file instead of a .pdf file or reducing the number of images or plots")
                else:
                    raise HTTPException(status_code=504, detail="Document Creation Timeout")

            if proc.returncode != 0:
                if self.doc_type == "pdf":
                    raise HTTPException(status_code=500, detail="Error generating PDF file. Image links are know to cause errors when generating .pdf documents. Replace image links with images inserted as files. If errors persist, consider exporting as a .docx file instead.<br><br>" 
                                                                + "Pandoc process error: " + stderr.decode())
                else:    
                    raise HTTPException(status_code=500, detail=stderr.decode())
            
            # make sure output file exists
            if not os.path.isfile(Path(self.temp_dir_name) / output_file_name):
                raise HTTPException(status_code=500, detail="Pandoc executed successfully but output file does not exist. Report issue to support@engineeringpaper.xyz")
        
        except Exception as e:
            self.future.set_exception(e)
        else:
            self.future.set_result(output_file_name)

async def worker(queue: asyncio.Queue[DocConversionTask]):
    while True:
        doc_conversion_task = await queue.get()
        await doc_conversion_task.convert()
        queue.task_done()

# global task queue
queue: asyncio.Queue[DocConversionTask] = asyncio.Queue()


tasks = []

# setup and cleanup task queue on startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # define task pool
    for i in range(MAX_CONCURRENT_PANDOC_RUNS):
        tasks.append(asyncio.create_task(worker(queue)))

    print(f'Task pool created with {len(tasks)} tasks')

    yield
    
    # wait for pending tasks to finish
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)

testing_env = os.environ.copy()
testing_env["SOURCE_DATE_EPOCH"] = "1704329963"

async def delete_temp_directory(temp_dir_name):
    await asyncio.to_thread(shutil.rmtree, temp_dir_name, ignore_errors=True)


@app.post("/docgen/{raw_doc_type}")
async def convert_markdown_file(request_file: UploadFile, raw_doc_type: Literal['docx', 'docx_a4', 'pdf', 'pdf_a4', 'tex', 'tex_a4'],
                                background_tasks: BackgroundTasks):
    if raw_doc_type.endswith('_a4'):
        paper_size = 'a4'
    else:
        paper_size = 'letter'
    
    doc_type = cast(Literal['docx', 'pdf', 'tex'], raw_doc_type.removesuffix('_a4'))

    temp_dir_name = None

    try:
        # make sure file is not too large
        if request_file.size and (request_file.size > MAX_INPUT_SIZE):
            raise HTTPException(status_code=413, detail="Sheet too large for document conversion, reduce size of images in documentation cells.")

        # verify file (protects against uploading a binary file, which will cause pandoc to hang)
        first_line = await request_file.read(43)
        try:
            first_line = first_line.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(status_code=415, detail="Unsupported file type")

        if first_line != "<!-- Created with EngineeringPaper.xyz -->\n":
            raise HTTPException(status_code=415, detail="Unsupported file type")

        await request_file.seek(0)

        temp_dir_name = tempfile.mkdtemp()
        background_tasks.add_task(delete_temp_directory, temp_dir_name)

        env = testing_env if testing else None

        with open(Path(temp_dir_name) / MD_FILE_NAME, 'wb') as md_input_file:
            await asyncio.to_thread(shutil.copyfileobj, request_file.file, md_input_file)
            md_input_file.write(("Created with [EngineeringPaper.xyz](https://engineeringpaper.xyz)\n\n").encode('utf-8'))
        
        # add to task queue
        doc_conversion_task = DocConversionTask(doc_type, paper_size, temp_dir_name, env)
        await queue.put(doc_conversion_task) # finishes when task is inserted into queue
        output_file_name = await doc_conversion_task.future # finishes when doc conversion is completed or raises

    except Exception as e:
        # need to delete temp directory since background tasks are not called for failed requests
        if temp_dir_name is not None:
            await delete_temp_directory(temp_dir_name)
        raise e

    return FileResponse(Path(temp_dir_name) / output_file_name,
                        media_type=MIME_TYPES[doc_type],
                        filename = f"output.{doc_type}")


@app.get("/healthz")
async def health_check():
    if all([not task.done() for task in tasks]):
        return Response(status_code=200, content="All tasks are currently running")
    else:
        return Response(status_code=503, content="Some tasks are no longer active")
