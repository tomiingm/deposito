from flask import Blueprint, render_template, request, jsonify
from app.db import get_connection

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Página principal del sistema."""
    return render_template('index.html')


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
