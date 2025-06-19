# Import library yang dibutuhkan
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import os 
import json 
import base64 # Untuk encoding/decoding base64, jika diperlukan untuk mengirim gambar

# Inisialisasi aplikasi Flask
app = Flask(__name__)
# Mengizinkan CORS (Cross-Origin Resource Sharing) untuk komunikasi frontend-backend
CORS(app) 

# --- Konfigurasi API Gemini ---
# API Key Anda. Disarankan untuk menggunakan environment variable dalam produksi.
# Untuk demonstrasi, kita langsung masukkan di sini sesuai permintaan.
GEMINI_API_KEY = "AIzaSyBJ3cFd100yNCi6GLZk4U621iWcfKxAW38" # API Key yang Anda berikan
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GEMINI_IMAGE_MODEL_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent" # Gemini mendukung multimodal

# --- Simulated In-Memory Database for User Preferences ---
# Dalam aplikasi nyata, ini akan diganti dengan database (misalnya Firestore, PostgreSQL)
# dan user_id akan didapatkan dari sistem otentikasi.
# Untuk demo, kita gunakan dummy user_id dan penyimpanan in-memory.
user_character_preferences = {
    "dummy_user_123": {"character_option": "new"} # Default for a dummy user
}

# --- Fungsi untuk Memanggil Gemini API (dengan respons terstruktur) ---
def generate_structured_text_with_gemini(prompt_text):
    """
    Memanggil Gemini API untuk menghasilkan teks berdasarkan prompt dengan respons terstruktur (JSON).
    """
    headers = {
        'Content-Type': 'application/json',
    }
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt_text}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json", 
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "prompt_id": {"type": "STRING", "description": "Detailed video prompt in Indonesian"},
                    "prompt_en": {"type": "STRING", "description": "Detailed video prompt in English"},
                    "visual_audio_suggestions_id": {"type": "STRING", "description": "Suggestions for visuals and audio in Indonesian"},
                    "visual_audio_suggestions_en": {"type": "STRING", "description": "Suggestions for visuals and audio in English"}
                },
                "propertyOrdering": ["prompt_id", "prompt_en", "visual_audio_suggestions_id", "visual_audio_suggestions_en"] 
            }
        }
    }

    try:
        response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", json=payload, headers=headers)
        response.raise_for_status() 
        result = response.json()
        
        if result and result.get('candidates') and len(result['candidates']) > 0 and \
           result['candidates'][0].get('content') and result['candidates'][0]['content'].get('parts') and \
           len(result['candidates'][0]['content']['parts']) > 0:
            
            json_string = result['candidates'][0]['content']['parts'][0]['text']
            parsed_json = json.loads(json_string)
            return (
                parsed_json.get('prompt_id', ''), 
                parsed_json.get('prompt_en', ''),
                parsed_json.get('visual_audio_suggestions_id', ''),
                parsed_json.get('visual_audio_suggestions_en', '')
            )
        else:
            print(f"Unexpected Gemini response structure: {result}")
            return None, None, None, None
    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API: {e}")
        return None, None, None, None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from Gemini response: {json_string} - {e}")
        return None, None, None, None

# --- Fungsi untuk Memanggil Gemini API (dengan respons teks biasa) ---
def generate_plain_text_with_gemini(prompt_text, language='id', image_data_base64=None, mime_type=None):
    """
    Memanggil Gemini API untuk menghasilkan teks biasa berdasarkan prompt,
    dengan opsi untuk menyertakan data gambar.
    """
    headers = {
        'Content-Type': 'application/json',
    }
    
    parts = [{"text": prompt_text}]
    if image_data_base64 and mime_type:
        parts.append({
            "inlineData": {
                "mimeType": mime_type,
                "data": image_data_base64
            }
        })

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": parts
            }
        ],
    }

    try:
        # Menggunakan model Gemini Multimodal (gemini-2.0-flash)
        response = requests.post(f"{GEMINI_IMAGE_MODEL_URL}?key={GEMINI_API_KEY}", json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        print('[DEBUG] Gemini response:', result)
        if result and result.get('candidates') and len(result['candidates']) > 0 and \
           result['candidates'][0].get('content') and result['candidates'][0]['content'].get('parts') and \
           len(result['candidates'][0]['content']['parts']) > 0:
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"Unexpected Gemini response structure for plain text: {result}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API for plain text: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from Gemini plain text response: {result} - {e}")
        return None


