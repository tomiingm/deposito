import csv
import io
import math
import os
import platform
import subprocess
import uuid
import zipfile
from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
from app.db import get_connection
from app.services.pdf_generator import generar_factura_pdf
from app.services.whatsapp_service import WhatsAppService

facturas_bp = Blueprint('facturas', __name__)

MESES_ES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
    7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

ESTADOS_PERMITIDOS = ['Sin enviar', 'Enviada', 'Cobrada']


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

            # 4. Insertar encabezado de factura con estado por defecto 'Sin enviar'
            placeholder_url = ""
            cursor.execute(
                "INSERT INTO factura (fecha, url, id_cliente, estado) VALUES (%s, %s, %s, 'Sin enviar')",
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
                SELECT p.id_producto, p.codigo_barra, p.descripcion, p.costo, p.ganancia, p.stock, p.codigo_proveedor,
                       p.fraccionado, p.cantidad_fracciones, p.metodo_ganancia,
                       s.nombre AS subcategoria
                FROM producto p
                LEFT JOIN subcategoria s ON s.id_subcategoria = p.id_subcategoria
                WHERE (p.activo = 1 OR p.activo IS NULL)
                ORDER BY p.descripcion ASC
            """)
            productos = cursor.fetchall()
            for p in productos:
                costo = float(p['costo']) if p['costo'] is not None else 0.0
                ganancia = float(p['ganancia']) if p['ganancia'] is not None else 0.0
                p['costo'] = costo
                p['ganancia'] = ganancia
                if p.get('stock') is not None:
                    p['stock'] = float(p['stock'])
                if p.get('cantidad_fracciones') is not None:
                    p['cantidad_fracciones'] = float(p['cantidad_fracciones'])

                es_frac = bool(p.get('fraccionado')) and p.get('cantidad_fracciones') and float(p['cantidad_fracciones']) > 0
                cant_f = float(p['cantidad_fracciones']) if es_frac else 1.0
                base_costo = costo / cant_f if es_frac else costo
                metodo_g = p.get('metodo_ganancia', 1)
                if metodo_g in (0, False, '0'):
                    precio_sug = base_costo + ganancia
                else:
                    precio_sug = base_costo * (1.0 + ganancia / 100.0)
                p['precio_sugerido'] = round(precio_sug, 2)

            cursor.execute("SELECT id_subcategoria, nombre FROM subcategoria ORDER BY nombre ASC")
            subcategorias = cursor.fetchall()
            cursor.execute("SELECT id_proveedor, nombre FROM proveedor ORDER BY nombre ASC")
            proveedores = cursor.fetchall()

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
    else:
        subcategorias = []
        proveedores = []

    hoy = date.today().strftime('%Y-%m-%d')
    return render_template(
        'facturas/nueva.html',
        hoy=hoy,
        clientes=clientes,
        productos=productos,
        subcategorias=subcategorias,
        proveedores=proveedores,
        cliente_duplicar=cliente_duplicar,
        items_duplicar=items_duplicar
    )


@facturas_bp.route('/api/clientes/nuevo', methods=['POST'])
def api_nuevo_cliente():
    """API para registrar un cliente en tiempo real desde el formulario."""
    data = request.get_json(silent=True) or request.form
    nombre = data.get('nombre', '').strip()
    telefono = data.get('telefono', '').strip()

    if not nombre:
        return jsonify({'success': False, 'error': 'El nombre del cliente es obligatorio.'}), 400

    if telefono and len(telefono) > 30:
        return jsonify({'success': False, 'error': 'El teléfono no puede superar los 30 caracteres.'}), 400

    conn = get_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Error de conexión a la base de datos.'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("INSERT INTO cliente (nombre, telefono, activo) VALUES (%s, %s, 1)", (nombre, telefono or None))
        conn.commit()
        new_id = cursor.lastrowid
        return jsonify({
            'success': True,
            'cliente': {
                'id_cliente': new_id,
                'nombre': nombre,
                'telefono': telefono
            }
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@facturas_bp.route('/api/productos/nuevo', methods=['POST'])
def api_nuevo_producto():
    """API para registrar un producto nuevo en tiempo real desde el formulario de facturación."""
    data = request.get_json(silent=True) or request.form
    descripcion = (data.get('descripcion') or '').strip()
    costo_str = str(data.get('costo') or '').strip()
    ganancia_str = str(data.get('ganancia') or '').strip()
    metodo_ganancia = int(data.get('metodo_ganancia', 1))
    id_subcategoria_raw = data.get('id_subcategoria')
    codigo_barra = (data.get('codigo_barra') or '').strip() or None
    codigo_proveedor = (data.get('codigo_proveedor') or '').strip() or None
    stock_str = str(data.get('stock') or '1').strip()
    fraccionado = 1 if data.get('fraccionado') else 0
    cantidad_fracciones_str = str(data.get('cantidad_fracciones') or '').strip()

    if not descripcion:
        return jsonify({'success': False, 'error': 'La descripción del producto es obligatoria.'}), 400

    try:
        costo = float(costo_str.replace('$', '').replace(' ', '').replace(',', '.'))
        if costo < 0:
            return jsonify({'success': False, 'error': 'El costo no puede ser negativo.'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'El costo debe ser un valor numérico válido.'}), 400

    try:
        ganancia = float(ganancia_str.replace('%', '').replace(' ', '').replace(',', '.'))
        if ganancia < 0:
            return jsonify({'success': False, 'error': 'La ganancia no puede ser negativa.'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'La ganancia debe ser un valor numérico válido.'}), 400

    try:
        stock = int(float(stock_str)) if stock_str else 1
    except (ValueError, TypeError):
        stock = 1

    cantidad_fracciones = None
    if fraccionado:
        try:
            cantidad_fracciones = float(cantidad_fracciones_str.replace(',', '.'))
            if cantidad_fracciones <= 0:
                cantidad_fracciones = 1.0
        except (ValueError, TypeError):
            cantidad_fracciones = 1.0

    id_subcategoria = None
    if id_subcategoria_raw:
        try:
            id_subcategoria = int(id_subcategoria_raw)
        except (ValueError, TypeError):
            id_subcategoria = None

    conn = get_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Error de conexión a la base de datos.'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        subcat_nombre = None
        if id_subcategoria:
            cursor.execute("SELECT id_subcategoria, nombre FROM subcategoria WHERE id_subcategoria = %s", (id_subcategoria,))
            sub_row = cursor.fetchone()
            if sub_row:
                subcat_nombre = sub_row['nombre']
                id_subcategoria = sub_row['id_subcategoria']
            else:
                id_subcategoria = None

        insert_sql = """
            INSERT INTO producto 
            (codigo_barra, descripcion, costo, ganancia, stock, imprimir, codigo_proveedor, fecha_ult_modificacion, id_subcategoria, fraccionado, cantidad_fracciones, metodo_ganancia, activo)
            VALUES (%s, %s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, 1)
        """
        cursor.execute(insert_sql, (
            codigo_barra,
            descripcion,
            costo,
            ganancia,
            stock,
            codigo_proveedor,
            date.today(),
            id_subcategoria,
            fraccionado,
            cantidad_fracciones,
            metodo_ganancia
        ))
        conn.commit()
        new_prod_id = cursor.lastrowid

        # Calcular precio sugerido
        es_frac = bool(fraccionado) and cantidad_fracciones and float(cantidad_fracciones) > 0
        cant_f = float(cantidad_fracciones) if es_frac else 1.0
        base_costo = costo / cant_f if es_frac else costo
        if metodo_ganancia in (0, False, '0'):
            precio_sug = base_costo + ganancia
        else:
            precio_sug = base_costo * (1.0 + ganancia / 100.0)
        precio_sugerido = round(precio_sug, 2)

        return jsonify({
            'success': True,
            'producto': {
                'id_producto': new_prod_id,
                'descripcion': descripcion,
                'codigo_barra': codigo_barra or '',
                'codigo_proveedor': codigo_proveedor or '',
                'costo': costo,
                'ganancia': ganancia,
                'stock': stock,
                'subcategoria': subcat_nombre or '',
                'fraccionado': fraccionado,
                'cantidad_fracciones': cantidad_fracciones,
                'metodo_ganancia': metodo_ganancia,
                'precio_sugerido': precio_sugerido
            },
            'message': f"Producto '{descripcion}' creado exitosamente e incorporado al catálogo."
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@facturas_bp.route('/editar/<int:id_factura>', methods=['GET', 'POST'])
def editar_factura(id_factura):
    """Formulario y procesamiento para editar una factura existente (solo permitido si estado == 'Sin enviar')."""
    conn = get_connection()
    if not conn:
        flash("Error al conectar con la base de datos.", "error")
        return redirect(url_for('facturas.listar_facturas'))

    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Verificar existencia y estado de la factura
        cursor.execute("SELECT id_factura, fecha, url, id_cliente, COALESCE(estado, 'Sin enviar') AS estado FROM factura WHERE id_factura = %s", (id_factura,))
        factura = cursor.fetchone()
        if not factura:
            flash("La factura solicitada no existe.", "error")
            return redirect(url_for('facturas.listar_facturas'))

        # REGLA ESTRICTA: Solo se pueden editar facturas con estado 'Sin enviar'
        if factura['estado'] in ('Enviada', 'Cobrada'):
            flash(f"No es posible editar la Factura Nº 00001-{id_factura:08d} porque ya fue {factura['estado'].lower()}. Solo se permite modificar comprobantes con estado 'Sin enviar'.", "error")
            return redirect(url_for('facturas.listar_facturas'))

        if request.method == 'POST':
            # Obtener y validar fecha
            fecha_str = request.form.get('fecha', '').strip()
            if fecha_str:
                try:
                    fecha_factura = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                except ValueError:
                    fecha_factura = factura['fecha'] or date.today()
            else:
                fecha_factura = factura['fecha'] or date.today()

            # Obtener y validar cliente
            id_cliente = request.form.get('id_cliente', '').strip()
            nuevo_cliente_nombre = request.form.get('nuevo_cliente_nombre', '').strip()

            if not id_cliente and nuevo_cliente_nombre:
                cursor.execute("INSERT INTO Cliente (nombre) VALUES (%s)", (nuevo_cliente_nombre,))
                id_cliente = cursor.lastrowid
            elif id_cliente:
                try:
                    id_cliente = int(id_cliente)
                except ValueError:
                    id_cliente = None

            if not id_cliente:
                flash("Debes seleccionar o ingresar un cliente válido.", "error")
                return redirect(url_for('facturas.editar_factura', id_factura=id_factura))

            cursor.execute("SELECT id_cliente, nombre FROM Cliente WHERE id_cliente = %s", (id_cliente,))
            cliente_db = cursor.fetchone()
            cliente_nombre = cliente_db['nombre'] if cliente_db else 'Consumidor Final'

            # Procesar renglones / ítems
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
                return redirect(url_for('facturas.editar_factura', id_factura=id_factura))

            # 2. Actualizar cabecera de la factura
            cursor.execute(
                "UPDATE factura SET fecha = %s, id_cliente = %s WHERE id_factura = %s",
                (fecha_factura, id_cliente, id_factura)
            )

            # 3. Eliminar renglones anteriores e insertar los actualizados
            cursor.execute("DELETE FROM item_factura WHERE id_factura = %s", (id_factura,))
            for it in items_to_save:
                cursor.execute(
                    "INSERT INTO item_factura (id_factura, id_producto, descripcion, cantidad, precio_unitario, descuento) VALUES (%s, %s, %s, %s, %s, %s)",
                    (id_factura, it['id_producto'], it['descripcion'], it['cantidad'], it['precio_unitario'], it['descuento'])
                )

            # 4. Regenerar archivo PDF con los datos actualizados
            cursor.execute("SELECT id_empresa, nro_telefono, razon_social, logo FROM empresa LIMIT 1")
            empresa_db = cursor.fetchone()

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

            # 5. Actualizar URL del PDF
            cursor.execute("UPDATE factura SET url = %s WHERE id_factura = %s", (pdf_url, id_factura))

            conn.commit()
            flash(f"¡Factura Nº 00001-{id_factura:08d} modificada y PDF regenerado con éxito!", "success")
            return redirect(url_for('facturas.listar_facturas', created_id=id_factura, pdf_url=pdf_url))

        # GET: Cargar datos para edición
        cursor.execute("SELECT id_cliente, nombre FROM Cliente WHERE activo = 1 ORDER BY nombre ASC")
        clientes = cursor.fetchall()

        cursor.execute("""
            SELECT p.id_producto, p.codigo_barra, p.descripcion, p.costo, p.ganancia, p.stock, p.codigo_proveedor,
                   p.fraccionado, p.cantidad_fracciones, p.metodo_ganancia,
                   s.nombre AS subcategoria
            FROM producto p
            LEFT JOIN subcategoria s ON s.id_subcategoria = p.id_subcategoria
            WHERE (p.activo = 1 OR p.activo IS NULL)
            ORDER BY p.descripcion ASC
        """)
        productos = cursor.fetchall()
        for p in productos:
            costo = float(p['costo']) if p['costo'] is not None else 0.0
            ganancia = float(p['ganancia']) if p['ganancia'] is not None else 0.0
            p['costo'] = costo
            p['ganancia'] = ganancia
            if p.get('stock') is not None:
                p['stock'] = float(p['stock'])
            if p.get('cantidad_fracciones') is not None:
                p['cantidad_fracciones'] = float(p['cantidad_fracciones'])

            es_frac = bool(p.get('fraccionado')) and p.get('cantidad_fracciones') and float(p['cantidad_fracciones']) > 0
            cant_f = float(p['cantidad_fracciones']) if es_frac else 1.0
            base_costo = costo / cant_f if es_frac else costo
            metodo_g = p.get('metodo_ganancia', 1)
            if metodo_g in (0, False, '0'):
                precio_sug = base_costo + ganancia
            else:
                precio_sug = base_costo * (1.0 + ganancia / 100.0)
            p['precio_sugerido'] = round(precio_sug, 2)

        # Cliente actual de la factura
        cursor.execute("SELECT id_cliente, nombre FROM Cliente WHERE id_cliente = %s", (factura['id_cliente'],))
        cliente_actual = cursor.fetchone()

        # Ítems actuales de la factura
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
        """, (id_factura,))
        raw_items = cursor.fetchall()
        items_actuales = []
        for it in raw_items:
            items_actuales.append({
                'id_producto': it['id_producto'],
                'descripcion': it['descripcion'] or '',
                'cantidad': int(it['cantidad'] or 1),
                'precio_unitario': float(it['precio_unitario']) if it['precio_unitario'] is not None else 0.0,
                'descuento': float(it['descuento']) if it['descuento'] is not None else 0.0
            })

        cursor.execute("SELECT id_subcategoria, nombre FROM subcategoria ORDER BY nombre ASC")
        subcategorias = cursor.fetchall()
        cursor.execute("SELECT id_proveedor, nombre FROM proveedor ORDER BY nombre ASC")
        proveedores = cursor.fetchall()

        fecha_str = factura['fecha'].strftime('%Y-%m-%d') if factura['fecha'] else date.today().strftime('%Y-%m-%d')

        return render_template(
            'facturas/editar.html',
            factura=factura,
            fecha_str=fecha_str,
            cliente_actual=cliente_actual,
            items_actuales=items_actuales,
            clientes=clientes,
            productos=productos,
            subcategorias=subcategorias,
            proveedores=proveedores
        )

    except Exception as e:
        if request.method == 'POST':
            conn.rollback()
        flash(f"Error al procesar la edición de la factura: {str(e)}", "error")
        return redirect(url_for('facturas.listar_facturas'))
    finally:
        cursor.close()
        conn.close()


