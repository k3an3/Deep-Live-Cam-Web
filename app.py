import argparse
import asyncio
import os.path
from uuid import uuid4

import aiofiles.os
import aiofiles.tempfile
from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles

app = FastAPI()
app.mount("/output", StaticFiles(directory="output"), name="output")

tasks = {}

parser = argparse.ArgumentParser()
parser.add_argument(
    "--python-path", default="python3", help="Path to python interpreter"
)
parser.add_argument(
    "--run-py-path", default="run.py", help="Path to the python script to be run"
)
parser.add_argument(
    "--num-threads", type=int, default=60, help="Number of execution threads"
)
parser.add_argument("--provider", default="cuda", help="Execution provider")
args = parser.parse_args()

PYTHON = args.python_path
RUN_PY = args.run_py_path
EXECUTION_THREADS = args.num_threads
EXECUTION_PROVIDER = args.provider


async def do_face_replacement(
        task_id: str, face_image_path: str, media_path: str, output_filename: str
):
    print(
        f"Processing {face_image_path} on {media_path} and saving to {output_filename}"
    )
    process = await asyncio.create_subprocess_exec(
        PYTHON,
        RUN_PY,
        "--execution-threads",
        str(EXECUTION_THREADS),
        "--execution-provider",
        EXECUTION_PROVIDER,
        "--source",
        face_image_path,
        "--target",
        media_path,
        "--output",
        output_filename,
    )
    tasks[task_id]["status"] = "processing"
    await process.wait()
    tasks[task_id]["status"] = "done"
    await asyncio.gather(
        aiofiles.os.unlink(face_image_path), aiofiles.os.unlink(media_path)
    )
    print("Completed task", task_id)


@app.post("/process")
async def process_request(
        background_tasks: BackgroundTasks,
        face_image: UploadFile = File(...),
        media_file: UploadFile = File(...),
):
    # Generate a unique task ID and output filename
    task_id = str(uuid4())
    extension = os.path.splitext(media_file.filename)[1]
    face_extension = os.path.splitext(face_image.filename)[1]
    output_filename = f"output/{task_id}{extension}"  # Assume the output is a video file

    async with aiofiles.tempfile.NamedTemporaryFile("wb", suffix=face_extension, delete=False) as f:
        await f.write(await face_image.read())
        face_image_path = f.name

    async with aiofiles.tempfile.NamedTemporaryFile("wb", suffix=extension, delete=False) as f:
        await f.write(await media_file.read())
        media_path = f.name

    # Store task details
    tasks[task_id] = {"status": "processing", "output_file": output_filename}

    # Run the system command in the background
    background_tasks.add_task(
        do_face_replacement, task_id, face_image_path, media_path, output_filename
    )

    # Return the task ID immediately
    return {"task_id": task_id}


@app.get("/tasks/{task_id}")
def task_status(task_id: str):
    try:
        return tasks[task_id]
    except KeyError:
        return {"error": "Task not found"}


@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
