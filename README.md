# RedShelf Virdocs - Bypass DRM protection PDF Download

In the web platform "**RedShelf Virdocs**" you are allowed to print in PDF your ePub/eReader documents, but sometimes the contributors or owners add DRM *(Digital Rights Management)* protection for do not allow the downloading and printing of these eBooks to avoid possible leaks or unauthorized third party distributions.

This is not a vulnerability or something not legitimate, simply an exploitation of how these eBooks published on this platform are being offered. Although the direct download or print functionality is not allowed for some eBooks by the contributor or owner, it is possible to "download" them in this alternative way.

This python script allows us to "bypass" DRM this protection and download ePub/eReader documents and export them to PDF format. First all pages are downloaded in jpg image format, resized to A4 size and finally a PDF document output is generated.

### Requirements
```python
pip install requests
pip install reportlab
```

### Get URL ePub/eReader images
Inside the RedShelf Virdocs ePub/eReader viewer. We inspect the web and look for the iframe corresponding to the current page, in the body we will see a div containing the internal URL inside an img src tag. There we can copy the absolute path and substitute it in the variable "url_base".

![redshelf-virdocs-url-img](screenshots/redshelf-virdocs-url-img.png)

### Variables
- Indicates the directory where the jpg images will be saved and the name of the exported PDF file.
- Replace XXXXXXX with the value of the URL.
- Replace the numpag variable with the number of jpg URL pages contained in the document.

```python
target_directory_img = "TARGET_DIRECTORY_IMG"
base_url = "https://platform.virdocs.com/rscontent/epub/XXXXXXX/XXXXXXX/OEBPS/images/page-{}.jpg"
pdf_file = "EXPORT_PDF_FILE.pdf"
numpag = 350
```

### Cookies
Replace session cookie settings. Use any browser addon for editing and exporting cookies.
```json
{
    "session_id": "value1",
    "csrftoken": "value2"
}
```

### Usage
```python
python3 RedShelf-BypassDRM-PDFDownload.py
```

![redshelf-virdocs-export-pdf](screenshots/redshelf-virdocs-export-pdf.png)

### Path to download without using the `img` tag

- Erikas Taroza: https://github.com/erikas-taroza/redshelf_downloader

```
https://platform.virdocs.com/spine/XXXXXXX/{}
```