# --- Endpoint untuk Menguji Koneksi Server ---
@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

# --- Endpoint untuk Menyimpan Preferensi Karakter (Simulasi) ---
@app.route('/save_character_preference', methods=['POST'])
def save_character_preference():
    """
    Endpoint untuk menyimpan preferensi karakter pengguna.
    Ini adalah simulasi, menggunakan penyimpanan in-memory.
    """
    data = request.get_json()
    user_id = data.get('user_id', 'dummy_user_123') # Gunakan dummy_user_id jika tidak disediakan
    character_option = data.get('character_option')

    if not character_option:
        return jsonify({'error': 'Pilihan karakter dibutuhkan.'}), 400

    user_character_preferences[user_id] = {"character_option": character_option}
    print(f"Saved character preference for {user_id}: {character_option}")
    return jsonify({'message': 'Preferensi karakter berhasil disimpan.', 'character_option': character_option}), 200

# --- Endpoint untuk Mengambil Preferensi Karakter (Simulasi) ---
@app.route('/get_character_preference', methods=['GET'])
def get_character_preference():
    """
    Endpoint untuk mengambil preferensi karakter pengguna.
    Ini adalah simulasi, menggunakan penyimpanan in-memory.
    """
    user_id = request.args.get('user_id', 'dummy_user_123') # Gunakan dummy_user_id jika tidak disediakan
    preference = user_character_preferences.get(user_id, {"character_option": "new"})
    return jsonify(preference), 200

# --- Endpoint untuk Menghasilkan Karakter dari Foto (Simulasi Menggunakan Gemini Multimodal) ---
@app.route('/generate_character_from_photo', methods=['POST'])
def generate_character_from_photo_endpoint():
    try:
        if 'image' not in request.files:
            print('[ERROR] Tidak ada file gambar yang diunggah.')
            return jsonify({'error': 'Tidak ada file gambar yang diunggah.'}), 400

        file = request.files['image']
        language = request.form.get('language', 'id')

        if file.filename == '':
            print('[ERROR] Tidak ada file gambar yang dipilih.')
            return jsonify({'error': 'Tidak ada file gambar yang dipilih.'}), 400

        if file:
            image_bytes = file.read()
            image_data_base64 = base64.b64encode(image_bytes).decode('utf-8')
            mime_type = file.mimetype

            print(f'[INFO] Menerima file: {file.filename}, mime: {mime_type}, size: {len(image_bytes)} bytes')

            prompt_instruction_id = "Deskripsikan orang di gambar ini secara singkat untuk digunakan sebagai deskripsi karakter video (maksimal 30 kata). Sebutkan fitur wajah, pakaian, gaya, dan suasana hati secara umum. Berikan dalam Bahasa Indonesia."
            prompt_instruction_en = "Briefly describe the person in this image for use as a video character description (max 30 words). Mention general facial features, clothing, style, and mood. Provide in English."

            character_desc_id = generate_plain_text_with_gemini(prompt_instruction_id, language='id', image_data_base64=image_data_base64, mime_type=mime_type)
            character_desc_en = generate_plain_text_with_gemini(prompt_instruction_en, language='en', image_data_base64=image_data_base64, mime_type=mime_type)

            print(f'[INFO] Hasil Gemini: ID: {character_desc_id}, EN: {character_desc_en}')

            if character_desc_id is None or character_desc_en is None:
                print('[ERROR] Gagal mendeskripsikan karakter dari gambar menggunakan AI.')
                return jsonify({'error': 'Gagal mendeskripsikan karakter dari gambar menggunakan AI.'}), 500

            return jsonify({
                'character_description_id': character_desc_id,
                'character_description_en': character_desc_en
            })
        print('[ERROR] Tidak ada file gambar yang valid.')
        return jsonify({'error': 'Tidak ada file gambar yang valid.'}), 400
    except Exception as e:
        print(f'[EXCEPTION] {str(e)}')
        return jsonify({'error': f'Terjadi kesalahan internal: {str(e)}'}), 500


