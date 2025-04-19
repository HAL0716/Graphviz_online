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
    if request.method == "POST":
        try:
            clear_uploads()

            # フォームから値取得
            alphabet = request.form.getlist('alphabet')  # フォームから選択されたシンボル
            if not alphabet:  # alphabetが空の場合
                alphabet = list(SYMBOLS)[:2]  # デフォルトで最初の2つのシンボルを使用

            phase = int(request.form['phase']) if request.form.get('phase') else 2  # デフォルト値 2
            f_len = int(request.form['f_len']) if request.form.get('f_len') else 2  # デフォルト値 2
            fwords = request.form.getlist('fwords')
            if not fwords:  # fwordsが空の場合、f_lenに基づいて最初の禁止語を設定
                fwords = [''.join(p) for p in product(alphabet, repeat=f_len)][0:1]

            x_scale = float(request.form['x_scale']) if request.form.get('x_scale') else 1.0  # デフォルト値 1.0
            y_scale = float(request.form['y_scale']) if request.form.get('y_scale') else 1.0  # デフォルト値 1.0

            # PFT構築とdotコード生成
            pft = PeriodicFiniteType(phase, f_len, fwords, True)
            pft.set_adj_list(alphabet)
            dot_code = pft.dot

            generate_graph_files(dot_code)
            return send_file(get_upload_path(ZIP_FILE), as_attachment=True)

        except ValueError as e:
            return render_template('index.html', error=f"エラー: {e}", symbols=SYMBOLS)
        except subprocess.CalledProcessError as e:
            return render_template('index.html', error="コマンド実行エラー", symbols=SYMBOLS)
        except Exception as e:
            return render_template('index.html', error=f"予期せぬエラー: {e}", symbols=SYMBOLS)

    # GETリクエスト時の処理
    alphabet = request.args.getlist('alphabet')  # URLパラメータの値を取得（GETリクエスト）
    if not alphabet:
        alphabet = list(SYMBOLS)[:2]  # デフォルトで最初の2つのシンボルを使用

    phase = int(request.args.get('phase', 2))  # phaseのデフォルト値を設定
    f_len = int(request.args.get('f_len', 2))  # f_lenのデフォルト値を設定
    fword_all = [''.join(p) for p in product(alphabet, repeat=f_len)] if alphabet else []

    # fwordsのデフォルト値として最初の禁止語を1つ選択
    fwords = [''.join(p) for p in product(alphabet, repeat=f_len)][0:1]

    x_scale = float(request.args.get('x_scale', 1.0))  # x_scaleのデフォルト値を設定
    y_scale = float(request.args.get('y_scale', 1.0))  # y_scaleのデフォルト値を設定

    return render_template(
        'index.html',
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
