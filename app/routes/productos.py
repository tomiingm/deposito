import os
import tempfile
import pdfplumber
import re
from flask import Blueprint, render_template, request, flash

productos_bp = Blueprint('productos', __name__)

def clean_price(price_str):
    if not price_str:
        return 0.0
    # Clean "$ 1.487,76" -> 1487.76
    s = str(price_str).replace('$', '').replace(' ', '')
    # Remove dots that act as thousands separators, replace comma with dot
    s = s.replace('.', '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return 0.0

def clean_price_famad(price_str):
    # E.g. "4.591.95" -> 4591.95
    s = str(price_str).replace('.', '')
    try:
        return float(s) / 100.0
    except ValueError:
        return 0.0

def parse_texto_famad(texto_extraido):
    productos = []
    lineas_no_reconocidas = 0
    lineas_no_reconocidas_detalle = []
    
    if isinstance(texto_extraido, list):
        texto = '\n'.join(texto_extraido)
    else:
        texto = texto_extraido
        
    lineas = texto.split('\n')
    patron = re.compile(r'(\d{1,6})\s+(.*?)\s+([\d\.]+\.\d{2})(?=\s+\d{1,6}\s|\s*$|\s+(?i:Rubro:))')
    
    for linea in lineas:
        linea = linea.strip()
        if not linea or linea == '---':
            continue
            
        linea_upper = linea.upper()
        if "FAMAD S.A.S." in linea_upper or \
           "LISTADO DE PRECIOS" in linea_upper or \
           "CODIGO DESCRIPCION PRECIO" in linea_upper or \
           linea_upper.startswith("RUBRO:"):
            continue
            
        # Descartar pie de página
        if re.search(r'EMITIDO:\s*\d{2}/\d{2}/\d{4}.*P[AÁ]GINA:\s*\d+/\d+', linea_upper):
            continue
            
        matches = patron.findall(linea)
        if matches:
            for match in matches:
                codigo, descripcion, precio_str = match
                productos.append({
                    "codigo": codigo,
                    "descripcion": descripcion.strip(),
                    "precio": clean_price_famad(precio_str)
                })
        else:
            lineas_no_reconocidas += 1
            lineas_no_reconocidas_detalle.append(linea)
            
    return {
        "productos": productos,
        "lineas_no_reconocidas": lineas_no_reconocidas,
        "lineas_no_reconocidas_detalle": lineas_no_reconocidas_detalle
    }

def parse_tabla_cervezas(tablas_extraidas):
    productos = []
    # Formato: codigo, descripcion, precio
    for tabla in tablas_extraidas:
        for fila in tabla:
            if not fila or len(fila) < 3:
                continue
            codigo, descripcion, precio = fila[0], fila[1], fila[2]
            if not descripcion or not precio:
                continue
            # Skip header, preventing rows like COD. CERVEZA 
            if str(precio).lower() == 'precio' or 'código' in str(codigo).lower() or 'cod.' in str(codigo).lower() or 'cerveza' in str(descripcion).lower():
                continue
                
            productos.append({
                "codigo": str(codigo).strip() if codigo else None,
                "descripcion": str(descripcion).strip(),
                "precio": clean_price(precio)
            })
    return productos

def parse_tabla_jjb(tablas_extraidas):
    productos = []
    # Formato: nombre_1, precio_1, nombre_2, precio_2
    for tabla in tablas_extraidas:
        for fila in tabla:
            if not fila or len(fila) < 2:
                continue
                
            # Pair 1: col 0 and 1
            if len(fila) >= 2:
                desc_1, prec_1 = fila[0], fila[1]
                if desc_1 and prec_1 and str(prec_1).strip() != '':
                    if str(prec_1).strip().lower() != 'precio':
                        productos.append({
                            "codigo": None,
                            "descripcion": str(desc_1).strip(),
                            "precio": clean_price(prec_1)
                        })
                        
            # Pair 2: col 2 and 3
            if len(fila) >= 4:
                desc_2, prec_2 = fila[2], fila[3]
                if desc_2 and prec_2 and str(prec_2).strip() != '':
                    if str(prec_2).strip().lower() != 'precio':
                        productos.append({
                            "codigo": None,
                            "descripcion": str(desc_2).strip(),
                            "precio": clean_price(prec_2)
                        })

    return productos

PROVEEDORES_CONFIG = {
    "famad": ("texto", parse_texto_famad),
    "cervezas": ("tabla", parse_tabla_cervezas),
    "jjb": ("tabla", parse_tabla_jjb)
}



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
    proveedor = request.form.get('proveedor')
    
    if not proveedor or proveedor not in PROVEEDORES_CONFIG:
        flash("Debe seleccionar un proveedor válido.", "error")
        return render_template('productos/actualizar_precios.html')
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
            else:
                productos_parseados = []
                lineas_no_reconocidas = 0
                lineas_no_reconocidas_detalle = []
                tipo_formato, func_parser = PROVEEDORES_CONFIG[proveedor]
                
                if tipo_formato == "tabla":
                    productos_parseados = func_parser(tablas_extraidas)
                elif tipo_formato == "texto":
                    resultado = func_parser(texto_extraido)
                    productos_parseados = resultado.get("productos", [])
                    lineas_no_reconocidas = resultado.get("lineas_no_reconocidas", 0)
                    lineas_no_reconocidas_detalle = resultado.get("lineas_no_reconocidas_detalle", [])
                
        except Exception as e:
            error_msg = str(e).lower()
            if "password" in error_msg or "encrypt" in error_msg:
                flash("El PDF está protegido con contraseña.", "error")
            else:
                flash(f"El archivo no es un PDF válido o está corrupto. ({e})", "error")
                
        return render_template(
            'productos/actualizar_precios.html',
            texto_extraido='\n---\n'.join(texto_extraido) if 'texto_extraido' in locals() else '',
            tablas_extraidas=tablas_extraidas if 'tablas_extraidas' in locals() else [],
            productos_parseados=productos_parseados if 'productos_parseados' in locals() else [],
            lineas_no_reconocidas=lineas_no_reconocidas if 'lineas_no_reconocidas' in locals() else 0,
            lineas_no_reconocidas_detalle=lineas_no_reconocidas_detalle if 'lineas_no_reconocidas_detalle' in locals() else []
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
