import os
import shutil
import uuid
from pathlib import Path

from flask import Blueprint, current_app
from extensions import db
from models import File

upload_bp = Blueprint("uploads", __name__)


def get_upload_folder() -> Path:
    return Path(current_app.config["UPLOAD_FOLDER"])

def upload_file(file, bucket):
    UPLOAD_DIR = "static/uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file)[1]
    file_id = str(uuid.uuid4())
    local_filename = f"{file_id}{ext}"
    save_path = os.path.join(UPLOAD_DIR, local_filename)
    basename = os.path.basename(file)
    shutil.move(file, save_path)
    filename_in_s3 = f"events/{file_id}"
    # Определение реального размера файла
    size = os.path.getsize(save_path)

    # s3.upload_fileobj(
    #     Fileobj=file.stream,
    #     Bucket=bucket,
    #     Key=filename_in_s3,
    #     ExtraArgs={"ContentType": file.mimetype}
    # )

    # Сохраняем в таблицу File
    new_file = File(
        id=file_id,
        bucket=bucket,
        filename=filename_in_s3,
        originalname=basename,
        size=size
    )
    db.session.add(new_file)
    db.session.commit()

    return file_id


def delete_file(bucket, old_file_id):
    # Удаляем старый файл
    old_file = db.session.get(File, old_file_id)
    if old_file:
        try:
            # Логика удаления из С3
            pass
            # s3.delete_object(Bucket=old_file.bucket, Key=old_file.filename)
        except Exception as e:
            print(f"Ошибка удаления файла из S3: {e}")
        db.session.delete(old_file)
    db.session.commit()
    return


def get_extension(filename):
    if filename and '.' in filename:
        return filename.rsplit('.', 1)[1]
    return ''
