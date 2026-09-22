from datetime import date, datetime
from flask import Blueprint, render_template, request, jsonify
from app.db import get_connection

main_bp = Blueprint('main', __name__)


def _obtener_stats_facturas(cursor, fecha_desde_str=None, fecha_hasta_str=None):
    """Calcula cantidad y monto facturado según rango de fechas opcional."""
    condiciones = []
    parametros = []

    if fecha_desde_str:
        condiciones.append("f.fecha >= %s")
        parametros.append(fecha_desde_str)

    if fecha_hasta_str:
        condiciones.append("f.fecha <= %s")
        parametros.append(fecha_hasta_str)

    where_clause = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

    sql_count = f"SELECT COUNT(*) AS total FROM factura f {where_clause}"
    cursor.execute(sql_count, tuple(parametros))
    row_count = cursor.fetchone()
    total_facturas = int(row_count['total']) if row_count else 0

    sql_monto = f"""
        SELECT COALESCE(SUM(i.cantidad * i.precio_unitario * (1.0 - COALESCE(i.descuento, 0) / 100.0)), 0) AS monto
        FROM factura f
        LEFT JOIN item_factura i ON f.id_factura = i.id_factura
        {where_clause}
    """
    cursor.execute(sql_monto, tuple(parametros))
    row_monto = cursor.fetchone()
    total_monto = float(row_monto['monto']) if row_monto and row_monto['monto'] is not None else 0.0

    return total_facturas, total_monto


@main_bp.route('/')
def index():
    """Página principal del sistema con estadísticas, gráficos y últimos productos modificados."""
    fecha_desde = request.args.get('fecha_desde', '').strip()
    fecha_hasta = request.args.get('fecha_hasta', '').strip()

    stats = {
        'productos_activos': 0,
        'clientes_activos': 0,
        'facturas_generadas': 0,
        'facturas_monto': 0.0,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    }

    chart_subcategorias = {
        'labels': [],
        'data': []
    }

    chart_proveedores = {
        'labels': [],
        'data': []
    }

    ultimos_productos = []

    conn = get_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Productos activos
            cursor.execute("SELECT COUNT(*) AS total FROM producto WHERE (activo = 1 OR activo IS NULL)")
            row_p = cursor.fetchone()
            stats['productos_activos'] = int(row_p['total']) if row_p else 0

            # 2. Clientes activos
            cursor.execute("SELECT COUNT(*) AS total FROM cliente WHERE activo = 1")
            row_c = cursor.fetchone()
            stats['clientes_activos'] = int(row_c['total']) if row_c else 0

            # 3. Facturas generadas con filtro de fecha
            total_fac, monto_fac = _obtener_stats_facturas(cursor, fecha_desde, fecha_hasta)
            stats['facturas_generadas'] = total_fac
            stats['facturas_monto'] = monto_fac

            # 4. Gráfico de barras horizontal: 5 subcategorías con más productos
            cursor.execute("""
                SELECT s.nombre, COUNT(p.id_producto) AS total
                FROM producto p
                INNER JOIN subcategoria s ON p.id_subcategoria = s.id_subcategoria
                WHERE p.activo = 1 OR p.activo IS NULL
                GROUP BY s.id_subcategoria, s.nombre
                ORDER BY total DESC
                LIMIT 5
            """)
            subcats = cursor.fetchall()
            chart_subcategorias['labels'] = [s['nombre'] for s in subcats]
            chart_subcategorias['data'] = [int(s['total']) for s in subcats]

            # 5. Gráfico de torta: cantidad de productos por proveedor (incluyendo sin proveedor)
            cursor.execute("""
                SELECT COALESCE(pr.nombre, 'Sin proveedor') AS nombre, COUNT(p.id_producto) AS total
                FROM producto p
                LEFT JOIN proveedor pr ON p.id_proveedor = pr.id_proveedor
                WHERE p.activo = 1 OR p.activo IS NULL
                GROUP BY p.id_proveedor, pr.nombre
                ORDER BY total DESC
            """)
            provs = cursor.fetchall()
            chart_proveedores['labels'] = [pr['nombre'] for pr in provs]
            chart_proveedores['data'] = [int(pr['total']) for pr in provs]

            # 6. Grilla de los últimos 10 productos modificados
            cursor.execute("""
                SELECT p.id_producto, p.descripcion, p.codigo_barra, p.costo, p.ganancia, p.stock,
                       p.fecha_ult_modificacion, p.imagen, p.fraccionado, p.cantidad_fracciones,
                       p.metodo_ganancia, p.es_nuevo, p.es_oferta,
                       s.nombre AS subcategoria_nombre,
                       pr.nombre AS proveedor_nombre
                FROM producto p
                LEFT JOIN subcategoria s ON s.id_subcategoria = p.id_subcategoria
                LEFT JOIN proveedor pr ON pr.id_proveedor = p.id_proveedor
                WHERE p.activo = 1 OR p.activo IS NULL
                ORDER BY p.fecha_ult_modificacion DESC, p.id_producto DESC
                LIMIT 10
            """)
            productos_raw = cursor.fetchall()
            for prod in productos_raw:
                costo = float(prod['costo']) if prod['costo'] is not None else None
                ganancia = float(prod['ganancia']) if prod['ganancia'] is not None else None

                if costo is not None and ganancia is not None:
                    es_frac = bool(prod.get('fraccionado')) and prod.get('cantidad_fracciones') and float(prod['cantidad_fracciones']) > 0
                    cant_f = float(prod['cantidad_fracciones']) if es_frac else 1.0
                    base_costo = costo / cant_f if es_frac else costo
                    metodo_g = prod.get('metodo_ganancia', 1)
                    if metodo_g == 0:
                        prod['precio_venta'] = base_costo + ganancia
                    else:
                        prod['precio_venta'] = base_costo * (1.0 + ganancia / 100.0)
                else:
                    prod['precio_venta'] = None

                prod['costo'] = costo
                prod['ganancia'] = ganancia
                prod['fecha_modificacion_str'] = prod['fecha_ult_modificacion'].strftime('%d/%m/%Y') if prod.get('fecha_ult_modificacion') else '-'
                ultimos_productos.append(prod)

        except Exception as e:
            print(f"Error cargando dashboard: {e}")
        finally:
            cursor.close()
            conn.close()

    return render_template(
        'index.html',
        stats=stats,
        chart_subcategorias=chart_subcategorias,
        chart_proveedores=chart_proveedores,
        ultimos_productos=ultimos_productos
    )


