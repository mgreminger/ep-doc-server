from typing import Literal, BinaryIO, Annotated

import tempfile
import asyncio
import shutil
from pathlib import Path
from functools import lru_cache
import os

from fastapi import FastAPI, UploadFile, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse

from pydantic_settings import BaseSettings

MD_FILE_NAME = "input.md"
OUTPUT_FILE_NAME_BASE = "output"
MIME_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf"
}

class Settings(BaseSettings):
    testing: bool = True

app = FastAPI()

@lru_cache
def get_settings():
    return Settings()

testing_env = os.environ.copy()
testing_env["SOURCE_DATE_EPOCH"] = "1704329963"

async def delete_temp_directory(temp_dir_name):
    await asyncio.to_thread(shutil.rmtree, temp_dir_name)
    print(f"Deleted dir: {temp_dir_name}")

@app.post("/docgen/{doc_type}")
async def convert_markdown_file(request_file: UploadFile, doc_type: Literal['docx', 'pdf'],
                                background_tasks: BackgroundTasks,
                                settings: Annotated[Settings, Depends(get_settings)]):
    
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
    print(f"Created dir: {temp_dir_name}")
    background_tasks.add_task(delete_temp_directory, temp_dir_name)

    env = testing_env if settings.testing else None

    output_file_name = f"{OUTPUT_FILE_NAME_BASE}.{doc_type}"

    with open(Path(temp_dir_name) / MD_FILE_NAME, 'wb') as md_input_file:
        await asyncio.to_thread(shutil.copyfileobj, request_file.file, md_input_file)
        
        cmd = f"pandoc --from markdown --to {doc_type} --standalone --embed-resources --no-highlight {MD_FILE_NAME} -o {output_file_name}";
        proc = await asyncio.create_subprocess_shell(
            cmd=cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=temp_dir_name,
            env=env)

        stdout, stderr = await proc.communicate()

        print(f'[{cmd!r} exited with {proc.returncode}]')
        if stdout:
            print(f'[stdout]\n{stdout.decode()}')
        if stderr:
            print(f'[stderr]\n{stderr.decode()}')

    return FileResponse(Path(temp_dir_name) / output_file_name,
                        media_type=MIME_TYPES[doc_type],
                        filename = f"output.{doc_type}")