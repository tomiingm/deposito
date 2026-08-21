import os
from datetime import date, datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app, send_file
from app.db import get_connection
from app.services.pdf_generator import generar_factura_pdf

facturas_bp = Blueprint('facturas', __name__)


@facturas_bp.route('/nueva', methods=['GET', 'POST'])
def nueva_factura():
    """Formulario y procesamiento para emitir una nueva factura."""
    if request.method == 'POST':
        conn = get_connection()
        if not conn:
            flash("Error al conectar con la base de datos.", "error")
            return redirect(url_for('facturas.nueva_factura'))

        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Obtener y validar fecha
            fecha_str = request.form.get('fecha', '').strip()
            if fecha_str:
                try:
                    fecha_factura = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                except ValueError:
                    fecha_factura = date.today()
            else:
                fecha_factura = date.today()

            # 2. Obtener y validar cliente
            id_cliente = request.form.get('id_cliente', '').strip()
            nuevo_cliente_nombre = request.form.get('nuevo_cliente_nombre', '').strip()

            if not id_cliente and nuevo_cliente_nombre:
                # Crear cliente nuevo al vuelo
                cursor.execute("INSERT INTO Cliente (nombre) VALUES (%s)", (nuevo_cliente_nombre,))
                id_cliente = cursor.lastrowid
            elif id_cliente:
                try:
                    id_cliente = int(id_cliente)
                except ValueError:
                    id_cliente = None

            if not id_cliente:
                flash("Debes seleccionar o ingresar un cliente válido.", "error")
                return redirect(url_for('facturas.nueva_factura'))

            # Obtener datos del cliente para el PDF
            cursor.execute("SELECT id_cliente, nombre FROM Cliente WHERE id_cliente = %s", (id_cliente,))
            cliente_db = cursor.fetchone()
            cliente_nombre = cliente_db['nombre'] if cliente_db else 'Consumidor Final'

            # 3. Procesar ítems / renglones
            # Recibimos listas de producto, cantidad, precio_unitario, descuento
            prod_ids = request.form.getlist('item_producto_id[]')
            cantidades = request.form.getlist('item_cantidad[]')
            precios = request.form.getlist('item_precio[]')
            descripciones = request.form.getlist('item_descripcion[]')
            descuentos = request.form.getlist('item_descuento[]')

            items_to_save = []
            for i in range(len(cantidades)):
                cant_str = cantidades[i].strip() if i < len(cantidades) else ''
                precio_str = precios[i].strip() if i < len(precios) else ''
                prod_id_str = prod_ids[i].strip() if i < len(prod_ids) else ''
                desc_str = descripciones[i].strip() if i < len(descripciones) else ''
                desc_pct_str = descuentos[i].strip() if i < len(descuentos) else '0'

                if not cant_str or not precio_str:
                    continue

                try:
                    cant = int(cant_str)
                    # Limpiar y convertir precio (ej. si viniera con $ o comas)
                    precio_clean = precio_str.replace('$', '').replace(' ', '').replace('.', '').replace(',', '.') if ',' in precio_str else precio_str.replace('$', '').replace(' ', '')
                    precio_u = float(precio_clean)
                except (ValueError, TypeError):
                    continue

                if cant <= 0 or precio_u == 0:
                    continue

                try:
                    desc_pct = float(desc_pct_str.replace('%', '').replace(' ', '').replace(',', '.'))
                    if desc_pct < 0:
                        desc_pct = 0.0
                    elif desc_pct > 100:
                        desc_pct = 100.0
                except (ValueError, TypeError):
                    desc_pct = 0.0

                try:
                    prod_id = int(prod_id_str) if prod_id_str else None
                except ValueError:
                    prod_id = None

                # Si no vino descripción explícita y hay prod_id, consultamos
                if not desc_str and prod_id:
                    cursor.execute("SELECT descripcion FROM producto WHERE id_producto = %s", (prod_id,))
                    p_row = cursor.fetchone()
                    if p_row:
                        desc_str = p_row['descripcion']

                if not desc_str:
                    desc_str = f"Producto #{prod_id}" if prod_id else "Artículo"

                items_to_save.append({
                    'id_producto': prod_id,
                    'descripcion': desc_str,
                    'cantidad': cant,
                    'precio_unitario': precio_u,
                    'descuento': round(desc_pct, 2)
                })

            if not items_to_save:
                flash("Debes agregar al menos un ítem con cantidad y precio válidos.", "error")
                return redirect(url_for('facturas.nueva_factura'))

            # 4. Insertar encabezado de factura
            placeholder_url = ""
            cursor.execute(
                "INSERT INTO factura (fecha, url, id_cliente) VALUES (%s, %s, %s)",
                (fecha_factura, placeholder_url, id_cliente)
            )
            id_factura = cursor.lastrowid

            # 5. Insertar renglones en item_factura
            for it in items_to_save:
                cursor.execute(
                    "INSERT INTO item_factura (id_factura, id_producto, descripcion, cantidad, precio_unitario, descuento) VALUES (%s, %s, %s, %s, %s, %s)",
                    (id_factura, it['id_producto'], it['descripcion'], it['cantidad'], it['precio_unitario'], it['descuento'])
                )

            # 6. Obtener datos de la empresa para el PDF
            cursor.execute("SELECT id_empresa, nro_telefono, razon_social, logo FROM empresa LIMIT 1")
            empresa_db = cursor.fetchone()

            # 7. Generar PDF
            factura_data = {
                'id_factura': id_factura,
                'fecha': fecha_factura
            }
            cliente_data = {
                'id_cliente': id_cliente,
                'nombre': cliente_nombre
            }

            pdf_path, pdf_url = generar_factura_pdf(
                factura_data=factura_data,
                cliente_data=cliente_data,
                items_data=items_to_save,
                empresa_data=empresa_db
            )

            # 8. Actualizar URL del PDF en la tabla factura
            cursor.execute(
                "UPDATE factura SET url = %s WHERE id_factura = %s",
                (pdf_url, id_factura)
            )

            conn.commit()
            flash(f"¡Factura Nº {id_factura:05d} creada con éxito!", "success")
            return redirect(url_for('facturas.listar_facturas', created_id=id_factura, pdf_url=pdf_url))

        except Exception as e:
            conn.rollback()
            flash(f"Error al guardar la factura: {str(e)}", "error")
            return redirect(url_for('facturas.nueva_factura'))
        finally:
            cursor.close()
            conn.close()

    # GET: Cargar datos para el formulario
    conn = get_connection()
    clientes = []
    productos = []
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id_cliente, nombre FROM Cliente WHERE activo = 1 ORDER BY nombre ASC")
            clientes = cursor.fetchall()

            cursor.execute("""
                SELECT id_producto, codigo_barra, descripcion, costo, ganancia, stock, codigo_proveedor
                FROM producto
                ORDER BY descripcion ASC
            """)
            productos = cursor.fetchall()
            for p in productos:
                costo = float(p['costo']) if p['costo'] is not None else 0.0
                ganancia = float(p['ganancia']) if p['ganancia'] is not None else 0.0
                precio_sug = costo * (1.0 + ganancia / 100.0)
                p['precio_sugerido'] = round(precio_sug, 2)
        except Exception as e:
            flash(f"Error al cargar clientes y productos: {str(e)}", "error")
        finally:
            cursor.close()
            conn.close()

    hoy = date.today().strftime('%Y-%m-%d')
    return render_template(
        'facturas/nueva.html',
        hoy=hoy,
        clientes=clientes,
        productos=productos
    )


