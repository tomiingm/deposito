from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.db import get_connection

clientes_bp = Blueprint('clientes', __name__)


@clientes_bp.route('/')
def listar_clientes():
    """Listado de clientes con búsqueda, ordenamiento, pestañas de activos/dados de baja y métricas."""
    query = request.args.get('q', '').strip()
    estado = request.args.get('estado', 'activos').strip().lower()
    orden = request.args.get('orden', 'nombre_asc').strip().lower()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    activo_val = 1 if estado != 'inactivos' else 0

    ordenes_validos = {
        'nombre_asc': 'c.nombre ASC',
        'nombre_desc': 'c.nombre DESC',
        'total_asc': 'total_facturado ASC, c.nombre ASC',
        'total_desc': 'total_facturado DESC, c.nombre ASC',
        'id_asc': 'c.id_cliente ASC',
        'id_desc': 'c.id_cliente DESC'
    }
    order_clause = ordenes_validos.get(orden, 'c.nombre ASC')

    conn = get_connection()
    if not conn:
        flash("Error al conectar con la base de datos.", "error")
        return render_template(
            'clientes/listar.html',
            clientes=[],
            query=query,
            estado=estado,
            orden=orden,
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

        # 3. Consulta de clientes con métricas de facturación y ordenamiento dinámico
        sql = f"""
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

        sql += f" GROUP BY c.id_cliente, c.nombre, c.telefono, c.activo ORDER BY {order_clause} LIMIT %s OFFSET %s"
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
        orden=orden,
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


@clientes_bp.route('/api/<int:id_cliente>/facturas')
def api_facturas_cliente(id_cliente):
    """Obtiene los comprobantes de un cliente paginados (por defecto 5 por página) para el desplegable."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 5

    offset = (page - 1) * per_page

    conn = get_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Error de conexión a la base de datos.'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        # Verificar cliente
        cursor.execute("SELECT id_cliente, nombre, telefono, activo FROM cliente WHERE id_cliente = %s", (id_cliente,))
        cliente = cursor.fetchone()
        if not cliente:
            return jsonify({'success': False, 'error': 'Cliente no encontrado.'}), 404

        # Contar total de comprobantes
        cursor.execute("SELECT COUNT(*) AS total FROM factura WHERE id_cliente = %s", (id_cliente,))
        total_items = cursor.fetchone()['total']

        total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1
        if page > total_pages and total_pages > 0:
            page = total_pages
            offset = (page - 1) * per_page

        # Obtener comprobantes con items y totales calculados
        sql = """
            SELECT 
                f.id_factura,
                f.fecha,
                f.url,
                COALESCE(NULLIF(f.estado, ''), 'Sin enviar') AS estado,
                COUNT(i.id_item_factura) AS total_items,
                COALESCE(SUM(i.cantidad * i.precio_unitario * (1.0 - COALESCE(i.descuento, 0) / 100.0)), 0) AS total_monto
            FROM factura f
            LEFT JOIN item_factura i ON f.id_factura = i.id_factura
            WHERE f.id_cliente = %s
            GROUP BY f.id_factura, f.fecha, f.url, f.estado
            ORDER BY f.fecha DESC, f.id_factura DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(sql, (id_cliente, per_page, offset))
        facturas = cursor.fetchall()

        facturas_list = []
        for f in facturas:
            monto = float(f['total_monto']) if f['total_monto'] is not None else 0.0
            fecha_str = f['fecha'].strftime('%d/%m/%Y') if f.get('fecha') else '-'
            facturas_list.append({
                'id_factura': f['id_factura'],
                'numero_formateado': f"00001-{f['id_factura']:08d}",
                'fecha': fecha_str,
                'estado': f['estado'],
                'total_items': f['total_items'],
                'total_monto': monto,
                'total_monto_formateado': f"$ {monto:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                'url_pdf': url_for('facturas.ver_pdf', id_factura=f['id_factura']),
                'url_editar': url_for('facturas.editar_factura', id_factura=f['id_factura']),
                'url_duplicar': url_for('facturas.nueva_factura', duplicar_id=f['id_factura']),
                'es_editable': (f['estado'] == 'Sin enviar')
            })

        return jsonify({
            'success': True,
            'cliente': {
                'id_cliente': cliente['id_cliente'],
                'nombre': cliente['nombre'],
                'telefono': cliente['telefono'] or ''
            },
            'facturas': facturas_list,
            'total_items': total_items,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

