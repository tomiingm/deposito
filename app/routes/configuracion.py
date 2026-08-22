import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from app.db import get_connection

configuracion_bp = Blueprint('configuracion', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@configuracion_bp.route('/', methods=['GET', 'POST'])
def index():
    conn = get_connection()
    if not conn:
        flash("Error al conectar con la base de datos.", "error")
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Update Empresa Data
            razon_social = request.form.get('razon_social', '').strip()
            nro_telefono = request.form.get('nro_telefono', '').strip()
            
            # Handle Logo Upload
            logo_filename = None
            if 'logo' in request.files:
                file = request.files['logo']
                if file and file.filename != '':
                    if allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        
                        # Guardar el archivo en la carpeta static/img
                        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        img_dir = os.path.join(base_dir, 'static', 'img')
                        os.makedirs(img_dir, exist_ok=True)
                        
                        file_path = os.path.join(img_dir, filename)
                        file.save(file_path)
                        
                        # Solo guardamos el nombre del archivo, ya que el generador de PDF buscará en img/
                        logo_filename = filename
                    else:
                        flash("Formato de imagen no permitido para el logo.", "error")

            # Preparar SQL para Empresa
            if logo_filename:
                cursor.execute("""
                    UPDATE empresa 
                    SET razon_social = %s, nro_telefono = %s, logo = %s 
                    WHERE id_empresa = 1
                """, (razon_social, nro_telefono, logo_filename))
            else:
                cursor.execute("""
                    UPDATE empresa 
                    SET razon_social = %s, nro_telefono = %s 
                    WHERE id_empresa = 1
                """, (razon_social, nro_telefono))

            # 2. Update Categorias Data
            # First reset all to 0
            cursor.execute("UPDATE categoria SET lista_con_imagen = 0")
            
            # Then set to 1 those that were checked
            # Checkboxes send their value only if they are checked
            cat_ids = request.form.getlist('lista_con_imagen')
            if cat_ids:
                # cat_ids is a list of strings representing the IDs
                ids_str = ','.join(['%s'] * len(cat_ids))
                cursor.execute(f"UPDATE categoria SET lista_con_imagen = 1 WHERE id_categoria IN ({ids_str})", tuple(cat_ids))
            
            conn.commit()
            flash("Configuración guardada exitosamente.", "success")
            return redirect(url_for('configuracion.index'))
            
        except Exception as e:
            conn.rollback()
            flash(f"Error al guardar configuración: {str(e)}", "error")
        finally:
            cursor.close()

    # GET Request
    empresa = {}
    categorias = []
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Load Empresa
        cursor.execute("SELECT * FROM empresa WHERE id_empresa = 1")
        empresa = cursor.fetchone() or {}
        
        # Load Categorias
        cursor.execute("SELECT id_categoria, descripcion, lista_con_imagen FROM categoria ORDER BY id_categoria ASC")
        categorias = cursor.fetchall()
    except Exception as e:
        flash(f"Error al cargar configuración: {str(e)}", "error")
    finally:
        cursor.close()
        conn.close()

    return render_template('configuracion/index.html', empresa=empresa, categorias=categorias)
