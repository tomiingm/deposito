from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.db import get_connection

clientes_bp = Blueprint('clientes', __name__)


@clientes_bp.route('/')
def listar_clientes():
    """Listado de clientes con búsqueda, pestañas de activos/dados de baja y métricas."""
    query = request.args.get('q', '').strip()
    estado = request.args.get('estado', 'activos').strip().lower()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    activo_val = 1 if estado != 'inactivos' else 0

    conn = get_connection()
    if not conn:
        flash("Error al conectar con la base de datos.", "error")
        return render_template(
            'clientes/listar.html',
            clientes=[],
            query=query,
            estado=estado,
            page=1,
            total_pages=1,
            total_items=0,
            total_activos=0,
            total_inactivos=0
        )

    cursor = conn.cursor(dictionary=True)
    clientes = []
    total_items = 0
    total_activos = 0
    total_inactivos = 0

    try:
        # 1. Métricas globales de clientes
        cursor.execute("SELECT COUNT(*) AS c FROM cliente WHERE activo = 1")
        total_activos = cursor.fetchone()['c']

        cursor.execute("SELECT COUNT(*) AS c FROM cliente WHERE activo = 0")
        total_inactivos = cursor.fetchone()['c']

        # 2. Conteo filtrado
        count_sql = "SELECT COUNT(*) AS total FROM cliente WHERE activo = %s"
        count_params = [activo_val]

        if query:
            count_sql += " AND (nombre LIKE %s OR telefono LIKE %s OR CAST(id_cliente AS CHAR) LIKE %s)"
            like_str = f"%{query}%"
            count_params.extend([like_str, like_str, like_str])

        cursor.execute(count_sql, count_params)
        total_items = cursor.fetchone()['total']

        total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1
        if page > total_pages:
            page = total_pages
        if page < 1:
            page = 1
        offset = (page - 1) * per_page

        # 3. Consulta de clientes con métricas de facturación
        sql = """
            SELECT 
                c.id_cliente, 
                c.nombre, 
                c.telefono,
                c.activo,
                COUNT(DISTINCT f.id_factura) AS total_facturas,
                COALESCE(SUM(i.cantidad * i.precio_unitario * (1.0 - COALESCE(i.descuento, 0) / 100.0)), 0) AS total_facturado
            FROM cliente c
            LEFT JOIN factura f ON c.id_cliente = f.id_cliente
            LEFT JOIN item_factura i ON f.id_factura = i.id_factura
            WHERE c.activo = %s
        """
        select_params = [activo_val]

        if query:
            sql += " AND (c.nombre LIKE %s OR c.telefono LIKE %s OR CAST(c.id_cliente AS CHAR) LIKE %s)"
            like_str = f"%{query}%"
            select_params.extend([like_str, like_str, like_str])

        sql += " GROUP BY c.id_cliente, c.nombre, c.telefono, c.activo ORDER BY c.nombre ASC LIMIT %s OFFSET %s"
        select_params.extend([per_page, offset])

        cursor.execute(sql, select_params)
        clientes = cursor.fetchall()

        for cli in clientes:
            cli['total_facturado'] = float(cli['total_facturado']) if cli['total_facturado'] is not None else 0.0

    except Exception as e:
        flash(f"Error al obtener el listado de clientes: {str(e)}", "error")
    finally:
        cursor.close()
        conn.close()

    return render_template(
        'clientes/listar.html',
        clientes=clientes,
        query=query,
        estado=estado,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        total_activos=total_activos,
        total_inactivos=total_inactivos
    )


@clientes_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo_cliente():
    """Formulario para dar de alta un nuevo cliente."""
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        telefono = request.form.get('telefono', '').strip()

        if not nombre:
            flash("El nombre o razón social es obligatorio.", "error")
            return render_template('clientes/nuevo_cliente.html', nombre=nombre, telefono=telefono)

        if len(nombre) > 50:
            flash("El nombre no puede superar los 50 caracteres.", "error")
            return render_template('clientes/nuevo_cliente.html', nombre=nombre, telefono=telefono)

        if telefono and len(telefono) > 30:
            flash("El teléfono no puede superar los 30 caracteres.", "error")
            return render_template('clientes/nuevo_cliente.html', nombre=nombre, telefono=telefono)

        conn = get_connection()
        if not conn:
            flash("Error de conexión a la base de datos.", "error")
            return render_template('clientes/nuevo_cliente.html', nombre=nombre, telefono=telefono)

        cursor = conn.cursor(dictionary=True)
        try:
            # Comprobar si ya existe un cliente con ese nombre
            cursor.execute("SELECT id_cliente, activo FROM cliente WHERE LOWER(nombre) = LOWER(%s)", (nombre,))
            existente = cursor.fetchone()

            if existente:
                if existente['activo'] == 1:
                    flash(f"Ya existe un cliente activo con el nombre '{nombre}'.", "error")
                    return render_template('clientes/nuevo_cliente.html', nombre=nombre, telefono=telefono)
                else:
                    # Reactivar si estaba inactivo y actualizar teléfono
                    cursor.execute("UPDATE cliente SET activo = 1, telefono = %s WHERE id_cliente = %s", (telefono or None, existente['id_cliente']))
                    conn.commit()
                    flash(f"El cliente '{nombre}' estaba dado de baja y fue reactivado exitosamente.", "success")
                    return redirect(url_for('clientes.listar_clientes'))

            cursor.execute("INSERT INTO cliente (nombre, telefono, activo) VALUES (%s, %s, 1)", (nombre, telefono or None))
            conn.commit()
            new_id = cursor.lastrowid
            flash(f"¡Cliente '{nombre}' (Nº {new_id:04d}) creado con éxito!", "success")
            return redirect(url_for('clientes.listar_clientes'))

        except Exception as e:
            conn.rollback()
            flash(f"Error al guardar el cliente: {str(e)}", "error")
            return render_template('clientes/nuevo_cliente.html', nombre=nombre, telefono=telefono)
        finally:
            cursor.close()
            conn.close()

    return render_template('clientes/nuevo_cliente.html', nombre='', telefono='')