@facturas_bp.route('/api/clientes/nuevo', methods=['POST'])
def api_nuevo_cliente():
    """API para registrar un cliente en tiempo real desde el formulario."""
    data = request.get_json(silent=True) or request.form
    nombre = data.get('nombre', '').strip()

    if not nombre:
        return jsonify({'success': False, 'error': 'El nombre del cliente es obligatorio.'}), 400

    conn = get_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Error de conexión a la base de datos.'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("INSERT INTO Cliente (nombre) VALUES (%s)", (nombre,))
        conn.commit()
        new_id = cursor.lastrowid
        return jsonify({
            'success': True,
            'cliente': {
                'id_cliente': new_id,
                'nombre': nombre
            }
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@facturas_bp.route('/')
def listar_facturas():
    """Listado de todas las facturas emitidas."""
    query = request.args.get('q', '').strip()
    fecha_desde = request.args.get('fecha_desde', '').strip()
    fecha_hasta = request.args.get('fecha_hasta', '').strip()
    created_id = request.args.get('created_id', '').strip()
    pdf_url = request.args.get('pdf_url', '').strip()

    conn = get_connection()
    facturas = []
    total_facturado = 0.0
    cantidad_facturas = 0

    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            sql = """
                SELECT 
                    f.id_factura, 
                    f.fecha, 
                    f.url, 
                    f.id_cliente,
                    c.nombre AS cliente_nombre,
                    COUNT(i.id_item_factura) AS total_items,
                    COALESCE(SUM(i.cantidad * i.precio_unitario * (1.0 - COALESCE(i.descuento, 0) / 100.0)), 0) AS total_monto
                FROM factura f
                LEFT JOIN Cliente c ON f.id_cliente = c.id_cliente
                LEFT JOIN item_factura i ON f.id_factura = i.id_factura
                WHERE 1=1
            """
            params = []

            if query:
                sql += " AND (c.nombre LIKE %s OR CAST(f.id_factura AS CHAR) LIKE %s)"
                like = f"%{query}%"
                params.extend([like, like])

            if fecha_desde:
                sql += " AND f.fecha >= %s"
                params.append(fecha_desde)

            if fecha_hasta:
                sql += " AND f.fecha <= %s"
                params.append(fecha_hasta)

            sql += " GROUP BY f.id_factura, f.fecha, f.url, f.id_cliente, c.nombre ORDER BY f.id_factura DESC"

            cursor.execute(sql, params)
            facturas = cursor.fetchall()
            
            for f in facturas:
                monto = float(f['total_monto']) if f['total_monto'] is not None else 0.0
                f['total_monto'] = monto
                total_facturado += monto

            cantidad_facturas = len(facturas)

        except Exception as e:
            flash(f"Error al obtener las facturas: {str(e)}", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template(
        'facturas/listar.html',
        facturas=facturas,
        total_facturado=total_facturado,
        cantidad_facturas=cantidad_facturas,
        query=query,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        created_id=created_id,
        pdf_url=pdf_url
    )


@facturas_bp.route('/<int:id_factura>/pdf')
def ver_pdf(id_factura):
    """Visualizar o regenerar el PDF de una factura."""
    conn = get_connection()
    if not conn:
        flash("Error al conectar con la base de datos.", "error")
        return redirect(url_for('facturas.listar_facturas'))

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id_factura, fecha, url, id_cliente FROM factura WHERE id_factura = %s", (id_factura,))
        factura = cursor.fetchone()
        if not factura:
            flash("La factura solicitada no existe.", "error")
            return redirect(url_for('facturas.listar_facturas'))

        cursor.execute("SELECT id_cliente, nombre FROM Cliente WHERE id_cliente = %s", (factura['id_cliente'],))
        cliente = cursor.fetchone()

        cursor.execute("""
            SELECT i.id_item_factura, i.id_producto, i.cantidad, i.precio_unitario, i.descuento,
                   COALESCE(NULLIF(TRIM(i.descripcion), ''), p.descripcion, 'Artículo') AS descripcion
            FROM item_factura i
            LEFT JOIN producto p ON i.id_producto = p.id_producto
            WHERE i.id_factura = %s
        """, (id_factura,))
        items = cursor.fetchall()

        cursor.execute("SELECT id_empresa, nro_telefono, razon_social, logo FROM empresa LIMIT 1")
        empresa = cursor.fetchone()

        pdf_path, pdf_url = generar_factura_pdf(
            factura_data=factura,
            cliente_data=cliente,
            items_data=items,
            empresa_data=empresa
        )

        return send_file(pdf_path, mimetype='application/pdf', as_attachment=False, download_name=f"factura_{id_factura}.pdf")

    except Exception as e:
        flash(f"Error al cargar el PDF: {str(e)}", "error")
        return redirect(url_for('facturas.listar_facturas'))
    finally:
        cursor.close()
        conn.close()
