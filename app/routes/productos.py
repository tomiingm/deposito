import os
import tempfile
import pdfplumber
import re
import uuid
from datetime import date
from flask import Blueprint, render_template, request, flash, current_app, redirect, url_for
from werkzeug.utils import secure_filename
from app.db import get_connection

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

OPCIONES_TIPO_LISTA = {
    "sin_lista": "Sin Lista",
    "famad": "FAMAD",
    "cervezas": "Cervezas",
    "jjb": "JJB Distribuciones"
}



@productos_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo_producto():
    """Formulario para crear un nuevo producto."""
    conn = get_connection()
    if not conn:
        flash("Error de conexión a la base de datos.", "error")
        return render_template('productos/nuevo.html', subcategorias=[], opciones_tipo_lista=OPCIONES_TIPO_LISTA)
        
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        # Retrieve form data
        codigo_barra = request.form.get('codigo_barra', '')
        tipo_lista = request.form.get('tipo_lista', '')
        codigo_proveedor = request.form.get('codigo_proveedor', '')
        descripcion = request.form.get('descripcion', '')
        costo_str = request.form.get('costo', '')
        ganancia_str = request.form.get('ganancia', '')
        id_subcategoria = request.form.get('id_subcategoria', '')
        
        # Validation
        errores = []
        if not descripcion:
            errores.append("La descripción es obligatoria.")
        if not tipo_lista:
            errores.append("El tipo de lista es obligatorio.")
        elif tipo_lista not in OPCIONES_TIPO_LISTA:
            errores.append("El tipo de lista seleccionado no es válido.")
        if not costo_str:
            errores.append("El costo es obligatorio.")
        if not ganancia_str:
            errores.append("La ganancia es obligatoria.")
        if not id_subcategoria:
            errores.append("La categoría es obligatoria.")
            
        try:
            costo = float(costo_str) if costo_str else 0.0
            if costo < 0:
                errores.append("El costo no puede ser negativo.")
        except ValueError:
            errores.append("El costo debe ser un valor numérico.")
            
        try:
            ganancia = float(ganancia_str) if ganancia_str else 0.0
            if ganancia < 0:
                errores.append("La ganancia no puede ser negativa.")
        except ValueError:
            errores.append("La ganancia debe ser un valor numérico.")
            
        # Image handling
        imagen_filename = None
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                # Generate unique name
                ext = os.path.splitext(filename)[1]
                unique_filename = f"{uuid.uuid4().hex}{ext}"
                
                # Make sure directory exists
                upload_folder = os.path.join(current_app.root_path, 'static', 'img', 'productos')
                os.makedirs(upload_folder, exist_ok=True)
                
                file_path = os.path.join(upload_folder, unique_filename)
                file.save(file_path)
                imagen_filename = f"img/productos/{unique_filename}"
                
        # Handle warnings (existing barcode)
        if codigo_barra:
            cursor.execute("SELECT id_producto FROM producto WHERE codigo_barra = %s", (codigo_barra,))
            if cursor.fetchone():
                flash(f"Advertencia: Ya existe un producto con el código de barra {codigo_barra}.", "warning")
                
        if errores:
            for error in errores:
                flash(error, "error")
            # Need to fetch subcategories again for the form
            cursor.execute("SELECT id_subcategoria, nombre FROM subcategoria ORDER BY nombre")
            subcategorias = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('productos/nuevo.html', subcategorias=subcategorias, form_data=request.form, opciones_tipo_lista=OPCIONES_TIPO_LISTA)
            
        # Insert into DB
        try:
            insert_query = """
                INSERT INTO producto 
                (codigo_barra, descripcion, costo, ganancia, stock, tipo_lista, imprimir, codigo_proveedor, fecha_ult_modificacion, imagen, id_subcategoria)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            # Default values
            stock = 1
            imprimir = 1
            fecha_ult_modificacion = date.today()
            
            cursor.execute(insert_query, (
                codigo_barra if codigo_barra else None,
                descripcion,
                costo,
                ganancia,
                stock,
                tipo_lista if tipo_lista != "sin_lista" else None,
                imprimir,
                codigo_proveedor if codigo_proveedor else None,
                fecha_ult_modificacion,
                imagen_filename,
                id_subcategoria
            ))
            conn.commit()
            flash("Producto guardado exitosamente.", "success")
            
        except Exception as e:
            conn.rollback()
            flash(f"Error al guardar el producto en la base de datos: {str(e)}", "error")
            # Fallback to render form with data
            cursor.execute("SELECT id_subcategoria, nombre FROM subcategoria ORDER BY nombre")
            subcategorias = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('productos/nuevo.html', subcategorias=subcategorias, form_data=request.form, opciones_tipo_lista=OPCIONES_TIPO_LISTA)
            
        # Success, clear form (redirect to GET)
        cursor.close()
        conn.close()
        return redirect(url_for('productos.nuevo_producto'))
        
    # GET request
    try:
        cursor.execute("SELECT id_subcategoria, nombre FROM subcategoria ORDER BY nombre")
        subcategorias = cursor.fetchall()
    except Exception as e:
        flash(f"Error al cargar categorías: {str(e)}", "error")
        subcategorias = []
        
    cursor.close()
    conn.close()
    return render_template('productos/nuevo.html', subcategorias=subcategorias, form_data={}, opciones_tipo_lista=OPCIONES_TIPO_LISTA)


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
