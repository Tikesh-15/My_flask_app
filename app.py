from flask import Flask, request, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename
from PIL import Image
import os
import time
import smtplib
from email.message import EmailMessage

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
COMPRESSED_FOLDER = 'compressed'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COMPRESSED_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'gif', 'jpg', 'jpeg', 'png', 'bmp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['COMPRESSED_FOLDER'] = COMPRESSED_FOLDER

# Pillow version compatibility
try:
    RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE = Image.ANTIALIAS

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def compress_image(input_path, output_path, target_size_kb):
    img = Image.open(input_path)
    ext = input_path.rsplit('.', 1)[1].lower()
    target_size_bytes = target_size_kb * 1024
    width, height = img.size
    quality = 95

    if ext in ['jpg', 'jpeg', 'png', 'bmp']:
        if ext in ['png', 'bmp']:
            img = img.convert('RGB')
            output_path = output_path.rsplit('.', 1)[0] + ".jpg"
        while True:
            img.save(output_path, format='JPEG', optimize=True, quality=quality)
            current_size = os.path.getsize(output_path)
            if current_size <= target_size_bytes or quality <= 20:
                break
            quality -= 5
        while current_size > target_size_bytes and width > 100 and height > 100:
            width = int(width * 0.9)
            height = int(height * 0.9)
            img = img.resize((width, height), RESAMPLE)
            img.save(output_path, format='JPEG', optimize=True, quality=quality)
            current_size = os.path.getsize(output_path)

    elif ext == 'gif':
        img.save(output_path, optimize=True)
        current_size = os.path.getsize(output_path)
        if current_size > target_size_bytes:
            while width > 100 and height > 100:
                width = int(width * 0.9)
                height = int(height * 0.9)
                img = img.resize((width, height), RESAMPLE)
                img.save(output_path, optimize=True)
                if os.path.getsize(output_path) <= target_size_bytes:
                    break
    else:
        img.save(output_path)

    return os.path.getsize(output_path) / 1024, os.path.basename(output_path)

# Home route – HTML form भी यही render करेगा
@app.route('/')
def index():
    return render_template('index.html')

# Feedback route
@app.route('/feedback', methods=['POST'])
def feedback():
    name = request.form['name']
    sender_email = request.form['email']
    message = request.form['message']

    try:
        email_sender = 'dewanganlucky625@gmail.com'
        email_password = 'hkhk acjl kxqx hvpz'
        email_receiver = 'dewanganlucky625@gmail.com'

        subject = f"New Feedback from {name}"
        email = EmailMessage()
        email['From'] = email_sender
        email['To'] = email_receiver
        email['Subject'] = subject
        email.set_content(f"Name: {name}\nEmail: {sender_email}\n\nFeedback:\n{message}")

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(email_sender, email_password)
            smtp.send_message(email)

        return "<h3>Thanks for your feedback!</h3>"

    except Exception as e:
        return f"<h3>Failed to send feedback: {str(e)}</h3>"

# Compress image route
@app.route('/compress', methods=['POST'])
def compress():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    try:
        target_size_kb = int(request.form.get('target_size_kb', 100))
        if target_size_kb <= 0:
            raise ValueError
    except:
        return jsonify({'error': 'Invalid target size'}), 400

    filename = f"{int(time.time())}_{secure_filename(file.filename)}"
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    output_path = os.path.join(app.config['COMPRESSED_FOLDER'], filename)

    file.save(input_path)

    try:
        final_size_kb, final_filename = compress_image(input_path, output_path, target_size_kb)
    except Exception as e:
        return jsonify({'error': f"Compression failed: {str(e)}"}), 500

    return jsonify({
        'download_url': f"/download/{final_filename}",
        'size_kb': round(final_size_kb, 2)
    })

# Download route
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['COMPRESSED_FOLDER'], filename, as_attachment=True)

# App run
if __name__ == '__main__':
    app.run(debug=True)
