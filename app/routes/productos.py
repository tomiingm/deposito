from flask import Blueprint, render_template

productos_bp = Blueprint('productos', __name__)


@productos_bp.route('/nuevo')
def nuevo_producto():
    """Formulario para crear un nuevo producto."""
    return render_template('productos/nuevo.html')


@productos_bp.route('/actualizar-precios')
def actualizar_precios():
    """Página para actualizar precios desde PDF."""
    return render_template('productos/actualizar_precios.html')


@productos_bp.route('/')
def listar_productos():
    """Listado de todos los productos."""
    return render_template('productos/listar.html')


@productos_bp.route('/modificar')
def modificar_producto():
    """Formulario para modificar un producto existente."""
    return render_template('productos/modificar.html')
