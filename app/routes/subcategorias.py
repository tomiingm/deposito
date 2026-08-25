from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.db import get_connection

subcategorias_bp = Blueprint('subcategorias', __name__)


def ensure_subcategorias_orden(cursor, conn):
    """
    Verifica si existen subcategorías con 'orden' nulo.
    Normaliza el campo 'orden' asignando números secuenciales (1, 2, 3...) por cada categoría.
    """
    try:
        cursor.execute("SELECT COUNT(*) AS total_null FROM subcategoria WHERE orden IS NULL")
        res = cursor.fetchone()
        if res and res['total_null'] > 0:
            cursor.execute("SELECT DISTINCT id_categoria FROM subcategoria")
            cats = cursor.fetchall()
            for cat in cats:
                id_cat = cat['id_categoria']
                if id_cat is not None:
                    cursor.execute("""
                        SELECT id_subcategoria 
                        FROM subcategoria 
                        WHERE id_categoria = %s 
                        ORDER BY COALESCE(orden, 999999), id_subcategoria ASC
                    """, (id_cat,))
                else:
                    cursor.execute("""
                        SELECT id_subcategoria 
                        FROM subcategoria 
                        WHERE id_categoria IS NULL 
                        ORDER BY COALESCE(orden, 999999), id_subcategoria ASC
                    """)
                subs = cursor.fetchall()
                for idx, s in enumerate(subs, start=1):
                    cursor.execute(
                        "UPDATE subcategoria SET orden = %s WHERE id_subcategoria = %s",
                        (idx, s['id_subcategoria'])
                    )
            conn.commit()
    except Exception:
        conn.rollback()


@subcategorias_bp.route('/nueva', methods=['GET', 'POST'])
def nueva_subcategoria():
    """Formulario para dar de alta una nueva subcategoría."""
    conn = get_connection()
    if not conn:
        flash("Error de conexión a la base de datos.", "error")
        return render_template('subcategorias/nueva_subcategoria.html', categorias=[], form_data={})

    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        id_categoria = request.form.get('id_categoria', '').strip()
        nombre = request.form.get('nombre', '').strip()
        imprimir = 1 if request.form.get('imprimir') else 0

        errores = []
        if not id_categoria:
            errores.append("Debe seleccionar una categoría.")
        if not nombre:
            errores.append("El nombre de la subcategoría es obligatorio.")
        if len(nombre) > 45:
            errores.append("El nombre no puede superar los 45 caracteres.")

        # Validar nombre único (case-insensitive)
        if nombre and not errores:
            cursor.execute(
                "SELECT id_subcategoria FROM subcategoria WHERE LOWER(nombre) = LOWER(%s)",
                (nombre,)
            )
            if cursor.fetchone():
                errores.append(f"Ya existe una subcategoría con el nombre '{nombre}'.")

        if errores:
            for error in errores:
                flash(error, "error")
            cursor.execute("SELECT id_categoria, descripcion FROM categoria ORDER BY descripcion")
            categorias = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template(
                'subcategorias/nueva_subcategoria.html',
                categorias=categorias,
                form_data=request.form
            )

        # Insertar con el siguiente orden dentro de la categoría
        try:
            cursor.execute(
                "SELECT COALESCE(MAX(orden), 0) + 1 AS next_orden FROM subcategoria WHERE id_categoria = %s",
                (id_categoria,)
            )
            next_ord_row = cursor.fetchone()
            next_orden = next_ord_row['next_orden'] if next_ord_row else 1

            cursor.execute(
                "INSERT INTO subcategoria (nombre, imprimir, id_categoria, orden) VALUES (%s, %s, %s, %s)",
                (nombre, imprimir, id_categoria, next_orden)
            )
            conn.commit()
            flash(f"Subcategoría '{nombre}' creada exitosamente.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Error al guardar la subcategoría: {str(e)}", "error")
            cursor.execute("SELECT id_categoria, descripcion FROM categoria ORDER BY descripcion")
            categorias = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template(
                'subcategorias/nueva_subcategoria.html',
                categorias=categorias,
                form_data=request.form
            )

        cursor.close()
        conn.close()
        return redirect(url_for('subcategorias.nueva_subcategoria'))

    # GET
    try:
        cursor.execute("SELECT id_categoria, descripcion FROM categoria ORDER BY descripcion")
        categorias = cursor.fetchall()
    except Exception as e:
        flash(f"Error al cargar categorías: {str(e)}", "error")
        categorias = []

    cursor.close()
    conn.close()
    return render_template('subcategorias/nueva_subcategoria.html', categorias=categorias, form_data={})