# --- Endpoint untuk Menghasilkan Target Audiens ---
@app.route('/generate_target_audience', methods=['POST'])
def generate_target_audience_endpoint():
    data = request.get_json()
    product_name = data.get('product_name')
    product_category = data.get('product_category', 'Umum')
    language = data.get('language', 'id')

    if not product_name:
        return jsonify({'error': 'Nama produk dibutuhkan untuk menghasilkan target audiens.'}), 400

    prompt_instruction_id = f"Hasilkan deskripsi singkat (maksimal 2 kalimat) untuk target audiens ideal produk '{product_name}' (kategori: {product_category}) dalam Bahasa Indonesia. Fokus pada demografi, minat, dan kebutuhan."
    prompt_instruction_en = f"Generate a brief description (max 2 sentences) for the ideal target audience of product '{product_name}' (category: {product_category}) in English. Focus on demographics, interests, and needs."
    
    audience_id = generate_plain_text_with_gemini(prompt_instruction_id, language='id')
    audience_en = generate_plain_text_with_gemini(prompt_instruction_en, language='en')

    if audience_id is None or audience_en is None:
        return jsonify({'error': 'Gagal menghasilkan target audiens dari Gemini AI.'}), 500

    return jsonify({'audience_id': audience_id, 'audience_en': audience_en})

# --- Endpoint untuk Menghasilkan Pesan Utama/USP ---
@app.route('/generate_main_message', methods=['POST'])
def generate_main_message_endpoint():
    data = request.get_json()
    product_name = data.get('product_name')
    product_category = data.get('product_category', 'Umum')
    language = data.get('language', 'id')

    if not product_name:
        return jsonify({'error': 'Nama produk dibutuhkan untuk menghasilkan pesan utama.'}), 400

    prompt_instruction_id = f"Hasilkan pesan utama atau Unique Selling Proposition (USP) yang sangat singkat (maksimal 1 kalimat, seperti slogan) untuk produk '{product_name}' (kategori: {product_category}) dalam Bahasa Indonesia."
    prompt_instruction_en = f"Generate a very concise main message or Unique Selling Proposition (USP) (max 1 sentence, like a slogan) for product '{product_name}' (category: {product_category}) in English."

    message_id = generate_plain_text_with_gemini(prompt_instruction_id, language='id')
    message_en = generate_plain_text_with_gemini(prompt_instruction_en, language='en')

    if message_id is None or message_en is None:
        return jsonify({'error': 'Gagal menghasilkan pesan utama dari Gemini AI.'}), 500

    return jsonify({'message_id': message_id, 'message_en': message_en})


