from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.db import get_connection

subcategorias_bp = Blueprint('subcategorias', __name__)


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

        # Insertar
        try:
            cursor.execute(
                "INSERT INTO subcategoria (nombre, imprimir, id_categoria) VALUES (%s, %s, %s)",
                (nombre, imprimir, id_categoria)
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
    """Grilla de subcategorías con categoría padre, productos asociados y acciones."""
    query = request.args.get('q', '').strip()
    id_categoria_filtro = request.args.get('id_categoria', '').strip()

    conn = get_connection()
    if not conn:
        flash("Error de conexión a la base de datos.", "error")
        return render_template(
            'subcategorias/listar.html',
            subcategorias=[], categorias=[],
            query=query, id_categoria_filtro=id_categoria_filtro
        )

    cursor = conn.cursor(dictionary=True)

    try:
        # Obtener subcategorías con conteo de productos
        conditions = []
        params = []

        if query:
            conditions.append("(s.nombre LIKE %s)")
            params.append(f"%{query}%")

        if id_categoria_filtro:
            conditions.append("s.id_categoria = %s")
            params.append(id_categoria_filtro)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sql = f"""
            SELECT s.id_subcategoria, s.nombre, s.imprimir, s.id_categoria,
                   c.descripcion AS categoria_nombre,
                   COUNT(p.id_producto) AS total_productos
            FROM subcategoria s
            LEFT JOIN categoria c ON c.id_categoria = s.id_categoria
            LEFT JOIN producto p ON p.id_subcategoria = s.id_subcategoria AND p.activo = 1
            WHERE {where_clause}
            GROUP BY s.id_subcategoria, s.nombre, s.imprimir, s.id_categoria, c.descripcion
            ORDER BY c.descripcion, s.nombre
        """

        cursor.execute(sql, params)
        subcategorias = cursor.fetchall()

        cursor.execute("SELECT id_categoria, descripcion FROM categoria ORDER BY descripcion")
        categorias = cursor.fetchall()

    except Exception as e:
        flash(f"Error al cargar subcategorías: {str(e)}", "error")
        subcategorias = []
        categorias = []

    cursor.close()
    conn.close()

    return render_template(
        'subcategorias/listar.html',
        subcategorias=subcategorias,
        categorias=categorias,
        query=query,
        id_categoria_filtro=id_categoria_filtro
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
