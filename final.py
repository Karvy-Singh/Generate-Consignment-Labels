from pdf2image import convert_from_path
import shutil
import cv2
from flask import Flask, jsonify, request, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from flask_cors import CORS
import csv
import os
from pyzbar.pyzbar import decode
from reportlab.graphics.barcode import code128
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.pdfgen import canvas

app = Flask(__name__, template_folder='templates')
CORS(app)

# Create folders if not exist
SAVED_DATA_FOLDER = os.path.join(os.getcwd(), 'saved_data')
UPLOAD_FOLDER_1 = os.path.join(os.getcwd(), 'excel')
UPLOAD_FOLDER_2 = os.path.join(os.getcwd(), 'barcode')

for folder in [UPLOAD_FOLDER_1, UPLOAD_FOLDER_2, SAVED_DATA_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

@app.get('/upload')
def upload_page():
    # Renders a simple HTML file: templates/template.html
    return render_template("template.html")

@app.route('/upload', methods=['POST'])
def upload_files():
    file = request.files['file']
    cat = request.form.get('dataType')
    uploaded_files = {"excel": None, "barcode": None}

    # Debug prints
    print("Received file:", file)
    print("Category (dataType):", cat)

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

    # If both folders have files, process the combination
    if len(os.listdir(UPLOAD_FOLDER_1)) > 0 and len(os.listdir(UPLOAD_FOLDER_2)) > 0:
        for excel_file in os.listdir(UPLOAD_FOLDER_1):
            for pdf_file in os.listdir(UPLOAD_FOLDER_2):
                print("Processing combination of:", excel_file, "and", pdf_file, "...")
                
                # Convert PDF to images
                images = convert_from_path(os.path.join(UPLOAD_FOLDER_2, pdf_file))
                
                # For each page in the PDF
                for i in range(len(images)):
                    images[i].save('qr.png', 'PNG')  # temporary in local folder

                    # Decode the barcode from 'qr.png'
                    image = cv2.imread("qr.png")
                    decoded_objects = decode(image)
                    for obj in decoded_objects:
                        qr_data = obj.data.decode("utf-8")
                        typeqr = obj.type
                        print("Decoded QR data:", qr_data, "| type:", typeqr)

                        # Create the new PDF with combined data
                        c = canvas.Canvas(os.path.join(SAVED_DATA_FOLDER, "barcode.pdf"))
                        c.setFont("Helvetica", 14)

                        # Read CSV data
                        with open(os.path.join(UPLOAD_FOLDER_1, excel_file), 'r', encoding='utf-8') as f:
                            reader = csv.reader(f)
                            data = list(reader)  # list of lists

                        # Convert CSV into a dict-like structure
                        json_data = {}
                        for row_index, row in enumerate(data):
                            row_dict = {}
                            for col_index, col_value in enumerate(row):
                                row_dict[f"Unnamed: {col_index}"] = col_value
                            json_data[row_index] = row_dict

                        # Example: combining 3 data fields into a single string (adjust as needed)
                        # Make sure your CSV has at least 4 rows with enough columns or handle errors
                        try:
                            s = json_data[3]["Unnamed: 1"] + " " + \
                                json_data[2]["Unnamed: 1"] + " " + \
                                json_data[1]["Unnamed: 1"]
                        except KeyError:
                            s = "Data not found"

                        # Create a table of the CSV and style it
                        from reportlab.platypus import Table, TableStyle
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

                        # Add the barcode
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
                        print("Barcode PDF saved in", SAVED_DATA_FOLDER)

    shutil.rmtree(UPLOAD_FOLDER_1)
    shutil.rmtree(UPLOAD_FOLDER_2)
    return render_template('template.html')


# For Replit, run on host='0.0.0.0' and port=3000
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 3000))
    app.run(host='0.0.0.0', port=port, debug=True)

