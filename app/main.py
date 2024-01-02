from typing import Literal, cast, BinaryIO, Annotated

import tempfile
import asyncio
import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse

MD_FILE_NAME = "input.md"
OUTPUT_FILE_NAME_BASE = "output"

app = FastAPI()

async def delete_temp_directory(temp_dir_name):
    await asyncio.to_thread(shutil.rmtree, temp_dir_name)
    print(f"Deleted dir: {temp_dir_name}")

@app.post("/docgen/{doc_type}")
async def convert_markdown_file(request_file: UploadFile, doc_type: Literal['docx', 'pdf'],
                                background_tasks: BackgroundTasks):
    temp_dir_name = tempfile.mkdtemp()
    print(f"Created dir: {temp_dir_name}")

    background_tasks.add_task(delete_temp_directory, temp_dir_name)

    output_file_name = f"{OUTPUT_FILE_NAME_BASE}.{doc_type}"

    with open(Path(temp_dir_name) / MD_FILE_NAME, 'wb') as md_input_file:
        await asyncio.to_thread(shutil.copyfileobj, request_file.file, md_input_file)
        
        cmd = f"pandoc --from markdown --to {doc_type} --standalone --embed-resources --no-highlight {MD_FILE_NAME} -o {output_file_name}";
        proc = await asyncio.create_subprocess_shell(
            cmd=cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=temp_dir_name)

        stdout, stderr = await proc.communicate()

        print(f'[{cmd!r} exited with {proc.returncode}]')
        if stdout:
            print(f'[stdout]\n{stdout.decode()}')
        if stderr:
            print(f'[stderr]\n{stderr.decode()}')

    return FileResponse(Path(temp_dir_name) / output_file_name)