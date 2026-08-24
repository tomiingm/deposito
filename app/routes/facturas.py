import csv
import io
import math
import os
import zipfile
from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app, send_file
from app.db import get_connection
from app.services.pdf_generator import generar_factura_pdf

facturas_bp = Blueprint('facturas', __name__)

MESES_ES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
    7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}


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
    duplicar_id = request.args.get('duplicar_id', '').strip()
    cliente_duplicar = None
    items_duplicar = []

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

            if duplicar_id:
                try:
                    dup_id_int = int(duplicar_id)
                    cursor.execute("SELECT id_factura, id_cliente FROM factura WHERE id_factura = %s", (dup_id_int,))
                    fac_dup = cursor.fetchone()
                    if fac_dup:
                        cursor.execute("SELECT id_cliente, nombre FROM Cliente WHERE id_cliente = %s", (fac_dup['id_cliente'],))
                        cli_dup = cursor.fetchone()
                        if cli_dup:
                            cliente_duplicar = {
                                'id_cliente': cli_dup['id_cliente'],
                                'nombre': cli_dup['nombre']
                            }

                        cursor.execute("""
                            SELECT i.id_producto,
                                   COALESCE(NULLIF(TRIM(i.descripcion), ''), p.descripcion, 'Artículo') AS descripcion,
                                   i.cantidad,
                                   i.precio_unitario,
                                   i.descuento
                            FROM item_factura i
                            LEFT JOIN producto p ON i.id_producto = p.id_producto
                            WHERE i.id_factura = %s
                            ORDER BY i.id_item_factura ASC
                        """, (dup_id_int,))
                        raw_items = cursor.fetchall()
                        for it in raw_items:
                            items_duplicar.append({
                                'id_producto': it['id_producto'],
                                'descripcion': it['descripcion'] or '',
                                'cantidad': int(it['cantidad'] or 1),
                                'precio_unitario': float(it['precio_unitario']) if it['precio_unitario'] is not None else 0.0,
                                'descuento': float(it['descuento']) if it['descuento'] is not None else 0.0
                            })
                        flash(f"Duplicando datos de Factura Nº {dup_id_int:05d}. Al guardar se generará un nuevo comprobante.", "info")
                    else:
                        flash("La factura especificada para duplicar no fue encontrada.", "error")
                except ValueError:
                    pass

        except Exception as e:
            flash(f"Error al cargar datos del formulario: {str(e)}", "error")
        finally:
            cursor.close()
            conn.close()

    hoy = date.today().strftime('%Y-%m-%d')
    return render_template(
        'facturas/nueva.html',
        hoy=hoy,
        clientes=clientes,
        productos=productos,
        cliente_duplicar=cliente_duplicar,
        items_duplicar=items_duplicar
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
    """Listado de todas las facturas emitidas con búsqueda, filtros, estadísticas y paginación."""
    nro_factura = request.args.get('nro_factura', '').strip()
    cliente = request.args.get('cliente', '').strip()
    fecha_desde = request.args.get('fecha_desde', '').strip()
    fecha_hasta = request.args.get('fecha_hasta', '').strip()
    created_id = request.args.get('created_id', '').strip()
    pdf_url = request.args.get('pdf_url', '').strip()

    # Manejo retrocompatible si se envía 'q'
    q_legacy = request.args.get('q', '').strip()
    if q_legacy and not nro_factura and not cliente:
        if q_legacy.isdigit():
            nro_factura = q_legacy
        else:
            cliente = q_legacy

    conn = get_connection()
    facturas = []
    total_mes_actual = 0.0
    total_semana = 0.0
    cant_mes_actual = 0
    nombre_mes_actual = MESES_ES.get(date.today().month, '')

    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Estadísticas relevantes (Facturado este mes, Facturado esta semana, Comprobantes este mes)
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN f.fecha >= DATE_FORMAT(NOW(), '%Y-%m-01') THEN i.cantidad * i.precio_unitario * (1.0 - COALESCE(i.descuento, 0) / 100.0) ELSE 0 END), 0) AS total_mes,
                    COALESCE(SUM(CASE WHEN f.fecha >= DATE_SUB(CURDATE(), INTERVAL 6 DAY) THEN i.cantidad * i.precio_unitario * (1.0 - COALESCE(i.descuento, 0) / 100.0) ELSE 0 END), 0) AS total_semana,
                    COUNT(DISTINCT CASE WHEN f.fecha >= DATE_FORMAT(NOW(), '%Y-%m-01') THEN f.id_factura END) AS cant_mes
                FROM factura f
                LEFT JOIN item_factura i ON f.id_factura = i.id_factura
            """)
            stats_row = cursor.fetchone()
            if stats_row:
                total_mes_actual = float(stats_row['total_mes'] or 0.0)
                total_semana = float(stats_row['total_semana'] or 0.0)
                cant_mes_actual = int(stats_row['cant_mes'] or 0)

            # 2. Consulta de facturas filtradas
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

            if nro_factura:
                clean_nro = nro_factura.lower().replace('00001-', '').lstrip('0')
                if not clean_nro:
                    clean_nro = '0'
                sql += " AND (CAST(f.id_factura AS CHAR) LIKE %s OR f.id_factura = %s)"
                like_nro = f"%{clean_nro}%"
                params.extend([like_nro, clean_nro])

            if cliente:
                sql += " AND c.nombre LIKE %s"
                params.append(f"%{cliente}%")

            if fecha_desde:
                sql += " AND f.fecha >= %s"
                params.append(fecha_desde)

            if fecha_hasta:
                sql += " AND f.fecha <= %s"
                params.append(fecha_hasta)

            sql += " GROUP BY f.id_factura, f.fecha, f.url, f.id_cliente, c.nombre ORDER BY f.id_factura DESC"

            cursor.execute(sql, params)
            facturas_db = cursor.fetchall()
            
            for f in facturas_db:
                monto = float(f['total_monto']) if f['total_monto'] is not None else 0.0
                f['total_monto'] = monto
                facturas.append(f)

        except Exception as e:
            flash(f"Error al obtener las facturas: {str(e)}", "error")
        finally:
            cursor.close()
            conn.close()

    # 3. Paginación de 20 comprobantes por página
    PER_PAGE = 20
    total_items = len(facturas)
    total_pages = math.ceil(total_items / PER_PAGE) if total_items > 0 else 1

    try:
        page = int(request.args.get('page', 1))
    except (ValueError, TypeError):
        page = 1

    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    start_idx = (page - 1) * PER_PAGE
    end_idx = start_idx + PER_PAGE
    facturas_page = facturas[start_idx:end_idx]

    start_item = start_idx + 1 if total_items > 0 else 0
    end_item = min(end_idx, total_items)
    has_prev = page > 1
    has_next = page < total_pages

    return render_template(
        'facturas/listar.html',
        facturas=facturas_page,
        total_mes_actual=total_mes_actual,
        total_semana=total_semana,
        cant_mes_actual=cant_mes_actual,
        nombre_mes_actual=nombre_mes_actual,
        nro_factura=nro_factura,
        cliente=cliente,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        created_id=created_id,
        pdf_url=pdf_url,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        start_item=start_item,
        end_item=end_item,
        has_prev=has_prev,
        has_next=has_next
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


@facturas_bp.route('/descargar-zip', methods=['POST', 'GET'])
def descargar_zip():
    """Genera y descarga un archivo .ZIP con todos los PDFs de las facturas seleccionadas."""
    ids_str = request.args.get('ids', '') or request.form.get('ids', '')
    if not ids_str:
        flash("No seleccionaste ninguna factura para descargar.", "error")
        return redirect(url_for('facturas.listar_facturas'))

    try:
        id_list = [int(x.strip()) for x in ids_str.split(',') if x.strip().isdigit()]
    except ValueError:
        id_list = []

    if not id_list:
        flash("La lista de facturas seleccionadas no es válida.", "error")
        return redirect(url_for('facturas.listar_facturas'))

    conn = get_connection()
    if not conn:
        flash("Error de conexión a la base de datos.", "error")
        return redirect(url_for('facturas.listar_facturas'))

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id_empresa, nro_telefono, razon_social, logo FROM empresa LIMIT 1")
            empresa = cursor.fetchone()

            for id_factura in id_list:
                cursor.execute("SELECT id_factura, fecha, url, id_cliente FROM factura WHERE id_factura = %s", (id_factura,))
                fac = cursor.fetchone()
                if not fac:
                    continue

                cursor.execute("SELECT id_cliente, nombre FROM Cliente WHERE id_cliente = %s", (fac['id_cliente'],))
                cli = cursor.fetchone()

                cursor.execute("""
                    SELECT i.id_item_factura, i.id_producto, i.cantidad, i.precio_unitario, i.descuento,
                           COALESCE(NULLIF(TRIM(i.descripcion), ''), p.descripcion, 'Artículo') AS descripcion
                    FROM item_factura i
                    LEFT JOIN producto p ON i.id_producto = p.id_producto
                    WHERE i.id_factura = %s
                """, (id_factura,))
                items = cursor.fetchall()

                pdf_path, _ = generar_factura_pdf(
                    factura_data=fac,
                    cliente_data=cli,
                    items_data=items,
                    empresa_data=empresa
                )
                
                filename_in_zip = f"factura_{id_factura:05d}.pdf"
                zf.write(pdf_path, arcname=filename_in_zip)
        except Exception as e:
            flash(f"Error generando archivo ZIP: {str(e)}", "error")
            return redirect(url_for('facturas.listar_facturas'))
        finally:
            cursor.close()
            conn.close()

    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name='facturas_seleccionadas.zip'
    )


@facturas_bp.route('/exportar-csv', methods=['POST', 'GET'])
def exportar_csv():
    """Exporta un archivo CSV con el resumen de las facturas seleccionadas."""
    ids_str = request.args.get('ids', '') or request.form.get('ids', '')
    if not ids_str:
        flash("No seleccionaste ninguna factura para exportar.", "error")
        return redirect(url_for('facturas.listar_facturas'))

    try:
        id_list = [int(x.strip()) for x in ids_str.split(',') if x.strip().isdigit()]
    except ValueError:
        id_list = []

    if not id_list:
        flash("La lista de facturas seleccionadas no es válida.", "error")
        return redirect(url_for('facturas.listar_facturas'))

    conn = get_connection()
    if not conn:
        flash("Error de conexión a la base de datos.", "error")
        return redirect(url_for('facturas.listar_facturas'))

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Nro Factura', 'Fecha', 'Cliente', 'Items', 'Total ($)'])

    cursor = conn.cursor(dictionary=True)
    try:
        format_ids = ','.join(['%s'] * len(id_list))
        sql = f"""
            SELECT 
                f.id_factura, 
                f.fecha, 
                c.nombre AS cliente_nombre,
                COUNT(i.id_item_factura) AS total_items,
                COALESCE(SUM(i.cantidad * i.precio_unitario * (1.0 - COALESCE(i.descuento, 0) / 100.0)), 0) AS total_monto
            FROM factura f
            LEFT JOIN Cliente c ON f.id_cliente = c.id_cliente
            LEFT JOIN item_factura i ON f.id_factura = i.id_factura
            WHERE f.id_factura IN ({format_ids})
            GROUP BY f.id_factura, f.fecha, c.nombre
            ORDER BY f.id_factura DESC
        """
        cursor.execute(sql, id_list)
        rows = cursor.fetchall()
        for r in rows:
            fecha_str = r['fecha'].strftime('%d/%m/%Y') if r['fecha'] else ''
            monto = float(r['total_monto']) if r['total_monto'] is not None else 0.0
            monto_fmt = f"{monto:.2f}".replace('.', ',')
            writer.writerow([f"00001-{r['id_factura']:08d}", fecha_str, r['cliente_nombre'] or 'Consumidor Final', r['total_items'], monto_fmt])
    except Exception as e:
        flash(f"Error generando exportación CSV: {str(e)}", "error")
        return redirect(url_for('facturas.listar_facturas'))
    finally:
        cursor.close()
        conn.close()

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='facturas_seleccionadas.csv'
    )