# --- Endpoint untuk Menghasilkan Prompt Video Utama ---
@app.route('/generate_prompt', methods=['POST'])
def generate_prompt_endpoint():
    """
    Endpoint untuk menerima input dari user dan menghasilkan prompt video 
    lengkap dalam bahasa Indonesia dan Inggris menggunakan Gemini AI.
    """
    data = request.get_json()
    product_name = data.get('product_name')
    character_option = data.get('character_option', 'new') 
    tone = data.get('tone', 'Informatif') 
    style = data.get('style', 'Langsung') 
    product_category = data.get('product_category', 'Umum') 
    video_length = data.get('video_length', '8 detik') # Default value
    target_audience = data.get('target_audience', 'audiens umum')
    main_message = data.get('main_message', 'tidak ada pesan utama spesifik')
    brand_voice = data.get('brand_voice', 'Profesional')
    vlogging_mode = data.get('vlogging_mode', False) 
    generated_character_description = data.get('generated_character_description', '') # New parameter
    voice_over_language = data.get('voice_over_language', 'id')


    if not product_name:
        return jsonify({'error': 'Nama produk dibutuhkan.'}), 400

    # Tambahkan instruksi karakter ke prompt berdasarkan pilihan
    character_instruction_id = ""
    character_instruction_en = ""
    if generated_character_description: # Prioritaskan deskripsi dari foto jika ada
        character_instruction_id = f"Karakter utama video dideskripsikan sebagai: {generated_character_description}. Pastikan ini adalah karakter utama."
        character_instruction_en = f"The main video character is described as: {generated_character_description}. Ensure this is the primary character."
    elif character_option == 'consistent':
        character_instruction_id = "Pastikan karakter visual dan narasi konsisten dengan karakter yang telah digunakan sebelumnya (jika ada)."
        character_instruction_en = "Ensure visual and narrative character consistency with previously used characters (if any)."
    else: # 'new'
        character_instruction_id = "Buat konsep karakter visual dan narasi yang baru dan unik untuk video ini."
        character_instruction_en = "Create a new and unique visual and narrative character concept for this video."

    # Tambahkan instruksi Vlogging Mode
    vlogging_instruction_id = ""
    vlogging_instruction_en = ""
    if vlogging_mode:
        vlogging_instruction_id = """
        Video ini harus menampilkan karakter yang berbicara langsung ke kamera atau berinteraksi secara verbal dalam gaya vlogging.
        Sertakan contoh dialog atau monolog singkat untuk karakter.
        Gaya presentasi harus seperti seorang vlogger yang mereview produk.
        """
        vlogging_instruction_en = """
        This video should feature a character speaking directly to the camera or verbally interacting in a vlogging style.
        Include brief dialogue or monologues for the character.
        The presentation style should be like a vlogger reviewing a product.
        """

    # Tambahkan instruksi voice over ke prompt jika vlogging_mode aktif
    voice_over_instruction_id = ''
    voice_over_instruction_en = ''
    if vlogging_mode:
        if voice_over_language == 'id':
            voice_over_instruction_id = '\nDialog/voice over karakter HARUS menggunakan Bahasa Indonesia.'
            voice_over_instruction_en = '\nCharacter dialogue/voice over MUST be in Indonesian.'
        elif voice_over_language == 'en':
            voice_over_instruction_id = '\nDialog/voice over karakter HARUS menggunakan Bahasa Inggris.'
            voice_over_instruction_en = '\nCharacter dialogue/voice over MUST be in English.'
        # Bisa tambah bahasa lain jika perlu

    # Instruksi mendetail untuk Gemini agar menghasilkan prompt Veo 3
    # Kita minta Gemini menghasilkan langsung dalam format JSON dengan kedua bahasa
    prompt_instruction = f"""
    Buatkan prompt video review produk yang sangat detail dan profesional untuk produk \"{product_name}\".
    Kategori Produk: \"{product_category}\". Durasi Video Ideal: \"{video_length}\".
    Nada Video: \"{tone}\". Gaya Presentasi: \"{style}\".
    Pesan Utama/USP: \"{main_message}\".
    Target Audiens: \"{target_audience}\".
    Gaya Suara Merek (Brand Voice): \"{brand_voice}\".
    {character_instruction_id}
    {vlogging_instruction_id}
    {voice_over_instruction_id}

    Prompt ini harus sesuai standar Veo 3 untuk video promosi/review produk yang menarik.
    Sertakan elemen-elemen berikut dalam prompt:
    1.  **Judul Video Menarik:** Saran judul yang clickbait dan informatif, sesuai target audiens dan pesan utama.
    2.  **Pembukaan (Hook):** Cara memulai video yang menarik perhatian dalam 5-10 detik pertama, sangat relevan dengan target audiens.
    3.  **Pengenalan Produk:** Deskripsi singkat produk, fitur utama, dan masalah yang dipecahkan, menyoroti pesan utama/USP.
    4.  **Fitur Unggulan (Detail):** Jelaskan 3-5 fitur kunci secara mendalam, termasuk manfaatnya bagi pengguna.
        * Contoh penggunaan fitur yang spesifik dan menarik bagi target audiens.
        * Keunggulan dibandingkan kompetitor (jika relevan dan sesuai gaya).
    5.  **Pengalaman Pengguna/Demo:** Bagaimana produk digunakan dalam skenario nyata yang relevan dengan target audiens.
    6.  **Kelebihan & Kekurangan (Objektif):** Sebutkan secara jujur kelebihan dan (jika ada) kekurangan kecil, disesuaikan dengan nada dan gaya, serta brand voice.
    7.  **Kesimpulan & Rekomendasi:** Ringkasan mengapa produk ini layak dan untuk siapa direkomendasikan, dengan menekankan pesan utama/USP.
    8.  **Call to Action (CTA):** Ajak penonton untuk 'beli sekarang', 'kunjungi link', 'follow', dll., disesuaikan dengan target audiens dan gaya presentasi.
    9.  **Visual & Audio (Saran):** Saran tentang jenis footage (close-up, wide-shot), transisi, musik latar, efek suara, yang mendukung nada, gaya, brand voice, dan menarik bagi target audiens.
    10. **Tone & Style:** Nada bicara (informatif, antusias, jujur), gaya presentasi, yang konsisten dengan brand voice.
    
    Tampilkan hasil prompt untuk Bahasa Inggris secara terpisah setelah prompt Bahasa Indonesia, dengan instruksi dan detail yang sama.

    Format output JSON dengan properti: 
    `prompt_id` (prompt video utama Bahasa Indonesia),
    `prompt_en` (prompt video utama Bahasa Inggris),
    `visual_audio_suggestions_id` (saran visual/audio Bahasa Indonesia),
    `visual_audio_suggestions_en` (saran visual/audio Bahasa Inggris).
    """

    prompt_id, prompt_en, visual_audio_suggestions_id, visual_audio_suggestions_en = generate_structured_text_with_gemini(prompt_instruction)

    if prompt_id is None or prompt_en is None:
        return jsonify({'error': 'Gagal mendapatkan respons valid dari Gemini AI.'}), 500

    return jsonify({
        'prompt_id': prompt_id,
        'prompt_en': prompt_en,
        'visual_audio_suggestions_id': visual_audio_suggestions_id,
        'visual_audio_suggestions_en': visual_audio_suggestions_en
    })