@main_bp.route('/api/dashboard/facturas-stat')
def api_dashboard_facturas_stat():
    """Endpoint dinámico para consultar estadísticas de facturas según rango de fechas."""
    fecha_desde = request.args.get('fecha_desde', '').strip() or None
    fecha_hasta = request.args.get('fecha_hasta', '').strip() or None

    conn = get_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Error de conexión'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        total_fac, monto_fac = _obtener_stats_facturas(cursor, fecha_desde, fecha_hasta)
        return jsonify({
            'success': True,
            'total': total_fac,
            'monto': monto_fac,
            'fecha_desde': fecha_desde or '',
            'fecha_hasta': fecha_hasta or ''
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@main_bp.route('/api/buscar')
def api_buscar():
    """Endpoint de búsqueda global para productos, clientes y facturas."""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({'productos': [], 'clientes': [], 'facturas': []})

    conn = get_connection()
    if not conn:
        return jsonify({'productos': [], 'clientes': [], 'facturas': [], 'error': 'Error de conexión'}), 500

    cursor = conn.cursor(dictionary=True)
    productos = []
    clientes = []
    facturas = []

    try:
        like_str = f"%{query}%"

        # 1. Buscar Productos (activos)
        sql_prod = """
            SELECT p.id_producto, p.descripcion, p.codigo_barra, p.codigo_proveedor,
                   p.costo, p.ganancia, p.stock, p.imagen,
                   p.fraccionado, p.cantidad_fracciones, p.metodo_ganancia,
                   s.nombre AS subcategoria_nombre
            FROM producto p
            LEFT JOIN subcategoria s ON s.id_subcategoria = p.id_subcategoria
            WHERE p.activo = 1 AND (
                p.descripcion LIKE %s OR 
                p.codigo_barra LIKE %s OR 
                p.codigo_proveedor LIKE %s
            )
            ORDER BY 
                CASE WHEN p.descripcion LIKE %s THEN 1 ELSE 2 END,
                p.descripcion ASC
            LIMIT 6
        """
        cursor.execute(sql_prod, (like_str, like_str, like_str, f"{query}%"))
        raw_prod = cursor.fetchall()
        for p in raw_prod:
            costo = float(p['costo']) if p['costo'] is not None else 0.0
            ganancia = float(p['ganancia']) if p['ganancia'] is not None else 0.0
            es_frac = bool(p.get('fraccionado')) and p.get('cantidad_fracciones') and float(p['cantidad_fracciones']) > 0
            cant_f = float(p['cantidad_fracciones']) if es_frac else 1.0
            base_costo = costo / cant_f if es_frac else costo
            metodo_g = p.get('metodo_ganancia', 1)
            if metodo_g == 0:
                precio = round(base_costo + ganancia, 2)
            else:
                precio = round(base_costo * (1 + ganancia / 100), 2)
            productos.append({
                'id_producto': p['id_producto'],
                'descripcion': p['descripcion'],
                'codigo_barra': p['codigo_barra'],
                'codigo_proveedor': p['codigo_proveedor'],
                'stock': p['stock'] if p['stock'] is not None else 0,
                'precio': precio,
                'subcategoria': p['subcategoria_nombre'],
                'imagen': p['imagen'],
                'url': f"/productos/editar/{p['id_producto']}"
            })

        # 2. Buscar Clientes (activos)
        sql_cli = """
            SELECT id_cliente, nombre, telefono
            FROM cliente
            WHERE activo = 1 AND (nombre LIKE %s OR telefono LIKE %s OR CAST(id_cliente AS CHAR) LIKE %s)
            ORDER BY 
                CASE WHEN nombre LIKE %s THEN 1 ELSE 2 END,
                nombre ASC
            LIMIT 5
        """
        cursor.execute(sql_cli, (like_str, like_str, like_str, f"{query}%"))
        raw_cli = cursor.fetchall()
        for c in raw_cli:
            clientes.append({
                'id_cliente': c['id_cliente'],
                'nombre': c['nombre'],
                'telefono': c['telefono'] or '',
                'url': f"/clientes/editar/{c['id_cliente']}"
            })

        # 3. Buscar Facturas
        sql_fac = """
            SELECT f.id_factura, f.fecha, f.url, c.nombre AS cliente_nombre,
                   COALESCE(SUM(i.cantidad * i.precio_unitario * (1.0 - COALESCE(i.descuento, 0) / 100.0)), 0) AS total
            FROM factura f
            LEFT JOIN cliente c ON f.id_cliente = c.id_cliente
            LEFT JOIN item_factura i ON f.id_factura = i.id_factura
            WHERE CAST(f.id_factura AS CHAR) LIKE %s OR c.nombre LIKE %s
            GROUP BY f.id_factura, f.fecha, f.url, c.nombre
            ORDER BY f.id_factura DESC
            LIMIT 4
        """
        cursor.execute(sql_fac, (like_str, like_str))
        raw_fac = cursor.fetchall()
        for f in raw_fac:
            fecha_str = f['fecha'].strftime('%d/%m/%Y') if f['fecha'] else ''
            facturas.append({
                'id_factura': f['id_factura'],
                'fecha': fecha_str,
                'cliente_nombre': f['cliente_nombre'] or 'Sin cliente',
                'total': float(f['total']) if f['total'] is not None else 0.0,
                'url': f['url'] or f"/facturas/?nro_factura={f['id_factura']}"
            })

    except Exception as e:
        return jsonify({'productos': [], 'clientes': [], 'facturas': [], 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify({
        'productos': productos,
        'clientes': clientes,
        'facturas': facturas
    })
