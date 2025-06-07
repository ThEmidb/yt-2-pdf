import os
import re
import cv2
from flask import Flask, render_template, request, send_file, flash
from werkzeug.utils import secure_filename
from fpdf import FPDF
from PIL import Image
import yt_dlp
import shutil

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit
app.config['TEMP_FOLDER'] = 'temp'

# Ensure temp directories exist
os.makedirs(os.path.join(app.config['TEMP_FOLDER'], 'videos'), exist_ok=True)
os.makedirs(os.path.join(app.config['TEMP_FOLDER'], 'frames'), exist_ok=True)

def clear_old_items():
    """Clear old files from temp/videos and temp/frames."""
    videos_dir = os.path.join(app.config['TEMP_FOLDER'], 'videos')
    frames_dir = os.path.join(app.config['TEMP_FOLDER'], 'frames')

    for directory in [videos_dir, frames_dir]:
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f'Failed to delete {file_path}. Reason: {e}')

def sanitize_filename(title):
    """Sanitize the filename to remove invalid characters."""
    safe_title = re.sub(r'[\\/*?:"<>|]', '', title)
    safe_title = safe_title.replace(' ', '_')
    return safe_title[:150]

def download_video(url, filename, max_retries=3):
    """Download a YouTube video using yt-dlp."""
    ydl_opts = {
        'outtmpl': filename,
        'format': 'bestvideo[height<=720][ext=mp4]/bestvideo[height<=480][ext=mp4]',
        'ignoreerrors': True
    }
    for retry in range(max_retries):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)
        except Exception as e:
            if retry == max_retries - 1:
                raise Exception(f"Failed to download video after {max_retries} attempts: {str(e)}")

def extract_frames(video_path, output_dir, interval_seconds=5):
    """Extract frames from a video at specified intervals."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = max(1, int(round(fps * interval_seconds)))

    timestamps = []
    frame_count = 0

    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count * frame_interval)
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (1280, 720), interpolation=cv2.INTER_AREA)

        timestamp = int(cap.get(cv2.CAP_PROP_POS_MSEC) / 1000)
        output_path = os.path.join(output_dir, f'frame_{int(timestamp)}.png')
        cv2.imwrite(output_path, frame)
        timestamps.append(timestamp)

        frame_count += 1

    cap.release()
    return timestamps

def create_pdf(frames_dir, output_path):
    """Create a PDF from extracted frames."""
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=False, margin=10)

    frame_files = sorted(
        [f for f in os.listdir(frames_dir) if f.endswith('.png')],
        key=lambda x: int(x.split('_')[1].split('.')[0])
    )

    for frame_file in frame_files:
        img_path = os.path.join(frames_dir, frame_file)
        img = Image.open(img_path)

        pdf.add_page()

        page_width = pdf.w - 20
        page_height = pdf.h - 20
        img_ratio = img.width / img.height
        page_ratio = page_width / page_height

        if img_ratio > page_ratio:
            width = page_width
            height = width / img_ratio
        else:
            height = page_height
            width = height * img_ratio

        x = (pdf.w - width) / 2
        y = (pdf.h - height) / 2

        pdf.image(img_path, x=x, y=y, w=width, h=height)

    pdf.output(output_path)

def process_video(url, interval_seconds, filename=None):
    """Process a YouTube video and generate a PDF."""
    try:
        temp_dir = os.path.join(app.config['TEMP_FOLDER'])
        videos_dir = os.path.join(temp_dir, 'videos')
        frames_dir = os.path.join(temp_dir, 'frames')
        os.makedirs(videos_dir, exist_ok=True)
        os.makedirs(frames_dir, exist_ok=True)

        video_filename = secure_filename(re.sub(r'[^a-zA-Z0-9]', '', url)) + '.mp4'
        video_path = os.path.join(videos_dir, video_filename)

        with yt_dlp.YoutubeDL() as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'video_screenshots')

        download_video(url, video_path)

        if not os.path.exists(video_path):
            raise ValueError("Failed to download video file")

        frames_subdir = os.path.join(frames_dir, video_filename)
        os.makedirs(frames_subdir, exist_ok=True)
        timestamps = extract_frames(video_path, frames_subdir, interval_seconds)

        if not timestamps:
            raise ValueError("No frames extracted")

        safe_title = sanitize_filename(filename) if filename else sanitize_filename(title)
        pdf_path = os.path.join(videos_dir, f"{safe_title}.pdf")

        create_pdf(frames_subdir, pdf_path)

        if not os.path.exists(pdf_path):
            raise ValueError("Failed to create PDF file")

        return pdf_path, safe_title

    except Exception as e:
        raise e

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url')
        interval = request.form.get('interval', type=int, default=10)
        filename = request.form.get('filename')

        try:
            if not url or ('youtube.com/' not in url and 'youtu.be/' not in url):
                raise ValueError("Please enter a valid YouTube URL")

            if interval < 1 or interval > 60:
                raise ValueError("Interval must be between 1 and 60 seconds")

            # Clear old files before processing new request
            clear_old_items()

            pdf_path, video_title = process_video(url, interval, filename)
            return send_file(
                pdf_path,
                as_attachment=True,
                download_name=f"{video_title}.pdf"
            )

        except Exception as e:
            flash(f"Error processing video: {str(e)}", 'error')
            return render_template('index.html')

    return render_template('index.html')
    
@app.route('/main')
def main_page():
    return render_template('main.html')
if __name__ == '__main__':
    app.run(debug=True)