@subcategorias_bp.route('/')
def listar_subcategorias():
    """Grilla de subcategorías con pestañas por categoría padre, paginación (40 items), orden y productos."""
    query = request.args.get('q', '').strip()
    id_categoria_filtro = request.args.get('id_categoria', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 40

    conn = get_connection()
    if not conn:
        flash("Error de conexión a la base de datos.", "error")
        return render_template(
            'subcategorias/listar.html',
            subcategorias=[], categorias=[],
            query=query, id_categoria_filtro=id_categoria_filtro,
            page=1, total_pages=1, total_items=0, per_page=per_page,
            total_general=0
        )

    cursor = conn.cursor(dictionary=True)

    try:
        # Asegurar que todas las subcategorías tengan un número de orden asignado
        ensure_subcategorias_orden(cursor, conn)

        # Categorías con conteo para las pestañas ordenadas por menor id_categoria
        cursor.execute("""
            SELECT c.id_categoria, c.descripcion, COUNT(s.id_subcategoria) AS total_subcategorias
            FROM categoria c
            LEFT JOIN subcategoria s ON s.id_categoria = c.id_categoria
            GROUP BY c.id_categoria, c.descripcion
            ORDER BY c.id_categoria ASC
        """)
        categorias = cursor.fetchall()

        # Si no se pasó categoría por URL, se selecciona como tab principal la que tenga menor id_categoria
        if not id_categoria_filtro and categorias:
            cat_principal = min(categorias, key=lambda x: x['id_categoria'])
            id_categoria_filtro = str(cat_principal['id_categoria'])

        # Total general de subcategorías registradas
        cursor.execute("SELECT COUNT(*) AS total FROM subcategoria")
        tot_gen_row = cursor.fetchone()
        total_general = tot_gen_row['total'] if tot_gen_row else 0

        # Filtros
        conditions = []
        params = []

        if query:
            conditions.append("(s.nombre LIKE %s)")
            params.append(f"%{query}%")

        if id_categoria_filtro:
            conditions.append("s.id_categoria = %s")
            params.append(id_categoria_filtro)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Conteo para paginación
        count_sql = f"""
            SELECT COUNT(DISTINCT s.id_subcategoria) AS total
            FROM subcategoria s
            LEFT JOIN categoria c ON c.id_categoria = s.id_categoria
            WHERE {where_clause}
        """
        cursor.execute(count_sql, params)
        count_row = cursor.fetchone()
        total_items = count_row['total'] if count_row else 0

        total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1
        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages

        offset = (page - 1) * per_page

        # Obtener subcategorías ordenadas por orden y nombre
        sql = f"""
            SELECT s.id_subcategoria, s.nombre, s.imprimir, s.id_categoria, s.orden,
                   c.descripcion AS categoria_nombre,
                   COUNT(p.id_producto) AS total_productos
            FROM subcategoria s
            LEFT JOIN categoria c ON c.id_categoria = s.id_categoria
            LEFT JOIN producto p ON p.id_subcategoria = s.id_subcategoria AND p.activo = 1
            WHERE {where_clause}
            GROUP BY s.id_subcategoria, s.nombre, s.imprimir, s.id_categoria, s.orden, c.descripcion
            ORDER BY c.descripcion ASC, s.orden ASC, s.nombre ASC
            LIMIT %s OFFSET %s
        """

        select_params = params + [per_page, offset]
        cursor.execute(sql, select_params)
        subcategorias = cursor.fetchall()

        # Determinar primer y último elemento de cada categoría para habilitar/deshabilitar flechas
        cursor.execute("""
            SELECT id_categoria, MIN(orden) as min_orden, MAX(orden) as max_orden, COUNT(*) as cat_count
            FROM subcategoria
            GROUP BY id_categoria
        """)
        limits_raw = cursor.fetchall()
        limits = {row['id_categoria']: row for row in limits_raw}

        for s in subcategorias:
            cat_info = limits.get(s['id_categoria'])
            if cat_info:
                s['is_first'] = (s['orden'] == cat_info['min_orden'])
                s['is_last'] = (s['orden'] == cat_info['max_orden'])
                s['cat_count'] = cat_info['cat_count']
            else:
                s['is_first'] = True
                s['is_last'] = True
                s['cat_count'] = 1

    except Exception as e:
        flash(f"Error al cargar subcategorías: {str(e)}", "error")
        subcategorias = []
        categorias = []
        total_items = 0
        total_pages = 1
        total_general = 0

    cursor.close()
    conn.close()

    return render_template(
        'subcategorias/listar.html',
        subcategorias=subcategorias,
        categorias=categorias,
        query=query,
        id_categoria_filtro=id_categoria_filtro,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        per_page=per_page,
        total_general=total_general
    )


@subcategorias_bp.route('/editar/<int:id_subcategoria>', methods=['GET', 'POST'])
def editar_subcategoria(id_subcategoria):
    """Formulario de edición de una subcategoría existente."""
    conn = get_connection()
    if not conn:
        flash("Error de conexión a la base de datos.", "error")
        return redirect(url_for('subcategorias.listar_subcategorias'))

    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        id_categoria = request.form.get('id_categoria', '').strip()
        nombre = request.form.get('nombre', '').strip()
        imprimir = 1 if request.form.get('imprimir') else 0

        errores = []
        if not id_categoria:
            errores.append("Debe seleccionar una categoría.")
        if not nombre:
            errores.append("El nombre de la subcategoría es obligatorio.")
        if len(nombre) > 45:
            errores.append("El nombre no puede superar los 45 caracteres.")

        # Validar unicidad excluyendo el registro actual
        if nombre and not errores:
            cursor.execute(
                "SELECT id_subcategoria FROM subcategoria WHERE LOWER(nombre) = LOWER(%s) AND id_subcategoria != %s",
                (nombre, id_subcategoria)
            )
            if cursor.fetchone():
                errores.append(f"Ya existe otra subcategoría con el nombre '{nombre}'.")

        if errores:
            for error in errores:
                flash(error, "error")
        else:
            try:
                cursor.execute(
                    "UPDATE subcategoria SET nombre = %s, imprimir = %s, id_categoria = %s WHERE id_subcategoria = %s",
                    (nombre, imprimir, id_categoria, id_subcategoria)
                )
                conn.commit()
                flash(f"Subcategoría '{nombre}' actualizada exitosamente.", "success")
                cursor.close()
                conn.close()
                return redirect(url_for('subcategorias.listar_subcategorias'))
            except Exception as e:
                conn.rollback()
                flash(f"Error al actualizar la subcategoría: {str(e)}", "error")

    # GET or validation failed: load data
    try:
        cursor.execute("SELECT * FROM subcategoria WHERE id_subcategoria = %s", (id_subcategoria,))
        subcategoria = cursor.fetchone()

        if not subcategoria:
            flash("Subcategoría no encontrada.", "error")
            cursor.close()
            conn.close()
            return redirect(url_for('subcategorias.listar_subcategorias'))

        cursor.execute("SELECT id_categoria, descripcion FROM categoria ORDER BY descripcion")
        categorias = cursor.fetchall()

    except Exception as e:
        flash(f"Error al cargar datos: {str(e)}", "error")
        cursor.close()
        conn.close()
        return redirect(url_for('subcategorias.listar_subcategorias'))

    cursor.close()
    conn.close()

    return render_template(
        'subcategorias/editar_subcategoria.html',
        subcategoria=subcategoria,
        categorias=categorias
    )


@subcategorias_bp.route('/api/eliminar/<int:id_subcategoria>', methods=['POST'])
def eliminar_subcategoria_api(id_subcategoria):
    """Elimina una subcategoría. Primero desasocia los productos (id_subcategoria = NULL)."""
    conn = get_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Error de conexión a la base de datos.'}), 500

    cursor = conn.cursor()
    try:
        # Desasociar productos
        cursor.execute(
            "UPDATE producto SET id_subcategoria = NULL WHERE id_subcategoria = %s",
            (id_subcategoria,)
        )
        # Eliminar subcategoría
        cursor.execute(
            "DELETE FROM subcategoria WHERE id_subcategoria = %s",
            (id_subcategoria,)
        )
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@subcategorias_bp.route('/api/productos/<int:id_subcategoria>')
def productos_subcategoria_api(id_subcategoria):
    """Devuelve la lista de productos activos de una subcategoría (JSON)."""
    conn = get_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Error de conexión a la base de datos.'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT id_producto, descripcion, costo, ganancia
               FROM producto
               WHERE id_subcategoria = %s AND activo = 1
               ORDER BY descripcion""",
            (id_subcategoria,)
        )
        productos = cursor.fetchall()

        # Convert Decimal to float for JSON serialization
        for p in productos:
            if p['costo'] is not None:
                p['costo'] = float(p['costo'])
            if p['ganancia'] is not None:
                p['ganancia'] = float(p['ganancia'])

        return jsonify({'success': True, 'productos': productos})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@subcategorias_bp.route('/api/mover-orden/<int:id_subcategoria>', methods=['POST'])
def mover_orden_api(id_subcategoria):
    """Intercambia el orden de una subcategoría con su vecina anterior o siguiente en la misma categoría."""
    data = request.get_json(silent=True) or request.form
    direccion = data.get('direccion', '').strip().lower()

    if direccion not in ('up', 'down'):
        return jsonify({'success': False, 'error': 'Dirección no válida (debe ser "up" o "down").'}), 400

    conn = get_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Error de conexión a la base de datos.'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        # Asegurar órdenes normalizados primero
        ensure_subcategorias_orden(cursor, conn)

        # Obtener subcategoría actual
        cursor.execute("SELECT id_subcategoria, id_categoria, orden FROM subcategoria WHERE id_subcategoria = %s", (id_subcategoria,))
        actual = cursor.fetchone()
        if not actual:
            return jsonify({'success': False, 'error': 'Subcategoría no encontrada.'}), 404

        id_categoria = actual['id_categoria']

        # Obtener todas las subcategorías de esta categoría ordenadas por 'orden'
        if id_categoria is not None:
            cursor.execute("""
                SELECT id_subcategoria, orden
                FROM subcategoria
                WHERE id_categoria = %s
                ORDER BY orden ASC, id_subcategoria ASC
            """, (id_categoria,))
        else:
            cursor.execute("""
                SELECT id_subcategoria, orden
                FROM subcategoria
                WHERE id_categoria IS NULL
                ORDER BY orden ASC, id_subcategoria ASC
            """)
        subs = cursor.fetchall()

        # Encontrar índice de la subcategoría actual
        idx = -1
        for i, s in enumerate(subs):
            if s['id_subcategoria'] == id_subcategoria:
                idx = i
                break

        if idx == -1:
            return jsonify({'success': False, 'error': 'Subcategoría no encontrada en su categoría.'}), 404

        target_idx = idx - 1 if direccion == 'up' else idx + 1

        if target_idx < 0 or target_idx >= len(subs):
            return jsonify({'success': True, 'message': 'Ya se encuentra en el límite de la lista.'})

        vecino = subs[target_idx]

        # Intercambiar ordenes
        cursor.execute("UPDATE subcategoria SET orden = %s WHERE id_subcategoria = %s", (vecino['orden'], actual['id_subcategoria']))
        cursor.execute("UPDATE subcategoria SET orden = %s WHERE id_subcategoria = %s", (actual['orden'], vecino['id_subcategoria']))
        conn.commit()

        return jsonify({'success': True, 'message': 'Orden actualizado correctamente.'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

