import os
import subprocess
import itertools
import tempfile
import zipfile
from flask import Flask, render_template, request, send_file, jsonify
from pdf2image import convert_from_bytes
from dot2tex import dot2tex
from src import PeriodicFiniteType
import json

# 初期化
app = Flask(__name__)
UPLOAD_DIR = 'static/uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ファイル名定義
PNG_FILE = 'graph.png'
TEX_FILE = 'graph.tex'
PDF_FILE = 'graph.pdf'
DOT_FILE = 'graph.dot'

# 設定ファイル読み込み
def load_input_values():
    with open('input_values.json', 'r') as f:
        return json.load(f)

input_values = load_input_values()

# 入力のバリデーション関数
def check_condition(condition, error_message):
    """指定された条件がTrueでなければエラーメッセージを投げる"""
    if not condition:
        raise ValueError(error_message)

# ========== ファイル関連ユーティリティ ==========

def get_upload_path(filename: str) -> str:
    """アップロードされたファイルのパスを取得"""
    return os.path.join(UPLOAD_DIR, filename)

def write_file(filename: str, content: str) -> None:
    """指定されたファイルに内容を書き込む"""
    with open(get_upload_path(filename), 'w') as f:
        f.write(content)

def clean_aux_files():
    """LaTeX中間ファイルを削除"""
    for ext in ['aux', 'fdb_latexmk', 'fls', 'log', 'out']:
        path = get_upload_path(f'graph.{ext}')
        if os.path.exists(path):
            os.remove(path)

# ========== LaTeX / DOT 処理系 ==========

def generate_tex(dot_code: str) -> None:
    """DOTコードからTeXを生成し、ファイルに保存"""
    def process_tex(tex_code: str) -> str:
        tex_code = tex_code.replace(r'\documentclass{article}', r'\documentclass[border=5pt]{standalone}')
        return '\n'.join(line for line in tex_code.splitlines() if not line.strip().startswith(r'\enlargethispage'))

    write_file(DOT_FILE, dot_code)
    tex_code = dot2tex(dot_code)
    write_file(TEX_FILE, process_tex(tex_code))

def generate_pdf() -> None:
    """TeXからPDFを生成"""
    result = subprocess.run(['pdflatex', TEX_FILE], cwd=UPLOAD_DIR, check=False, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"PDF生成失敗:\n{result.stderr.decode()}")

def convert_pdf_to_png() -> None:
    """PDFをPNGに変換"""
    pdf_path = get_upload_path(PDF_FILE)
    png_path = get_upload_path(PNG_FILE)

    with open(pdf_path, 'rb') as f:
        images = convert_from_bytes(f.read())
        images[0].save(png_path, 'PNG')

# ========== グラフ生成ロジック ==========

def build_pft_with_data(data: dict) -> PeriodicFiniteType:
    """データを元にPeriodicFiniteTypeを生成"""
    alphabet = data.get('symbols', [])
    period = int(data.get('period', input_values['period']['default']))
    forbidden_length = int(data.get('forbiddenLength', input_values['forbiddenLength']['default']))
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
    """ホームページ（初期設定のHTMLページ）"""
    symbols = list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return render_template('index.html', symbols=symbols, input_values=input_values)

@app.route('/get_forbidden_words', methods=['POST'])
def get_forbidden_words_route():
    """禁止語を取得するAPI"""
    try:
        data = request.json
        symbols = data.get('symbols', [])
        length = int(data.get('length', input_values['forbiddenLength']['default']))
        
        check_condition(isinstance(symbols, list), 'symbols はリスト形式で送信してください')
        check_condition(input_values['forbiddenLength']['min'] <= length <= input_values['forbiddenLength']['max'], 
                        f"length は {input_values['forbiddenLength']['min']}〜{input_values['forbiddenLength']['max']} の範囲で指定してください")

        words = [''.join(p) for p in itertools.product(symbols, repeat=length)]
        return jsonify(words)

    except (ValueError, TypeError) as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'サーバーエラー: {str(e)}'}), 500

@app.route('/generate', methods=['POST'])
def generate_graph():
    """グラフを生成するAPI"""
    try:
        data = request.json
        symbols = data.get('symbols', [])
        period = int(data.get('period', input_values['period']['default']))
        forbidden_length = int(data.get('forbiddenLength', input_values['forbiddenLength']['default']))

        check_condition(isinstance(symbols, list), 'symbols はリスト形式で送信してください')
        check_condition(input_values['period']['min'] <= period <= input_values['period']['max'], 
                        f"period は {input_values['period']['min']}〜{input_values['period']['max']} の範囲で指定してください")
        check_condition(input_values['forbiddenLength']['min'] <= forbidden_length <= input_values['forbiddenLength']['max'], 
                        f"forbiddenLength は {input_values['forbiddenLength']['min']}〜{input_values['forbiddenLength']['max']} の範囲で指定してください")

        pft = build_pft_with_data(data)
        dot_code = pft.dot(data)

        generate_tex(dot_code)
        generate_pdf()
        convert_pdf_to_png()
        clean_aux_files()

        return jsonify({"image_url": f"/static/uploads/graph.png?{os.urandom(4).hex()}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download')
def download_files():
    """生成されたファイルをダウンロードするAPI"""
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