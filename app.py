import os
import subprocess
import itertools
import tempfile
import zipfile
from flask import Flask, render_template, request, send_file, jsonify
from pdf2image import convert_from_bytes
from dot2tex import dot2tex
from src import PeriodicFiniteType

app = Flask(__name__)
UPLOAD_DIR = 'static/uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ファイル名定義
PNG_FILE = 'graph.png'
TEX_FILE = 'graph.tex'
PDF_FILE = 'graph.pdf'
DOT_FILE = 'graph.dot'


# ========== ファイル関連ユーティリティ ==========

def get_upload_path(filename: str) -> str:
    return os.path.join(UPLOAD_DIR, filename)

def write_file(filename: str, content: str) -> None:
    with open(get_upload_path(filename), 'w') as f:
        f.write(content)

def clean_aux_files():
    """LaTeX中間ファイルを削除"""
    for ext in ['aux', 'log', 'out']:
        path = get_upload_path(f'graph.{ext}')
        if os.path.exists(path):
            os.remove(path)

# ========== LaTeX / DOT 処理系 ==========

def process_tex(tex_code: str) -> str:
    tex_code = tex_code.replace(r'\documentclass{article}', r'\documentclass[border=5pt]{standalone}')
    return '\n'.join(
        line for line in tex_code.splitlines()
        if not line.strip().startswith(r'\enlargethispage')
    )

def generate_tex(dot_code: str) -> None:
    write_file(DOT_FILE, dot_code)
    tex_code = dot2tex(dot_code)
    write_file(TEX_FILE, process_tex(tex_code))

def generate_pdf() -> None:
    result = subprocess.run(['pdflatex', TEX_FILE], cwd=UPLOAD_DIR, check=False, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"PDF生成失敗:\n{result.stderr.decode()}")

def convert_pdf_to_png() -> None:
    pdf_path = get_upload_path(PDF_FILE)
    png_path = get_upload_path(PNG_FILE)

    with open(pdf_path, 'rb') as f:
        images = convert_from_bytes(f.read())
        images[0].save(png_path, 'PNG')


# ========== グラフ生成ロジック ==========

def build_pft_from_data(data) -> PeriodicFiniteType:
    alphabet = data.get('symbols', [])
    period = int(data.get('period', 2))
    forbidden_length = int(data.get('forbiddenLength', 2))
    forbidden_words = data.get('forbiddenWords', [])

    pft = PeriodicFiniteType(alphabet, period, forbidden_length, forbidden_words)
    pft.set_adj_list()

    if data.get('essentialize', False):
        pft.update_essential()
    if data.get('minimize', False):
        pft.update_minimize()

    return pft

# ========== Flask ルート ==========

@app.route('/', methods=['GET'])
def index():
    symbols = list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return render_template('index.html', symbols=symbols)

@app.route('/get_forbidden_words', methods=['POST'])
def get_forbidden_words_route():
    symbols = request.json.get('symbols', [])
    length = int(request.json.get('length', 2))
    words = [''.join(p) for p in itertools.product(symbols, repeat=int(length))] if symbols and length else []
    return jsonify(words)

@app.route('/generate', methods=['POST'])
def generate_graph():
    try:
        data = request.json
        pft = build_pft_from_data(data)
        if data.get('essentialize', False):
            pft.update_essential()
        if data.get('minimize', False):
            pft.update_minimize()
        dot_code = pft.dot(data)

        generate_tex(dot_code)
        generate_pdf()
        convert_pdf_to_png()

        return jsonify({"image_url": f"/static/uploads/graph.png?{os.urandom(4).hex()}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download')
def download_files():
    selected_exts = request.args.getlist('ext')
    filenames = {
        'png': PNG_FILE,
        'pdf': PDF_FILE,
        'tex': TEX_FILE,
        'dot': DOT_FILE
    }

    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
        with zipfile.ZipFile(tmp, 'w') as zipf:
            for ext in selected_exts:
                fname = filenames.get(ext)
                if fname and os.path.exists(get_upload_path(fname)):
                    zipf.write(get_upload_path(fname), arcname=fname)
        tmp_path = tmp.name

    return send_file(tmp_path, mimetype='application/zip',
                     as_attachment=True, download_name='pft_graph.zip')

if __name__ == '__main__':
    app.run(debug=True)