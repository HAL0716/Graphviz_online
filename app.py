import os
import subprocess
import itertools
from flask import Flask, render_template, request, send_file, jsonify
from pdf2image import convert_from_bytes
from dot2tex import dot2tex
from src import PeriodicFiniteType

app = Flask(__name__)
UPLOAD_DIR = 'static/uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ファイル名
PNG_FILE = 'graph.png'
TEX_FILE = 'graph.tex'
PDF_FILE = 'graph.pdf'

def get_upload_path(filename: str) -> str:
    """UPLOAD_DIR 内のフルパスを返す"""
    return os.path.join(UPLOAD_DIR, filename)

def generate_forbidden_words(symbols, length):
    """禁止語の生成"""
    if not symbols or not length:
        return []
    return [''.join(p) for p in itertools.product(symbols, repeat=int(length))]

def process_tex(tex_code: str) -> str:
    """LaTeXコードを整形"""
    tex_code = tex_code.replace(
        r'\documentclass{article}', r'\documentclass[border=5pt]{standalone}'
    )
    return '\n'.join(
        line for line in tex_code.splitlines()
        if not line.strip().startswith(r'\enlargethispage')
    )

def generate_tex(dot_code: str) -> None:
    """TeXファイルを生成"""
    tex_file_path = get_upload_path(TEX_FILE)
    with open(tex_file_path, 'w') as f:
        f.write(process_tex(dot2tex(dot_code)))

def generate_pdf() -> None:
    """PDFファイルの生成"""
    result = subprocess.run(
        ['pdflatex', TEX_FILE], cwd=UPLOAD_DIR, check=False, capture_output=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"PDF generation failed: {result.stderr.decode()}")

def convert_pdf_to_png() -> None:
    """PDFをPNGに変換"""
    pdf_path = get_upload_path(PDF_FILE)
    png_path = get_upload_path(PNG_FILE)
    
    with open(pdf_path, 'rb') as f:
        images = convert_from_bytes(f.read())
        images[0].save(png_path, 'PNG')

def get_param(params: dict, key: str, default: float) -> float:
    """params 辞書から値を取得するヘルパー関数"""
    if params and key in params and str(params[key]).strip():
        return float(params[key])
    return default

@app.route('/', methods=['GET'])
def index():
    symbols = list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return render_template('index.html', symbols=symbols)

@app.route('/get_forbidden_words', methods=['POST'])
def get_forbidden_words_route():
    symbols = request.json.get('symbols', [])
    length = int(request.json.get('length', 2))
    words = generate_forbidden_words(symbols, length)
    return jsonify(words)

@app.route('/generate', methods=['POST'])
def generate_graph():
    data = request.json
    selected_symbols = data.get('symbols', [])
    period = int(data.get('period', 2))
    forbidden_length = int(data.get('forbidden_length', 2))
    forbidden_words = data.get('forbidden_words', [])

    # PeriodicFiniteTypeのインスタンスを作成
    pft = PeriodicFiniteType(period, forbidden_length, forbidden_words, True)
    pft.set_adj_list(selected_symbols)
    dot_code = pft.dot(data)
    
    try:
        # LaTeX の生成と PDF への変換
        generate_tex(dot_code)
        generate_pdf()
        convert_pdf_to_png()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"image_url": f"/static/uploads/graph.png?{os.urandom(4).hex()}"})

@app.route('/download')
def download_image():
    path = get_upload_path(PNG_FILE)
    return send_file(path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)