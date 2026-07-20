import os
import tempfile
import pdfplumber
from flask import Blueprint, render_template, request, flash

productos_bp = Blueprint('productos', __name__)


@productos_bp.route('/nuevo')
def nuevo_producto():
    """Formulario para crear un nuevo producto."""
    return render_template('productos/nuevo.html')


@productos_bp.route('/actualizar-precios')
def actualizar_precios():
    """Página para actualizar precios desde PDF."""
    return render_template('productos/actualizar_precios.html')


@productos_bp.route('/actualizar-precios/preview', methods=['POST'])
def actualizar_precios_preview():
    """Procesa el PDF subido y extrae el texto/tablas crudos (Fase 1)."""
    if 'pdf_file' not in request.files:
        flash("No se envió ningún archivo.", "error")
        return render_template('productos/actualizar_precios.html')
        
    file = request.files['pdf_file']
    if file.filename == '':
        flash("No se seleccionó ningún archivo.", "error")
        return render_template('productos/actualizar_precios.html')
        
    if not file.filename.lower().endswith('.pdf'):
        flash("El archivo debe ser un PDF.", "error")
        return render_template('productos/actualizar_precios.html')

    fd, temp_path = tempfile.mkstemp(suffix='.pdf')
    try:
        with os.fdopen(fd, 'wb') as f:
            file.save(f)
            
        texto_extraido = []
        tablas_extraidas = []
        
        try:
            with pdfplumber.open(temp_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        texto_extraido.append(text)
                        
                    tables = page.extract_tables()
                    for table in tables:
                        tablas_extraidas.append(table)
                        
            if not texto_extraido and not tablas_extraidas:
                flash("El PDF está vacío o no contiene texto extraíble.", "error")
                
        except Exception as e:
            error_msg = str(e).lower()
            if "password" in error_msg or "encrypt" in error_msg:
                flash("El PDF está protegido con contraseña.", "error")
            else:
                flash(f"El archivo no es un PDF válido o está corrupto. ({e})", "error")
                
        return render_template(
            'productos/actualizar_precios.html',
            texto_extraido='\n---\n'.join(texto_extraido),
            tablas_extraidas=tablas_extraidas
        )
        
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@productos_bp.route('/')
def listar_productos():
    """Listado de todos los productos."""
    return render_template('productos/listar.html')


@productos_bp.route('/modificar')
def modificar_producto():
    """Formulario para modificar un producto existente."""
    return render_template('productos/modificar.html')
