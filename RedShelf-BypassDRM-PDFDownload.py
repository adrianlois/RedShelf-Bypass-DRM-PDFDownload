import requests
import json
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import utils
from reportlab.platypus import SimpleDocTemplate, Image

# Load session cookies from a JSON file
def load_cookies_from_json(file_name):
    try:
        with open(file_name, 'r') as file:
            cookies = json.load(file)
        return cookies
    except FileNotFoundError:
        print(f"The file {file_name} was not found.")
        return None

# Directory in which you want to save the images
target_directory_img = "TARGET_DIRECTORY_IMG"
# Base URL
base_url = "https://platform.virdocs.com/rscontent/epub/XXXXXXX/XXXXXXX/OEBPS/images/page-{}.jpg"
# Total number of URL pages
numpag = 350
# PDF file name
pdf_file = "EXPORT_PDF_FILE.pdf"

# Create the directory if it does not exist
if not os.path.exists(target_directory_img):
    os.makedirs(target_directory_img)

# Load session cookies from a JSON file
cookies = load_cookies_from_json("cookies.json")

if cookies is not None:
    # Create an A4 formatted PDF document in portrait orientation
    doc = SimpleDocTemplate(pdf_file, pagesize=A4, rightMargin=0, leftMargin=0, topMargin=0, bottomMargin=0)

    images = []

    for numpag in range(1, numpag + 1):
        url = base_url.format(numpag)
        file_name = os.path.join(target_directory_img, f"{numpag}.jpg")

        # HTTP request with session cookies
        response = requests.get(url, cookies=cookies)

        if response.status_code == 200:
            with open(file_name, 'wb') as imagen:
                imagen.write(response.content)
            print(f"Image {file_name} successfully downloaded.")

            # Add image to PDF document
            img = utils.ImageReader(file_name)
            img_width, img_height = img.getSize()
            aspect_ratio = img_height / float(img_width)
            images.append((numpag, Image(file_name, width=A4[0], height=(A4[0] * aspect_ratio))))
        else:
            print(f"Could not download the {file_name}. Status code: {response.status_code}")

    # Sort images by page number
    print(f"Sort images by page number...")
    images = sorted(images, key=lambda x: x[0])

    # Generate the PDF with the images in page order
    doc.build([img for _, img in images])
    print(f"PDF created: {pdf_file}")
else:
    print("Could not load session cookies.")