@facturas_bp.route('/api/<int:id_factura>/estado', methods=['POST'])
def api_cambiar_estado(id_factura):
    """API para cambiar el estado de una factura individual."""
    data = request.get_json(silent=True) or request.form
    nuevo_estado = (data.get('estado') or '').strip()

    if nuevo_estado not in ESTADOS_PERMITIDOS:
        return jsonify({
            'success': False,
            'error': f"Estado no válido. Los estados permitidos son: {', '.join(ESTADOS_PERMITIDOS)}"
        }), 400

    conn = get_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Error de conexión a la base de datos.'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id_factura, COALESCE(estado, 'Sin enviar') AS estado FROM factura WHERE id_factura = %s", (id_factura,))
        fac = cursor.fetchone()
        if not fac:
            return jsonify({'success': False, 'error': 'La factura no existe.'}), 404

        if fac['estado'] == 'Cobrada':
            return jsonify({
                'success': False,
                'error': 'La factura ya ha sido cobrada y su estado no puede ser modificado.'
            }), 400

        cursor.execute("UPDATE factura SET estado = %s WHERE id_factura = %s", (nuevo_estado, id_factura))
        conn.commit()

        return jsonify({
            'success': True,
            'id_factura': id_factura,
            'estado_anterior': fac['estado'],
            'estado': nuevo_estado,
            'message': f"Estado de Factura Nº 00001-{id_factura:08d} actualizado a '{nuevo_estado}'."
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@facturas_bp.route('/api/cambiar-estado-lote', methods=['POST'])
def api_cambiar_estado_lote():
    """API para cambiar el estado de múltiples facturas seleccionadas."""
    data = request.get_json(silent=True) or request.form
    nuevo_estado = (data.get('estado') or '').strip()
    ids_raw = data.get('ids', [])

    if isinstance(ids_raw, str):
        id_list = [int(x.strip()) for x in ids_raw.split(',') if x.strip().isdigit()]
    elif isinstance(ids_raw, list):
        id_list = [int(x) for x in ids_raw if str(x).isdigit()]
    else:
        id_list = []

    if not id_list:
        return jsonify({'success': False, 'error': 'No se seleccionaron facturas válidas.'}), 400

    if nuevo_estado not in ESTADOS_PERMITIDOS:
        return jsonify({'success': False, 'error': f"Estado no válido. Opciones: {', '.join(ESTADOS_PERMITIDOS)}"}), 400

    conn = get_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Error de conexión a la base de datos.'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        format_ids = ','.join(['%s'] * len(id_list))
        cursor.execute(f"SELECT id_factura FROM factura WHERE id_factura IN ({format_ids}) AND COALESCE(estado, 'Sin enviar') = 'Cobrada'", id_list)
        cobradas_rows = cursor.fetchall()
        cobradas_ids = set(r['id_factura'] for r in cobradas_rows)

        valid_ids = [fid for fid in id_list if fid not in cobradas_ids]
        if not valid_ids:
            return jsonify({
                'success': False,
                'error': 'Las facturas seleccionadas ya están cobradas y no se pueden modificar.'
            }), 400

        valid_format = ','.join(['%s'] * len(valid_ids))
        cursor.execute(f"UPDATE factura SET estado = %s WHERE id_factura IN ({valid_format})", [nuevo_estado] + valid_ids)
        conn.commit()

        msg = f"Se actualizaron {len(valid_ids)} factura(s) a '{nuevo_estado}' exitosamente."
        if cobradas_ids:
            msg += f" ({len(cobradas_ids)} omitida(s) por estar ya cobradas)"

        return jsonify({
            'success': True,
            'count': len(valid_ids),
            'cobradas_omitidas': len(cobradas_ids),
            'estado': nuevo_estado,
            'message': msg
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@facturas_bp.route('/api/<int:id_factura>/abrir-carpeta', methods=['POST'])
def api_abrir_carpeta_factura(id_factura):
    """Abre el Explorador de archivos del sistema con el archivo PDF de la factura seleccionado y enfocado."""
    conn = get_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Error de conexión a la base de datos'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id_factura, fecha, url, id_cliente FROM factura WHERE id_factura = %s", (id_factura,))
        factura = cursor.fetchone()
        if not factura:
            return jsonify({'success': False, 'error': 'Factura no encontrada'}), 404

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pdf_path = None
        if factura.get('url'):
            possible_path = os.path.join(base_dir, factura['url'].lstrip('/\\'))
            if os.path.exists(possible_path):
                pdf_path = possible_path

        # Si el archivo PDF no existe físicamente en disco, generarlo con nombre descriptivo
        if not pdf_path or not os.path.exists(pdf_path):
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
            cursor.execute("UPDATE factura SET url = %s WHERE id_factura = %s", (pdf_url, id_factura))
            conn.commit()

        if pdf_path and os.path.exists(pdf_path):
            norm_path = os.path.normpath(pdf_path)
            sys_name = platform.system()
            if sys_name == 'Windows':
                # explorer /select,"path" abre la carpeta y selecciona el archivo resaltándolo
                subprocess.Popen(f'explorer /select,"{norm_path}"')
            elif sys_name == 'Darwin':  # macOS
                subprocess.Popen(['open', '-R', norm_path])
            else:  # Linux
                subprocess.Popen(['xdg-open', os.path.dirname(norm_path)])

            return jsonify({
                'success': True,
                'path': norm_path,
                'filename': os.path.basename(norm_path)
            })
        else:
            return jsonify({'success': False, 'error': 'No se pudo generar el archivo PDF'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@facturas_bp.route('/')
def listar_facturas():
    """Listado de todas las facturas emitidas con búsqueda, filtros, estadísticas y paginación."""
    nro_factura = request.args.get('nro_factura', '').strip()
    cliente = request.args.get('cliente', '').strip()
    estado_filtro = request.args.get('estado', '').strip()
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

    # Contadores por estado
    stats_estados = {
        'Sin enviar': {'count': 0, 'total': 0.0},
        'Enviada': {'count': 0, 'total': 0.0},
        'Cobrada': {'count': 0, 'total': 0.0},
    }

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

            # 2. Conteo y montos por cada estado global
            cursor.execute("""
                SELECT 
                    COALESCE(NULLIF(f.estado, ''), 'Sin enviar') AS estado,
                    COUNT(DISTINCT f.id_factura) AS cant,
                    COALESCE(SUM(i.cantidad * i.precio_unitario * (1.0 - COALESCE(i.descuento, 0) / 100.0)), 0) AS total
                FROM factura f
                LEFT JOIN item_factura i ON f.id_factura = i.id_factura
                GROUP BY COALESCE(NULLIF(f.estado, ''), 'Sin enviar')
            """)
            estado_rows = cursor.fetchall()
            for er in estado_rows:
                est = er['estado']
                if est in stats_estados:
                    stats_estados[est]['count'] = int(er['cant'] or 0)
                    stats_estados[est]['total'] = float(er['total'] or 0.0)

            # 3. Consulta de facturas filtradas
            sql = """
                SELECT 
                    f.id_factura, 
                    f.fecha, 
                    f.url, 
                    f.id_cliente,
                    COALESCE(NULLIF(f.estado, ''), 'Sin enviar') AS estado,
                    c.nombre AS cliente_nombre,
                    c.telefono AS cliente_telefono,
                    COUNT(i.id_item_factura) AS total_items,
                    COALESCE(SUM(i.cantidad * i.precio_unitario * (1.0 - COALESCE(i.descuento, 0) / 100.0)), 0) AS total_monto
                FROM factura f
                LEFT JOIN cliente c ON f.id_cliente = c.id_cliente
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

            if estado_filtro and estado_filtro in ESTADOS_PERMITIDOS:
                sql += " AND COALESCE(NULLIF(f.estado, ''), 'Sin enviar') = %s"
                params.append(estado_filtro)

            if fecha_desde:
                sql += " AND f.fecha >= %s"
                params.append(fecha_desde)

            if fecha_hasta:
                sql += " AND f.fecha <= %s"
                params.append(fecha_hasta)

            sql += " GROUP BY f.id_factura, f.fecha, f.url, f.id_cliente, f.estado, c.nombre, c.telefono ORDER BY f.id_factura DESC"

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

    # 4. Paginación de 20 comprobantes por página
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
        stats_estados=stats_estados,
        estados_permitidos=ESTADOS_PERMITIDOS,
        estado_filtro=estado_filtro,
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

        return send_file(pdf_path, mimetype='application/pdf', as_attachment=False, download_name=os.path.basename(pdf_path))

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
    writer.writerow(['Nro Factura', 'Fecha', 'Cliente', 'Items', 'Total ($)', 'Estado'])

    cursor = conn.cursor(dictionary=True)
    try:
        format_ids = ','.join(['%s'] * len(id_list))
        sql = f"""
            SELECT 
                f.id_factura, 
                f.fecha, 
                COALESCE(NULLIF(f.estado, ''), 'Sin enviar') AS estado,
                c.nombre AS cliente_nombre,
                COUNT(i.id_item_factura) AS total_items,
                COALESCE(SUM(i.cantidad * i.precio_unitario * (1.0 - COALESCE(i.descuento, 0) / 100.0)), 0) AS total_monto
            FROM factura f
            LEFT JOIN Cliente c ON f.id_cliente = c.id_cliente
            LEFT JOIN item_factura i ON f.id_factura = i.id_factura
            WHERE f.id_factura IN ({format_ids})
            GROUP BY f.id_factura, f.fecha, f.estado, c.nombre
            ORDER BY f.id_factura DESC
        """
        cursor.execute(sql, id_list)
        rows = cursor.fetchall()
        for r in rows:
            fecha_str = r['fecha'].strftime('%d/%m/%Y') if r['fecha'] else ''
            monto = float(r['total_monto']) if r['total_monto'] is not None else 0.0
            monto_fmt = f"{monto:.2f}".replace('.', ',')
            writer.writerow([f"00001-{r['id_factura']:08d}", fecha_str, r['cliente_nombre'] or 'Consumidor Final', r['total_items'], monto_fmt, r['estado']])
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


@facturas_bp.route('/api/<int:id_factura>/enviar-whatsapp-auto', methods=['POST'])
def enviar_whatsapp_auto(id_factura):
    """Envía la factura con su PDF adjunto por WhatsApp de forma automatizada."""
    data = request.get_json(silent=True) or {}
    telefono_override = data.get('telefono', '').strip()

    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "error": "Error al conectar con la base de datos."}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id_factura, fecha, url, id_cliente, COALESCE(estado, 'Sin enviar') AS estado FROM factura WHERE id_factura = %s", (id_factura,))
        factura = cursor.fetchone()
        if not factura:
            return jsonify({"success": False, "error": "La factura no existe."}), 404

        cliente = None
        if factura['id_cliente']:
            cursor.execute("SELECT id_cliente, nombre, telefono FROM cliente WHERE id_cliente = %s", (factura['id_cliente'],))
            cliente = cursor.fetchone()

        # Determinar teléfono a utilizar
        telefono = telefono_override or (cliente['telefono'] if cliente and cliente.get('telefono') else '')

        # Si vino telefono_override y el cliente existe, guardarlo en la base de datos
        if telefono_override and cliente and cliente.get('id_cliente'):
            cursor.execute("UPDATE cliente SET telefono = %s WHERE id_cliente = %s", (telefono_override, cliente['id_cliente']))
            conn.commit()

        if not telefono:
            return jsonify({
                "success": False,
                "needs_phone": True,
                "cliente_nombre": cliente['nombre'] if cliente else "Consumidor Final",
                "id_cliente": cliente['id_cliente'] if cliente else None,
                "error": "El cliente no tiene un teléfono registrado."
            }), 400

        # Obtener items de la factura
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

        # Generar archivo PDF
        pdf_path, _ = generar_factura_pdf(
            factura_data=factura,
            cliente_data=cliente,
            items_data=items,
            empresa_data=empresa
        )

        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()

        # Calcular monto total
        total_monto = sum(float(it['cantidad']) * float(it['precio_unitario']) * (1.0 - (float(it.get('descuento') or 0.0) / 100.0)) for it in items)
        total_formatted = f"{total_monto:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        fecha_str = factura['fecha'].strftime('%d/%m/%Y') if factura.get('fecha') else ''
        cliente_nombre = cliente['nombre'] if cliente and cliente.get('nombre') else 'Consumidor Final'
        filename = f"Factura_00001-{id_factura:08d}.pdf"

        caption = (
            f"Hola *{cliente_nombre}*! 👋\n"
            f"Le adjuntamos el comprobante en PDF de su *Factura Nº 00001-{id_factura:08d}*:\n\n"
            f"📅 *Fecha:* {fecha_str}\n"
            f"💰 *Total:* $ {total_formatted}\n\n"
            f"¡Muchas gracias por su compra!"
        )

        # Enviar vía WhatsApp Service
        success, message = WhatsAppService.enviar_factura_pdf(
            telefono=telefono,
            pdf_bytes=pdf_bytes,
            filename=filename,
            caption=caption
        )

        if success:
            # Si el estado actual es 'Sin enviar', actualizar a 'Enviada' automáticamente
            if factura['estado'] == 'Sin enviar':
                cursor.execute("UPDATE factura SET estado = 'Enviada' WHERE id_factura = %s", (id_factura,))
                conn.commit()
            return jsonify({"success": True, "message": message, "telefono": telefono, "nuevo_estado": "Enviada"})
        else:
            return jsonify({"success": False, "error": message}), 400

    except Exception as e:
        return jsonify({"success": False, "error": f"Error interno: {str(e)}"}), 500
    finally:
        cursor.close()
        conn.close()

