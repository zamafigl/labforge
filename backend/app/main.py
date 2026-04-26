import os
import uuid
import zipfile

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from backend.app.generator.ai_client import generate_cpp_solution

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(BASE_DIR, "..", "artifacts")
SUBJECTS_DIR = os.path.join(BASE_DIR, "subjects")

os.makedirs(ARTIFACTS_DIR, exist_ok=True)

app = FastAPI(title="LabForge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Student(BaseModel):
    name: str
    group: str


class GenerateRequest(BaseModel):
    subject: str
    lab: str
    variant: int
    student: Student


def load_variants(subject: str, lab: str) -> dict:
    path = os.path.join(SUBJECTS_DIR, subject, lab, "variants.yaml")

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="variants.yaml not found")

    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def get_variant_data(subject: str, lab: str, variant_id: int) -> dict:
    data = load_variants(subject, lab)

    for variant in data.get("variants", []):
        if variant.get("id") == variant_id:
            return variant

    raise HTTPException(status_code=404, detail="Variant not found")


def write_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        file.write(content)


def create_zip(source_dir: str, zip_path: str) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, _, files in os.walk(source_dir):
            for filename in files:
                full_path = os.path.join(root, filename)
                arcname = os.path.relpath(full_path, source_dir)
                zip_file.write(full_path, arcname)


@app.get("/")
def root():
    return {"status": "ok", "service": "LabForge API"}


@app.post("/generate-ai")
def generate_ai(req: GenerateRequest):
    variant_data = get_variant_data(req.subject, req.lab, req.variant)

    job_id = str(uuid.uuid4())
    job_dir = os.path.join(ARTIFACTS_DIR, job_id)

    try:
        ai_result = generate_cpp_solution(
            task=variant_data["task"],
            variant_id=req.variant,
            student=req.student.model_dump()
        )

        write_file(os.path.join(job_dir, "src", "main.cpp"), ai_result["main_cpp"])
        write_file(os.path.join(job_dir, "README.md"), ai_result["readme_md"])
        write_file(os.path.join(job_dir, "report", "report.typ"), ai_result["report_typ"])

        zip_path = os.path.join(ARTIFACTS_DIR, f"{job_id}.zip")
        create_zip(job_dir, zip_path)

        return {
            "status": "ok",
            "job_id": job_id,
            "download_url": f"/download/{job_id}"
        }

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.get("/download/{job_id}")
def download(job_id: str):
    zip_path = os.path.join(ARTIFACTS_DIR, f"{job_id}.zip")

    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="Archive not found")

    return FileResponse(zip_path, filename=f"labforge-{job_id}.zip")