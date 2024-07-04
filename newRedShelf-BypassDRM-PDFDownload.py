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
target_directory_img = "."        
# Base URL with a placeholder for the page number
base_url = 'https://platform.virdocs.com/rscontent/epub/XXXXXXX/XXXXXXX/OEBPS/images/page-{}.jpg'

# Range of page numbers to process
start_page = 28
end_page = 35

# Total number of URL pages
numpag = end_page - start_page
# PDF file name
pdf_file = "EXPORT_PDF_FILE.pdf"

cookies = load_cookies_from_json("cookies.json")

doc = SimpleDocTemplate(pdf_file, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
images = []

# Loop through the range of page numbers
for page_number in range(start_page, end_page + 1):
    # Construct the URL by replacing the placeholder with the current page number
    url = base_url.format(page_number)

    try:

        # Send the initial GET request
        response = requests.get(url, cookies=cookies, allow_redirects=False)
        response.raise_for_status()  # Check if the request was successful

        # Extract the Location header
        location_url = response.headers.get('Location')
        if not location_url:
            print(f"No 'Location' header found for URL: {url}")
            continue
        else:
        # Send another GET request to the Location URL 
            image_response = requests.get(location_url, cookies=cookies)
            image_response.raise_for_status()  # Check if the request was successful

        # Save the response content as a .jpg file
            file_name = f"image_page_{page_number}.jpg"
            with open(file_name, 'wb') as file:
                file.write(image_response.content)

            print(f"Image saved as {file_name}\n")

        # Add image to PDF document
            img = utils.ImageReader(file_name)
            img_width, img_height = img.getSize()
            aspect_ratio = img_height / float(img_width)
            images.append((numpag, Image(file_name, width=A4[0], height=(A4[0] * aspect_ratio))))        

    except requests.RequestException as e:
        print(f"An error occurred with URL {url}: {e}")

# Generate the PDF with the images in page order
doc.build([img for _, img in images])
print(f"PDF created: {pdf_file}")
print("Processing completed.")