@clientes_bp.route('/editar/<int:id_cliente>', methods=['GET', 'POST'])
def editar_cliente(id_cliente):
    """Formulario para editar los datos de un cliente existente."""
    conn = get_connection()
    if not conn:
        flash("Error de conexión a la base de datos.", "error")
        return redirect(url_for('clientes.listar_clientes'))

    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        telefono = request.form.get('telefono', '').strip()

        if not nombre:
            flash("El nombre o razón social es obligatorio.", "error")
            return render_template('clientes/editar_cliente.html', cliente={'id_cliente': id_cliente, 'nombre': nombre, 'telefono': telefono})

        if len(nombre) > 50:
            flash("El nombre no puede superar los 50 caracteres.", "error")
            return render_template('clientes/editar_cliente.html', cliente={'id_cliente': id_cliente, 'nombre': nombre, 'telefono': telefono})

        if telefono and len(telefono) > 30:
            flash("El teléfono no puede superar los 30 caracteres.", "error")
            return render_template('clientes/editar_cliente.html', cliente={'id_cliente': id_cliente, 'nombre': nombre, 'telefono': telefono})

        try:
            # Comprobar duplicado con otro cliente
            cursor.execute("SELECT id_cliente FROM cliente WHERE LOWER(nombre) = LOWER(%s) AND id_cliente != %s", (nombre, id_cliente))
            if cursor.fetchone():
                flash(f"Ya existe otro cliente con el nombre '{nombre}'.", "error")
                return render_template('clientes/editar_cliente.html', cliente={'id_cliente': id_cliente, 'nombre': nombre, 'telefono': telefono})

            cursor.execute("UPDATE cliente SET nombre = %s, telefono = %s WHERE id_cliente = %s", (nombre, telefono or None, id_cliente))
            conn.commit()
            flash(f"¡Cliente Nº {id_cliente:04d} actualizado con éxito!", "success")
            return redirect(url_for('clientes.listar_clientes'))

        except Exception as e:
            conn.rollback()
            flash(f"Error al actualizar el cliente: {str(e)}", "error")
            return render_template('clientes/editar_cliente.html', cliente={'id_cliente': id_cliente, 'nombre': nombre, 'telefono': telefono})
        finally:
            cursor.close()
            conn.close()

    # GET: Cargar datos actuales
    try:
        cursor.execute("SELECT id_cliente, nombre, telefono, activo FROM cliente WHERE id_cliente = %s", (id_cliente,))
        cliente = cursor.fetchone()
        if not cliente:
            flash("El cliente solicitado no existe.", "error")
            return redirect(url_for('clientes.listar_clientes'))

        # Obtener resumen de facturas asociadas
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT f.id_factura) AS total_facturas,
                COALESCE(SUM(i.cantidad * i.precio_unitario * (1.0 - COALESCE(i.descuento, 0) / 100.0)), 0) AS total_facturado
            FROM factura f
            LEFT JOIN item_factura i ON f.id_factura = i.id_factura
            WHERE f.id_cliente = %s
        """, (id_cliente,))
        stats = cursor.fetchone()
        cliente['total_facturas'] = stats['total_facturas'] if stats else 0
        cliente['total_facturado'] = float(stats['total_facturado']) if stats and stats['total_facturado'] is not None else 0.0

        return render_template('clientes/editar_cliente.html', cliente=cliente)

    except Exception as e:
        flash(f"Error al cargar el cliente: {str(e)}", "error")
        return redirect(url_for('clientes.listar_clientes'))
    finally:
        cursor.close()
        conn.close()


@clientes_bp.route('/api/actualizar-telefono/<int:id_cliente>', methods=['POST'])
def api_actualizar_telefono(id_cliente):
    """API para actualizar o asignar rápidamente el teléfono de un cliente."""
    data = request.get_json(silent=True) or request.form
    telefono = (data.get('telefono') or '').strip()

    if telefono and len(telefono) > 30:
        return jsonify({'success': False, 'error': 'El teléfono no puede superar los 30 caracteres.'}), 400

    conn = get_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Error de conexión a la base de datos.'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("UPDATE cliente SET telefono = %s WHERE id_cliente = %s", (telefono or None, id_cliente))
        conn.commit()
        return jsonify({'success': True, 'telefono': telefono})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@clientes_bp.route('/api/eliminar/<int:id_cliente>', methods=['POST'])
def eliminar_cliente(id_cliente):
    """Baja lógica de cliente (activo = 0)."""
    conn = get_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Error de conexión a la base de datos.'}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE cliente SET activo = 0 WHERE id_cliente = %s", (id_cliente,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@clientes_bp.route('/api/reactivar/<int:id_cliente>', methods=['POST'])
def reactivar_cliente(id_cliente):
    """Reactivación de cliente (activo = 1)."""
    conn = get_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Error de conexión a la base de datos.'}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE cliente SET activo = 1 WHERE id_cliente = %s", (id_cliente,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()
