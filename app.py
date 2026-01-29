import json
import base64
import io
import os
import pathlib

from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont
from rembg import remove, new_session

app = Flask(__name__)

# Inizializza sessione rembg con modello leggero u2netp (~4MB)
print("[figurine] Inizializzazione modello u2netp...")
REMBG_SESSION = new_session("u2netp")
print("[figurine] ✅ Modello u2netp caricato!")

# Path assets
BASE_DIR = pathlib.Path(__file__).parent.resolve()
TEMPLATE_PATH = BASE_DIR / "tamplate.png"
FONT_PATH = BASE_DIR / "arialbd.ttf"

# Mapping ruoli
ROLE_MAP = {
    "P": "Portiere",
    "D": "Difensore",
    "C": "Centrocampista",
    "A": "Attaccante",
    "N/D": "N/D"
}


def genera_figurina(foto_base64: str, dati: dict) -> dict:
    try:
        # Validazione
        chiavi_richieste = ['nome', 'cognome', 'squadra', 'ruolo', 'anno']
        chiavi_mancanti = [k for k in chiavi_richieste if k not in dati]
        if chiavi_mancanti:
            return {"success": False, "error": f"Chiavi mancanti: {chiavi_mancanti}"}

        print(f"[figurine] Elaborazione: {dati['nome']} {dati['cognome']}...")

        # 1. Decode base64 -> bytes
        foto_bytes = base64.b64decode(foto_base64)

        # 2. Carica template
        if not TEMPLATE_PATH.exists():
            return {"success": False, "error": f"Template not found at {TEMPLATE_PATH}"}
        sfondo = Image.open(str(TEMPLATE_PATH)).convert("RGBA")
        W, H = sfondo.size

        # 3. Rimuovi sfondo con rembg
        print("[figurine] Rimozione sfondo in corso...")
        foto_scontornata = remove(foto_bytes, session=REMBG_SESSION)
        print(f"[figurine] ✅ Sfondo rimosso: {len(foto_scontornata)} bytes")

        # 4. Carica immagine scontornata
        giocatore = Image.open(io.BytesIO(foto_scontornata)).convert("RGBA")
        print("[figurine] Foto scontornata caricata")

        # 5. Ridimensionamento e posizionamento
        target_y_start = int(H * 0.15)
        target_y_end = int(H * 0.78)
        target_height = target_y_end - target_y_start

        aspect_ratio = giocatore.width / giocatore.height
        new_height = int(target_height * 1.45)
        new_width = int(new_height * aspect_ratio)

        giocatore = giocatore.resize((new_width, new_height), Image.Resampling.LANCZOS)

        center_x = W // 2
        pos_x = center_x - (new_width // 2)
        pos_y = target_y_start + (target_height - new_height)

        # 6. Compositing
        canvas = Image.new("RGBA", sfondo.size)
        canvas.paste(sfondo, (0, 0))
        canvas.paste(giocatore, (pos_x, pos_y), mask=giocatore)

        # 7. Testo
        draw = ImageDraw.Draw(canvas)

        try:
            font = ImageFont.truetype(str(FONT_PATH), 33)
        except IOError:
            font = ImageFont.load_default()
            print(f"[figurine] Font non trovato a {FONT_PATH}, uso default")

        text_color = (30, 30, 30, 255)
        text_x = int(W * 0.08)
        line_spacing = int(H * 0.040)
        offset_x_labels = int(W * 0.20)

        ruolo_completo = ROLE_MAP.get(dati['ruolo'], dati['ruolo'])

        nome_completo = f"{dati['cognome']} {dati['nome']}".upper()
        squadra = dati['squadra'].upper()
        ruolo = ruolo_completo.upper()
        anno = str(dati['anno'])

        y_nome = int(H * 0.795)
        y_squadra = y_nome + line_spacing
        y_ruolo = y_squadra + line_spacing
        y_anno = y_ruolo + line_spacing

        draw.text((text_x + offset_x_labels, y_nome), nome_completo, font=font, fill=text_color)
        draw.text((text_x + offset_x_labels, y_squadra), squadra, font=font, fill=text_color)
        draw.text((text_x + offset_x_labels, y_ruolo), ruolo, font=font, fill=text_color)
        draw.text((text_x + offset_x_labels, y_anno), anno, font=font, fill=text_color)

        # 8. Salva come PNG in memoria
        bg = Image.new("RGB", canvas.size, (255, 255, 255))
        bg.paste(canvas, mask=canvas.split()[3])

        output = io.BytesIO()
        bg.save(output, format='PNG')
        figurina_base64 = base64.b64encode(output.getvalue()).decode('utf-8')

        print(f"[figurine] ✅ Figurina generata: {len(output.getvalue()) // 1024}KB")

        return {
            "success": True,
            "figurinaBase64": figurina_base64,
            "size": len(output.getvalue())
        }

    except Exception as e:
        print(f"[figurine] ❌ Errore: {str(e)}")
        return {"success": False, "error": str(e)}


@app.route('/api/generate-figurine', methods=['POST', 'OPTIONS'])
def generate_figurine():
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    try:
        data = request.get_json()
        foto_base64 = data.get('fotoBase64')
        dati_giocatore = data.get('datiGiocatore')

        if not foto_base64 or not dati_giocatore:
            result = {"success": False, "error": "Missing fotoBase64 or datiGiocatore"}
        else:
            result = genera_figurina(foto_base64, dati_giocatore)

        response = jsonify(result)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    except Exception as e:
        response = jsonify({"success": False, "error": str(e)})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "model": "u2netp",
        "template_exists": TEMPLATE_PATH.exists(),
        "font_exists": FONT_PATH.exists()
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
