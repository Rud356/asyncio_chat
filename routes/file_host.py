import imghdr
import os
from pathlib import Path
from random import choices
from string import ascii_letters
from time import time

from bson import ObjectId
from bson import errors as bson_errors
from quart import request, send_file
from werkzeug.utils import secure_filename

from app import app
from models.file_model import FileModel
from views import User

from .middlewares import authorized
from .responces import error, success

allowed_formats = {'gif', 'jpeg', 'png', 'webp'}
profile_pics_folder = Path(app.config['UPLOAD_FOLDER']) / 'profile_pics'
files_path = Path(app.config['UPLOAD_FOLDER'])


@app.route("/api/user/set_image", methods=["POST"])
@authorized
async def upload_profile_pic(user: User):
    if (
        request.content_length is None or
        request.content_length > 4 * 1024 * 1024
    ):
        return error("Too big file", 400)

    files = await request.files
    profile_img = files['image']

    if profile_img.filename == '':
        return error("None image selected", 400)

    if imghdr.what(profile_img) not in allowed_formats:
        return error("Incorrect file format", 400)

    profile_img.save(profile_pics_folder / user._id)
    return success("Profile image updated!")


@app.route("/api/user/<string:user_id>/profile_pic")
@authorized
async def get_profile_pic(user: User, user_id: str):
    try:
        user_id = ObjectId(ObjectId)
        user_id = str(user)
        if not os.path.isfile(profile_pics_folder / user_id):
            return error("No such pfp")

        filename = user_id + imghdr.what(profile_pics_folder / user_id)

        response = await send_file(profile_pics_folder / user_id)
        response.headers['x-filename'] = filename

        return response

    except bson_errors.InvalidId:
        return error("Invalid user id")


@app.route("/api/files/upload", methods=["POST"])
@authorized
async def upload_file(user: User):
    files = await request.files
    files_ids = []

    for file_name in files:
        file = files[file_name]
        if file.filename == '':
            continue

        rand_part = ''.join(choices(ascii_letters, k=12))

        system_file_name = f"{time()}_{user._id}_{rand_part}"
        with open(files_path / system_file_name, 'wb') as f:
            file.save(f)

            await FileModel.create_file(
                secure_filename(file.filename),
                system_file_name
            )

        files_ids.append(system_file_name)

    return success(files_ids)


@app.route("/api/files/<string:file_name>")
@authorized
async def get_file(user: User, file_name: str):
    try:
        file_name = files_path / file_name

        with open(file_name, 'rb') as f:
            response = await send_file(f)

        file_record = FileModel.get_file(file_name)
        response.headers['x-filename'] = file_record.file_name

        return response

    except bson_errors.InvalidId:
        return error("Invalid id")
