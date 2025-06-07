# Youtube To PDF - UTUBE2PDF

[![Clone](https://img.shields.io/badge/Clone%20Repo-Click%20Here-blue)](https://dub.sh/utube2pdf)
🔗 [View Source](https://github.com/puspendusantra/youtube-to-pdf)

A Flask application that converts YouTube videos to PDF by extracting frames at customizable intervals.

## ✨ Features
- YouTube video downloading
- Frame extraction at configurable intervals
- PDF generation from frames
- Simple web interface
- Progress tracking

## 🛠️ Installation

### Requirements
- Flask==3.0.2
- opencv-python-headless==4.9.0.80
- scikit-image==0.22.0
- yt-dlp==2025.2.19
- numpy==1.26.4
- fpdf2==2.7.8
- Pillow==10.2.0


```bash
git clone https://github.com/puspendusantra/youtube-to-pdf.git
cd youtube-to-pdf
pip install -r requirements.txt
pyhton app.py
