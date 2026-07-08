from flask import Blueprint, render_template

facturas_bp = Blueprint('facturas', __name__)


@facturas_bp.route('/nueva')
def nueva_factura():
    """Formulario para crear una nueva factura."""
    return render_template('facturas/nueva.html')


@facturas_bp.route('/')
def listar_facturas():
    """Listado de todas las facturas."""
    return render_template('facturas/listar.html')