# --- Endpoint untuk Mengambil Prompt dari Video Eksternal (Simulasi) ---
@app.route('/get_external_prompt', methods=['POST'])
def get_external_prompt_endpoint():
    """
    Endpoint ini mensimulasikan pengambilan prompt dari link video TikTok/YouTube.
    Sekarang mendukung semua format link (web/mobile/short) TikTok & YouTube.
    """
    data = request.get_json()
    video_url = data.get('video_url', '').strip()

    if not video_url:
        return jsonify({'error': 'Link video dibutuhkan.'}), 400

    url_lower = video_url.lower()
    # Deteksi semua format TikTok & YouTube
    is_youtube = any(x in url_lower for x in ['youtube.com', 'youtu.be', 'm.youtube.com'])
    is_tiktok = any(x in url_lower for x in ['tiktok.com', 'vt.tiktok.com', 'vm.tiktok.com'])

    simulated_prompt_id = ""
    simulated_prompt_en = ""
    simulated_visual_audio_id = ""
    simulated_visual_audio_en = ""

    if is_youtube:
        simulated_prompt_id = f"""
        (Prompt Simulasi dari YouTube: {video_url})
        **Judul:** "Review Mendalam: Laptop Gaming Terbaru yang Mengguncang Pasar!"
        **Pembukaan:** Adegan dramatis performa gaming, "Apakah ini laptop impian para gamer?"
        **Fitur Utama:** Performa CPU/GPU, kualitas layar, sistem pendingin.
        **Demo:** Uji benchmark, gameplay berat, pengeditan video.
        **Kesimpulan:** Laptop ini adalah monster performa untuk gamer serius dan kreator konten.
        **CTA:** "Jangan lewatkan! Link pembelian di deskripsi video!"
        """
        simulated_prompt_en = f"""
        (Simulated Prompt from YouTube: {video_url})
        **Title:** "In-depth Review: The New Gaming Laptop Shaking Up the Market!"
        **Opening:** Dramatic gaming performance scene, "Is this the ultimate gamer's dream laptop?"
        **Key Features:** CPU/GPU performance, screen quality, cooling system.
        **Demo:** Benchmark tests, heavy gameplay, video editing.
        **Conclusion:** This laptop is a performance beast for serious gamers and content creators.
        **CTA:** "Don't miss out! Purchase link in video description!"
        """
        simulated_visual_audio_id = """
        **Saran Visual & Audio:**
        -   Visual: Scene intro 3D logo gaming, footage close-up keyboard RGB, grafis spek overlay.
        -   Audio: Musik latar epik, efek suara keyboard mekanik, suara kipas laptop (rendah).
        """
        simulated_visual_audio_en = """
        **Visual & Audio Suggestions:**
        -   Visual: 3D gaming logo intro scene, RGB keyboard close-up footage, spec overlay graphics.
        -   Audio: Epic background music, mechanical keyboard sound effects, low laptop fan sound.
        """
    elif is_tiktok:
        simulated_prompt_id = f"""
        (Prompt Simulasi dari TikTok: {video_url})
        **Judul:** "Wajib Punya! Smartwatch Estetik & Fitur Lengkap #smartwatch #fashiontech"
        **Pembukaan:** Transisi cepat gaya hidup aktif dengan smartwatch.
        **Fitur Cepat:** Pelacakan kesehatan, notifikasi, desain.
        **Sound:** Musik trendi, efek suara transisi.
        **CTA:** "Cek keranjang kuning sekarang!"
        """
        simulated_prompt_en = f"""
        (Simulated Prompt from TikTok: {video_url})
        **Title:** "Must-Have! Aesthetic & Feature-Packed Smartwatch #smartwatch #fashiontech"
        **Opening:** Fast-paced active lifestyle transitions with the smartwatch.
        **Quick Features:** Health tracking, notifications, design.
        **Sound:** Trendy music, transition sound effects.
        **CTA:** "Check the yellow basket now!"
        """
        simulated_visual_audio_id = """
        **Saran Visual & Audio:**
        -   Visual: Transisi cepat dengan efek 'glitch', tampilan UI smartwatch, orang berolahraga dengan smartwatch.
        -   Audio: Musik pop ceria, efek 'swoosh' untuk transisi.
        """
        simulated_visual_audio_en = """
        **Visual & Audio Suggestions:**
        -   Visual: Fast transitions with 'glitch' effects, smartwatch UI display, people exercising with the smartwatch.
        -   Audio: Upbeat pop music, 'swoosh' effects for transitions.
        """
    else:
        simulated_prompt_id = f"""
        (Prompt Simulasi Umum dari Link: {video_url})
        **Judul:** "Review Produk Keren: {video_url} Ini Bakal Ubah Hidupmu!"
        **Pembukaan:** Tunjukkan masalah umum, lalu perkenalkan produk sebagai solusi.
        **Manfaat:** Sebutkan 3 manfaat utama.
        **Visual:** Dekat, bersih, fokus pada produk.
        **CTA:** "Pelajari lebih lanjut di sini!"
        """
        simulated_prompt_en = f"""
        (Generic Simulated Prompt from Link: {video_url})
        **Title:** "Awesome Product Review: {video_url} Will Change Your Life!"
        **Opening:** Show a common problem, then introduce the product as a solution.
        **Benefits:** Mention 3 key benefits.
        **Visuals:** Close-ups, clean, focus on the product.
        **CTA:** "Learn more here!"
        """
        simulated_visual_audio_id = """
        **Saran Visual & Audio:**
        -   Visual: Pencahayaan alami, latar belakang minimalis, grafis teks sederhana.
        -   Audio: Musik latar tenang, suara narasi jelas.
        """
        simulated_visual_audio_en = """
        **Visual & Audio Suggestions:**
        -   Visual: Natural lighting, minimalist background, simple text graphics.
        -   Audio: Calm background music, clear narration voice.
        """
    return jsonify({
        'prompt': simulated_prompt_id + "\n\n---\n\n" + simulated_prompt_en,
        'visual_audio_suggestions_id': simulated_visual_audio_id,
        'visual_audio_suggestions_en': simulated_visual_audio_en
    })

# --- Menjalankan Aplikasi Flask ---
if __name__ == '__main__':
    # Pastikan aplikasi berjalan di port 5000 agar sesuai dengan frontend
    # Untuk produksi, Anda akan menggunakan server WSGI seperti Gunicorn/uWSGI
    app.run(debug=True, port=5000)
