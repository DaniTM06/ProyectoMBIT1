import os
import base64
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from imagekitio import ImageKit
import requests
from sqlalchemy import create_engine, text

app = Flask(__name__)

# Configuración de ImageKit y Imagga
imagekit = ImageKit(
    public_key='public_Gvw/Zmhspbpr8lSOnMJ/3K3Zl0g=',
    private_key='private_LWC481k8Mj4PA/QKlu9aT2AwC10=',
    url_endpoint='https://ik.imagekit.io/DaniTM/'
)
api_key = 'acc_48f5530976934bb'
api_secret = '88eb94597b80acd92d375a1e6b095769'

# Configuración de la base de datos
db_url = "mysql+pymysql://mbit:mbit@db:3306/pictures"
engine = create_engine(db_url)

@app.route('/image', methods=['POST'])
#Aqui defino una función post_image que se encargue de recibir la imagen en base 64 (data) y la confidence cuando realizamos el request.
def post_image():
    data = request.json.get('data')
    min_confidence = request.args.get('min_confidence', 80, type=float)
    img_data = base64.b64decode(data)
    #Genero id unico y guardo la fecha
    img_id = str(uuid.uuid4()) 
    date_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Subir imagen a ImageKit
    upload_info = imagekit.upload(file=img_data, file_name=f"{img_id}.jpg")
    image_url = upload_info['url']

    # Obtengo los tags de Imagga
    response = requests.get(f"https://api.imagga.com/v2/tags?image_url={image_url}", auth=(api_key, api_secret))
    tags = [
        {
            "tag": t["tag"]["en"],
            "confidence": t["confidence"]
        }
        for t in response.json()["result"]["tags"]
        if t["confidence"] > min_confidence
    ]

    # Ya que tenemos todo lo que necesitamos guardo las variables en mi tabla.

    #Primero me guardo la foto en una carpeta. Esto lo hace a fuerza bruta, no es lo mas optimo.
    nombre_archivo = f"{img_id}.png" #Lo voy a guardar con un nombre que sea el id asignado antes
    path = r"C:\Users\Danie\Master-VSC-Carpetas\ENTREGA\Fotos" #Carpeta donde lo voy a guardar (cambiar en caso de estar en otro pc)
    ruta_archivo = os.path.join(path, nombre_archivo) #Concateno path y el nombre.
    with open(ruta_archivo, "wb") as archivo:
        archivo.write(img_data) #Almaceno

    # Insertamos en la base de datos

    with engine.connect() as connection:
        connection.execute(
            text("INSERT INTO pictures (id, path, date) VALUES (:id, :path, :date)"),
            {"id": img_id, "path": path, "date": date_now}
        )
        for tag in tags:
            connection.execute(
                text("INSERT INTO tags (tag, picture_id, confidence, date) VALUES (:tag, :picture_id, :confidence, :date)"),
                {"tag": tag["tag"], "picture_id": img_id, "confidence": tag["confidence"], "date": date_now}
            )
    #Que nos devuelva al final del todo los datos almacenados
    return jsonify({
        "id": img_id,
        "size": len(img_data) / 1024,
        "date": date_now,
        "tags": tags,
        "data": data
    })

@app.route('/images', methods=['GET'])
def get_images():
    #Esta función obtiene por la llamada de la API un rango de fechas asi como las tags concretas a mostrar
    min_date = request.args.get('min_date')
    max_date = request.args.get('max_date')
    tags = request.args.get('tags')

    #Los datos los obtenemos de la tabla pictures
    query = "SELECT * FROM pictures"
    conditions = []
    params = {}
    
    #Almacenamos las fechas asi como los tags, separados entre si
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

    #Teniendo todo, consultamos la tabla
    with engine.connect() as connection:
        result = connection.execute(text(query), params)
        images = [dict(row) for row in result]

    for image in images:
        image["tags"] = get_tags_for_image(image["id"])

    return jsonify(images)

@app.route('/image/<id>', methods=['GET'])
def get_image(id):
    #Obtiene un id unico por la llamada dela api y muestra lo relacionado a ese id
    with engine.connect() as connection:
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

def get_tags_for_image(image_id): #Para obtener los tags de un id concreto
    with engine.connect() as connection:
        result = connection.execute(text("SELECT tag, confidence FROM tags WHERE picture_id = :image_id"), {"image_id": image_id})
        tags = [dict(row) for row in result]
    return tags
    
if __name__ == '__main__':
    app.run(debug=True)
