from flask import Blueprint, request, jsonify, current_app
from . import db
from .models import Picture, Tag
import requests, base64, uuid
from datetime import datetime
from imagekitio import ImageKit
import os

main_blueprint = Blueprint('main', __name__)

@main_blueprint.route('/image', methods=['POST'])
def post_image():
    try:
        data = request.json.get('data')
        min_confidence = request.args.get('min_confidence', 80, type=float)
        img_data = base64.b64decode(data)
        img_id = str(uuid.uuid4())
        date_now = datetime.now()

        imagekit = ImageKit(
            public_key=current_app.config['IMAGEKIT_PUBLIC_KEY'],
            private_key=current_app.config['IMAGEKIT_PRIVATE_KEY'],
            url_endpoint=current_app.config['IMAGEKIT_URL_ENDPOINT']
        )

        upload_info = imagekit.upload(file=img_data, file_name=f"{img_id}.jpg")
        image_url = upload_info['url']

        response = requests.get(
            f"https://api.imagga.com/v2/tags?image_url={image_url}",
            auth=(current_app.config['IMAGGA_API_KEY'], current_app.config['IMAGGA_API_SECRET'])
        )

        tags_response = response.json().get("result", {}).get("tags", [])
        tags = [
            {
                "tag": t.get("tag", {}).get("en", ""),
                "confidence": t.get("confidence", 0)
            }
            for t in tags_response
            if t.get("confidence", 0) > min_confidence
        ]

        nombre_archivo = f"{img_id}.png" #Lo voy a guardar con un nombre que sea el id asignado antes
        path = r"C:\Users\Danie\Master-VSC-Carpetas\ENTREGA\Fotos" #Carpeta donde lo voy a guardar (cambiar en caso de estar en otro pc)
        ruta_archivo = os.path.join(path, nombre_archivo) #Concateno path y el nombre.
        with open(ruta_archivo, "wb") as archivo:
        archivo.write(img_data) #Almaceno

        new_picture = Picture(id=img_id, path=path, date=date_now)
        db.session.add(new_picture)

        for tag in tags:
            new_tag = Tag(tag=tag["tag"], picture_id=img_id, confidence=tag["confidence"], date=date_now)
            db.session.add(new_tag)

        db.session.commit()

        return jsonify({
            "id": img_id,
            "size": len(img_data) / 1024,
            "date": date_now,
            "tags": tags,
            "data": data
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@main_blueprint.route('/images', methods=['GET'])
def get_images():
    min_date = request.args.get('min_date')
    max_date = request.args.get('max_date')
    tags = request.args.get('tags')

    query = "SELECT * FROM pictures"
    conditions = []
    params = {}

    if min_date:
        conditions.append("date >= :min_date")
        params["min_date"] = min_date
    if max_date:
        conditions.append("date <= :max_date")
        params["max_date"] = max_date
    if tags:
        tag_list = tags.split(',')
        conditions.append("id IN (SELECT picture_id FROM tags WHERE tag IN :tags)")
        params["tags"] = tuple(tag_list)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    with db.engine.connect() as connection:
        result = connection.execute(text(query), params)
        images = [dict(row) for row in result]

    for image in images:
        image["tags"] = get_tags_for_image(image["id"])

    return jsonify(images)

@main_blueprint.route('/image/<id>', methods=['GET'])
def get_image(id):
    with db.engine.connect() as connection:
        result = connection.execute(text("SELECT * FROM pictures WHERE id = :id"), {"id": id})
        image = result.fetchone()

    if not image:
        return jsonify({"error": "Image not found"}), 404

    image = dict(image)
    image["tags"] = get_tags_for_image(id)
    with open(image["path"], "rb") as f:
        image["data"] = base64.b64encode(f.read()).decode('utf-8')
    image["size"] = os.path.getsize(image["path"]) / 1024

    return jsonify(image)

def get_tags_for_image(image_id):
    with db.engine.connect() as connection:
        result = connection.execute(text("SELECT tag, confidence FROM tags WHERE picture_id = :image_id"), {"image_id": image_id})
        tags = [dict(row) for row in result]
    return tags
