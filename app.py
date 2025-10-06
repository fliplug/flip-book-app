from flask import Flask, request, send_file, render_template_string, url_for
from pdf2image import convert_from_path
import os
import uuid
import shutil

app = Flask(__name__)

UPLOAD_FOLDER = './uploads'
IMAGE_FOLDER = './static/flipbooks'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGE_FOLDER, exist_ok=True)


@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Upload PDF</title></head>
    <body>
      <h1>Upload PDF</h1>
      <form action="/upload_pdf" method="POST" enctype="multipart/form-data">
        <input type="file" name="file" required>
        <button type="submit">Upload</button>
      </form>
    </body>
    </html>
    '''


@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    file = request.files.get('file')
    if not file:
        return "No file uploaded", 400

    pdf_id = str(uuid.uuid4())
    pdf_path = os.path.join(UPLOAD_FOLDER, f'{pdf_id}.pdf')
    file.save(pdf_path)

    pages = convert_from_path(pdf_path, dpi=150)
    book_dir = os.path.join(IMAGE_FOLDER, pdf_id)
    os.makedirs(book_dir, exist_ok=True)

    for i, page in enumerate(pages, start=1):
        img_path = os.path.join(book_dir, f'page_{i}.png')
        page.save(img_path, 'PNG')

    html_content = generate_flipbook_html(pdf_id, len(pages))
    html_path = os.path.join(book_dir, 'index.html')
    with open(html_path, 'w') as f:
        f.write(html_content)

    zip_path = shutil.make_archive(base_name=book_dir, format='zip', root_dir=book_dir)

    flipbook_url = url_for('static', filename=f'flipbooks/{pdf_id}/index.html', _external=True)
    download_url = url_for('download_flipbook', pdf_id=pdf_id, _external=True)

    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
      <title>Flipbook Ready</title>
      <style>
        body { font-family: Arial, sans-serif; padding: 30px; text-align: center; }
        iframe { width: 100%; height: 600px; border: 1px solid #ccc; margin-bottom: 20px; max-width: 900px; }
        .button {
          display: inline-block;
          margin: 10px;
          padding: 10px 20px;
          background: #007bff;
          color: white;
          text-decoration: none;
          border-radius: 5px;
        }
        input[type="text"] {
          width: 80%;
          padding: 10px;
          font-size: 16px;
          text-align: center;
        }
      </style>
    </head>
    <body>
      <h1>📘 Your Flipbook is Ready!</h1>
      <iframe src="{{ flipbook_url }}" frameborder="0"></iframe><br>
      <a href="{{ download_url }}" class="button" download>Download ZIP</a>
      <a href="{{ flipbook_url }}" class="button" target="_blank">Open Flipbook</a>
      <p>Share this link:</p>
      <input type="text" value="{{ flipbook_url }}" onclick="this.select();" readonly>
    </body>
    </html>
    ''', flipbook_url=flipbook_url, download_url=download_url)


@app.route('/download/<pdf_id>')
def download_flipbook(pdf_id):
    book_dir = os.path.join(IMAGE_FOLDER, pdf_id)
    zip_path = f"{book_dir}.zip"
    if not os.path.exists(zip_path):
        shutil.make_archive(base_name=book_dir, format='zip', root_dir=book_dir)
    return send_file(zip_path, as_attachment=True)


def generate_flipbook_html(pdf_id, num_pages):
    # First and last pages will be "hard" cover
    pages_html = f'''
    <div class="page page-cover page-cover-top" data-density="hard">My Book</div>
    '''
    for i in range(1, num_pages + 1):
        pages_html += f'''
        <div class="page"><img src="page_{i}.png" alt="Page {i}" /></div>
        '''
    pages_html += f'''
    <div class="page page-cover page-cover-bottom" data-density="hard">The End</div>
    '''

    return f'''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Flipbook Viewer</title>
  <style>
    body {{
      margin: 0; padding: 0;
      background: #ccc;
      font-family: sans-serif;
    }}
    #bookContainer {{
      width: 900px;
      height: 600px;
      margin: 40px auto;
    }}
    .page {{
      background: white;
      width: 100%;
      height: 100%;
      box-sizing: border-box;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .page img {{
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
    }}
    .page-cover {{
      background: #333;
      color: white;
      font-size: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/page-flip@2.0.7/dist/js/page-flip.browser.min.js"></script>
</head>
<body>

<div id="bookContainer">
  {pages_html}
</div>

<script>
  const pageFlip = new St.PageFlip(document.getElementById("bookContainer"), {{
    width: 450,
    height: 600,
    size: "fixed",
    showCover: true,
    flippingTime: 1000,
    useMouseEvents: true,
    maxShadowOpacity: 0.5
  }});

  pageFlip.loadFromHTML(document.querySelectorAll(".page"));
</script>

</body>
</html>
'''


if __name__ == '__main__':
    app.run(debug=True)
