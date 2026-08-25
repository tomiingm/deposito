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
    tab = request.args.get('tab', 'general').strip().lower()
    if tab not in ('general', 'listas'):
        tab = 'general'

    conn = get_connection()
    if not conn:
        flash("Error al conectar con la base de datos.", "error")
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        tab = request.form.get('active_tab', tab).strip().lower()
        if tab not in ('general', 'listas'):
            tab = 'general'

        cursor = conn.cursor(dictionary=True)
        try:
            if tab == 'general' or 'razon_social' in request.form:
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

            if tab == 'listas' or 'lista_form_submitted' in request.form:
                # 2. Update Categorias Data
                cursor.execute("UPDATE categoria SET lista_con_imagen = 0")
                
                cat_ids = request.form.getlist('lista_con_imagen')
                if cat_ids:
                    ids_str = ','.join(['%s'] * len(cat_ids))
                    cursor.execute(f"UPDATE categoria SET lista_con_imagen = 1 WHERE id_categoria IN ({ids_str})", tuple(cat_ids))
            
            conn.commit()
            flash("Configuración guardada exitosamente.", "success")
            return redirect(url_for('configuracion.index', tab=tab))
            
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

    return render_template('configuracion/index.html', empresa=empresa, categorias=categorias, active_tab=tab)

