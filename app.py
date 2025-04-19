import os
import subprocess
from flask import Flask, render_template, request, send_file
from itertools import product
from dot2tex import dot2tex
from src import PeriodicFiniteType

# ----------------------------------------
# 定数
# ----------------------------------------
SYMBOLS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
UPLOAD_DIR = 'static/uploads'
DOT_FILE = 'graph.dot'
PNG_FILE = 'graph.png'
TEX_FILE = 'graph.tex'
PDF_FILE = 'graph.pdf'
ZIP_FILE = 'graph_files.zip'

# ----------------------------------------
# Flaskアプリ設定
# ----------------------------------------
app = Flask(__name__)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ----------------------------------------
# ユーティリティ関数
# ----------------------------------------
def clear_uploads():
    """UPLOAD_DIR の中身をすべて削除"""
    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

def get_upload_path(filename: str) -> str:
    """UPLOAD_DIR 内のフルパスを返す"""
    return os.path.join(UPLOAD_DIR, filename)

def process_tex(tex_content: str) -> str:
    """LaTeXコードを整形（documentclass変更 & enlargethispage削除）"""
    tex_content = tex_content.replace(
        r'\documentclass{article}',
        r'\documentclass[border=5pt]{standalone}'
    )
    return '\n'.join(
        line for line in tex_content.splitlines()
        if not line.strip().startswith(r'\enlargethispage')
    )

def generate_graph_files(dot_code: str) -> None:
    """DOT, PNG, TeX, PDFファイルの生成"""
    dot_path = get_upload_path(DOT_FILE)
    with open(dot_path, 'w') as f:
        f.write(dot_code)

    # PNG生成
    png_path = get_upload_path(PNG_FILE)
    subprocess.run(['dot', '-Tpng', dot_path, '-o', png_path], check=True)

    # TeX生成
    tex_path = get_upload_path(TEX_FILE)
    with open(tex_path, 'w') as f:
        f.write(process_tex(dot2tex(dot_code)))

    # PDF生成
    subprocess.run(['pdflatex', TEX_FILE], cwd=UPLOAD_DIR, check=True)

    # ZIPファイル作成
    zip_path = get_upload_path(ZIP_FILE)
    subprocess.run([
        'zip', '-r', zip_path,
        get_upload_path(DOT_FILE),
        get_upload_path(PNG_FILE),
        get_upload_path(PDF_FILE)
    ], check=True)

# ----------------------------------------
# ルーティング
# ----------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    # フォームの初期値を設定
    alphabet = request.form.getlist('alphabet') if request.method == 'POST' else request.args.getlist('alphabet')
    if not alphabet:
        alphabet = list(SYMBOLS)[:2]  # デフォルトで最初の2つのシンボルを使用

    phase = int(request.form.get('phase', 2)) if request.method == 'POST' else int(request.args.get('phase', 2))
    f_len = int(request.form.get('f_len', 2)) if request.method == 'POST' else int(request.args.get('f_len', 2))
    fwords = request.form.getlist('fwords') if request.method == 'POST' else request.args.getlist('fwords')
    if not fwords:
        fwords = [''.join(p) for p in product(alphabet, repeat=f_len)][0:1]  # デフォルト値

    x_scale = float(request.form.get('x_scale', 1.0)) if request.method == 'POST' else float(request.args.get('x_scale', 1.0))
    y_scale = float(request.form.get('y_scale', 1.0)) if request.method == 'POST' else float(request.args.get('y_scale', 1.0))

    fword_all = [''.join(p) for p in product(alphabet, repeat=f_len)] if alphabet else []

    if request.method == "POST":
        try:
            clear_uploads()

            # PFT構築とdotコード生成
            pft = PeriodicFiniteType(phase, f_len, fwords, True)
            pft.set_adj_list(alphabet)
            dot_code = pft.dot

            generate_graph_files(dot_code)
            return send_file(get_upload_path(ZIP_FILE), as_attachment=True)

        except ValueError as e:
            return render_template('index.html', error=f"エラー: {e}", symbols=SYMBOLS,
                                   alphabet=alphabet, phase=phase, f_len=f_len,
                                   fwords=fwords, x_scale=x_scale, y_scale=y_scale, fword_all=fword_all)
        except subprocess.CalledProcessError as e:
            return render_template('index.html', error="コマンド実行エラー", symbols=SYMBOLS,
                                   alphabet=alphabet, phase=phase, f_len=f_len,
                                   fwords=fwords, x_scale=x_scale, y_scale=y_scale, fword_all=fword_all)
        except Exception as e:
            return render_template('index.html', error=f"予期せぬエラー: {e}", symbols=SYMBOLS,
                                   alphabet=alphabet, phase=phase, f_len=f_len,
                                   fwords=fwords, x_scale=x_scale, y_scale=y_scale, fword_all=fword_all)

    return render_template(
        'home/index.html',
        symbols=SYMBOLS,
        fword_all=fword_all,
        alphabet=alphabet,
        phase=phase,
        f_len=f_len,
        fwords=fwords,
        x_scale=x_scale,
        y_scale=y_scale,
        error="",
        request=request  # テンプレートで form の状態を維持するため
    )

# ----------------------------------------
# 実行
# ----------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
