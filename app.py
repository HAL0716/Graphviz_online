from flask import Flask, render_template, request, send_file
from graphviz import Source
import subprocess
import os
from dot2tex import dot2tex
from PIL import Image

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # ユーザーの入力を受け取る
        dot_code = request.form['dot_code']

        # dot形式のファイルを保存
        dot_file = 'static/uploads/graph.dot'
        with open(dot_file, 'w') as f:
            f.write(dot_code)

        # dot -> png (画像生成)
        png_file = 'static/uploads/graph.png'
        subprocess.run(['dot', '-Tpng', dot_file, '-o', png_file])

        # dot -> tex (LaTeX形式)
        tex_file = 'static/uploads/graph.tex'
        with open(tex_file, 'w') as f:
            f.write(dot2tex(dot_file))

        # tex -> pdf (LaTeXでPDF生成)
        pdf_file = 'static/uploads/graph.pdf'
        subprocess.run(['pdflatex', tex_file])

        # ファイルを圧縮してまとめる
        zip_filename = 'static/uploads/graph_files.zip'
        subprocess.run(['zip', '-r', zip_filename, png_file, tex_file, pdf_file])

        return send_file(zip_filename, as_attachment=True)

    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
