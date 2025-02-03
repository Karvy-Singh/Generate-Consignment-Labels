from pdf2image import convert_from_path
import cv2
from flask import Flask, jsonify, request, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from flask_cors import CORS
import csv
import os
import ctypes
from pyzbar.pyzbar import decode
from reportlab.graphics.barcode import code128
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.pdfgen import canvas

# Rename your Flask instance to 'app'
app = Flask(__name__)
CORS(app)

if platform.system() == "Linux":
    zbar_path = os.path.join(os.getcwd(), 'libs', 'libzbar.so.0.3.0')
    ctypes.cdll.LoadLibrary(zbar_path)

elif platform.system() == "Windows":
    zbar_path = os.path.join(os.getcwd(), 'libs', 'zbar.dll')
    ctypes.cdll.LoadLibrary(zbar_path)

SAVED_DATA_FOLDER = os.path.join(os.getcwd(), 'saved_data')
UPLOAD_FOLDER_1 = os.path.join(os.getcwd(), 'excel')
UPLOAD_FOLDER_2 = os.path.join(os.getcwd(), 'barcode')

for folder in [UPLOAD_FOLDER_1, UPLOAD_FOLDER_2, SAVED_DATA_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)


@app.get('/upload')
def upload_page():
    return render_template("template.html")


@app.route('/upload', methods=['POST'])
def upload_files():
    file = request.files['file']
    cat = request.form.get('dataType')
    uploaded_files = {"excel": None, "barcode": None}
    print(cat)
    print(file)

    if cat == "barcode":
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER_2, filename)
        uploaded_files["barcode"] = file_path
        file.save(file_path)
    elif cat == "excel":
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER_1, filename)
        uploaded_files["excel"] = file_path
        file.save(file_path)

    if len(os.listdir(UPLOAD_FOLDER_1)) > 0 and len(os.listdir(UPLOAD_FOLDER_2)) > 0:
        for excel_file in os.listdir(UPLOAD_FOLDER_1):
            for pdf_file in os.listdir(UPLOAD_FOLDER_2):
                print("Processing combination of files...")
                images = convert_from_path(os.path.join(UPLOAD_FOLDER_2, pdf_file))
                for i in range(len(images)):
                    images[i].save('qr.png', 'PNG')  # temporary in local folder

                # Decode the barcode from 'qr.png'
                image = cv2.imread("qr.png")
                decoded_objects = decode(image)
                for obj in decoded_objects:
                    qr_data = obj.data.decode("utf-8")
                    typeqr = obj.type
                    print("Decoded QR data:", qr_data, "type:", typeqr)

                    c = canvas.Canvas(os.path.join(SAVED_DATA_FOLDER, "barcode.pdf"))
                    c.setFont("Helvetica", 14)

                    with open(os.path.join(UPLOAD_FOLDER_1,l), 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        data = list(reader)  # list of lists

                    json = {}
                    for i, row in enumerate(data):
                        row_dict = {}
                        for j, col_value in enumerate(row):
                            row_dict[f"Unnamed: {j}"] = col_value
                        json[i] = row_dict
                    print(json)
                    s=json[3]["Unnamed: 1"]+" "+json[2]["Unnamed: 1"]+" "+json[1]["Unnamed: 1"]

                    # Create a table and style it
                    table = Table(data)
                    style = TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
                    ])
                    table.setStyle(style)

                    table.wrapOn(c, 500, 400)
                    table.drawOn(c, x=50, y=600)
                    table.wrapOn(c, 500, 400)
                    table.drawOn(c, x=50, y=150)

                    barcode_obj = code128.Code128(qr_data, barHeight=25, barWidth=1)
                    # Top portion
                    barcode_obj.drawOn(c, x=150, y=550)
                    c.drawString(200, 530, qr_data)
                    c.drawString(200, 510, s)

                    # Bottom portion
                    barcode_obj.drawOn(c, x=150, y=110)
                    c.drawString(200, 90, qr_data)
                    c.drawString(200, 70, s)

                    c.save()
                    print("Barcode PDF saved")

    return render_template('template.html')


# The default Flask start
if __name__ == '__main__':
    # Important: Vercel by default sets PORT=3000
    port = int(os.environ.get("PORT", 3000))
    app.run(host='0.0.0.0', port=port, debug=True)

