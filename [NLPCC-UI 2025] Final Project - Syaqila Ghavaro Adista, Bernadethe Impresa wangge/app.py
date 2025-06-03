from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import json
import re
from urllib.parse import urlparse, parse_qs
import google.generativeai as genai
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Konfigurasi API Keys (menggunakan environment variables untuk keamanan)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "AIzaSyCYTSavzx91Eajmly6gHdkF5mdVsUik1OE")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyABEsr5FEiPhOFCnRszQDoYnHyorIgKzWM")

# Inisialisasi Gemini AI
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("✅ Gemini AI berhasil dikonfigurasi")
except Exception as e:
    print(f"❌ Error konfigurasi Gemini AI: {e}")

# Inisialisasi YouTube API
try:
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    print("✅ YouTube API berhasil dikonfigurasi")
except Exception as e:
    print(f"❌ Error konfigurasi YouTube API: {e}")

def extract_video_id(url):
    """Ekstrak video ID dari URL YouTube"""
    parsed_url = urlparse(url)
    if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
        if parsed_url.path == '/watch':
            return parse_qs(parsed_url.query)['v'][0]
    elif parsed_url.hostname in ['youtu.be']:
        return parsed_url.path[1:]
    return None

def get_youtube_comments(video_id, max_results=100):
    """Mengambil komentar dari video YouTube"""
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=max_results,
            order="relevance"
        )
        response = request.execute()
        
        comments = []
        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']
            comments.append({
                'text': comment['textDisplay'],
                'author': comment['authorDisplayName'],
                'likes': comment['likeCount'],
                'published': comment['publishedAt']
            })
        
        return comments
    except Exception as e:
        return None

def analyze_comments_with_gemini(comments):
    """Menganalisis komentar menggunakan Gemini AI"""
    try:
        # Gabungkan semua komentar
        all_comments = "\n".join([comment['text'] for comment in comments[:1000]])  
        
        prompt = f"""
        Analisis komentar-komentar YouTube berikut dan berikan ringkasan dalam bahasa Indonesia:

        Komentar:
        {all_comments}

        Berikan analisis berupa:
        1. Sentimen umum (positif/negatif/netral)
        2. Topik utama yang dibahas
        3. Emosi dominan
        4. Poin-poin penting yang sering disebutkan
        5. Kesimpulan singkat tentang respons audiens

        Format jawaban dalam bentuk yang mudah dibaca.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error dalam analisis: {str(e)}"

@app.route('/')
def index():
    """Halaman utama aplikasi"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'YouTube Comment Analyzer is running!',
        'endpoints': {
            'main': '/',
            'analyze': '/analyze',
            'test': '/test'
        }
    })

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        print("📥 Menerima request analisis...")
        data = request.json
        youtube_url = data.get('url')
        
        if not youtube_url:
            print("❌ URL YouTube tidak ditemukan")
            return jsonify({'success': False, 'error': 'URL YouTube diperlukan'})
        
        print(f"🔍 Menganalisis URL: {youtube_url}")
        
        # Ekstrak video ID
        video_id = extract_video_id(youtube_url)
        if not video_id:
            print("❌ Video ID tidak valid")
            return jsonify({'success': False, 'error': 'URL YouTube tidak valid'})
        
        print(f"✅ Video ID ditemukan: {video_id}")
        
        # Ambil komentar
        print("📝 Mengambil komentar...")
        comments = get_youtube_comments(video_id)
        if comments is None:
            print("❌ Gagal mengambil komentar")
            return jsonify({'success': False, 'error': 'Gagal mengambil komentar. Pastikan video memiliki komentar yang dapat diakses.'})
        
        if len(comments) == 0:
            print("⚠️ Tidak ada komentar ditemukan")
            return jsonify({'success': False, 'error': 'Tidak ada komentar ditemukan pada video ini'})
        
        print(f"✅ Berhasil mengambil {len(comments)} komentar")
        
        # Analisis dengan Gemini
        print("🤖 Memulai analisis AI...")
        analysis = analyze_comments_with_gemini(comments)
        print("✅ Analisis AI selesai")
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'total_comments': len(comments),
            'analysis': analysis
        })
        
    except Exception as e:
        print(f"❌ Error dalam analisis: {str(e)}")
        return jsonify({'success': False, 'error': f'Terjadi error: {str(e)}'})

@app.route('/test', methods=['GET'])
def test():
    """Endpoint untuk test koneksi"""
    return jsonify({
        'success': True,
        'message': 'Server berjalan dengan baik!',
        'youtube_api': 'OK' if 'youtube' in globals() else 'ERROR',
        'gemini_api': 'OK' if 'model' in globals() else 'ERROR'
    })

if __name__ == '__main__':
    print("🚀 Memulai YouTube Comment Analyzer...")
    print("📋 Konfigurasi:")
    print(f"   - YouTube API: {'✅' if YOUTUBE_API_KEY else '❌'}")
    print(f"   - Gemini API: {'✅' if GEMINI_API_KEY else '❌'}")
    print("🌐 Server akan berjalan di: http://localhost:5000")
    print("📱 Tekan Ctrl+C untuk menghentikan server")
    print("-" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)