import os
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfgen import canvas


def format_currency(val):
    """Formatea un número flotante o decimal como moneda argentina: $ 1.234,56 o -$ 1.234,56"""
    try:
        num = float(val) if val is not None else 0.0
    except (ValueError, TypeError):
        num = 0.0
    is_neg = num < 0
    abs_num = abs(num)
    s = f"{abs_num:,.2f}"
    main_part, dec_part = s.split('.')
    main_part = main_part.replace(',', '.')
    return f"{'-' if is_neg else ''}$ {main_part},{dec_part}"


class NumberedCanvas(canvas.Canvas):
    """Canvas para agregar numeración de páginas y pie de página en ReportLab."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#4a6280"))
        
        # Pie de página: aclaración de documento no válido como factura
        pie_texto = "DOCUMENTO NO VALIDO COMO FACTURA - COMPROBANTE DE VENTA"
        self.drawCentredString(A4[0] / 2.0, 24, pie_texto)
        
        # Número de página
        page_str = f"Pag. {self._pageNumber} de {page_count}"
        self.drawRightString(A4[0] - 30, 24, page_str)
        
        self.restoreState()


def generar_factura_pdf(factura_data, cliente_data, items_data, empresa_data=None, output_path=None):
    """
    Genera un archivo PDF 'Tipo Factura X' con los datos provistos.
    
    :param factura_data: dict con id_factura, fecha
    :param cliente_data: dict con nombre (o id_cliente)
    :param items_data: list de dicts con descripcion, cantidad, precio_unitario
    :param empresa_data: dict opcional con razon_social, nro_telefono, logo
    :param output_path: ruta absoluta donde guardar el PDF. Si es None, guarda en static/facturas/
    :return: (ruta_absoluta, url_relativa)
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_facturas_dir = os.path.join(base_dir, 'static', 'facturas')
    os.makedirs(static_facturas_dir, exist_ok=True)

    id_factura = factura_data.get('id_factura', 1)
    filename = f"factura_{id_factura}.pdf"
    
    if not output_path:
        output_path = os.path.join(static_facturas_dir, filename)
        
    url_relativa = f"/static/facturas/{filename}"

    # Datos de empresa con fallbacks
    empresa = empresa_data or {}
    razon_social = empresa.get('razon_social') or 'JJB DISTRIBUCIONES'
    telefono = empresa.get('nro_telefono') or ''
    logo_path = empresa.get('logo')

    # Resolver logo
    default_logo = os.path.join(base_dir, 'static', 'img', 'logo.png')
    if not logo_path or not os.path.exists(logo_path):
        if logo_path and os.path.exists(os.path.join(base_dir, 'static', logo_path)):
            logo_path = os.path.join(base_dir, 'static', logo_path)
        elif logo_path and os.path.exists(os.path.join(base_dir, 'static', 'img', logo_path)):
            logo_path = os.path.join(base_dir, 'static', 'img', logo_path)
        else:
            logo_path = default_logo if os.path.exists(default_logo) else None

    # Fecha formateada
    fecha_val = factura_data.get('fecha')
    if isinstance(fecha_val, (datetime, date)):
        fecha_str = fecha_val.strftime('%d/%m/%Y')
    elif isinstance(fecha_val, str) and fecha_val:
        try:
            dt = datetime.strptime(fecha_val, '%Y-%m-%d')
            fecha_str = dt.strftime('%d/%m/%Y')
        except ValueError:
            fecha_str = fecha_val
    else:
        fecha_str = datetime.now().strftime('%d/%m/%Y')

    # Cliente
    nombre_cliente = cliente_data.get('nombre') if cliente_data else 'Consumidor Final'
    if not nombre_cliente:
        nombre_cliente = 'Consumidor Final'

    # Crear Documento
    # Márgenes de 28pt (~1 cm) para maximizar área útil
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=28,
        rightMargin=28,
        topMargin=28,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Estilos de párrafos personalizados
    style_normal = ParagraphStyle(
        'FacturaNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0C2340')
    )
    
    style_empresa_title = ParagraphStyle(
        'EmpresaTitle',
        parent=style_normal,
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0C2340')
    )
    
    style_empresa_info = ParagraphStyle(
        'EmpresaInfo',
        parent=style_normal,
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#4a6280')
    )
    
    style_tipo_letra = ParagraphStyle(
        'TipoLetra',
        parent=style_normal,
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=24,
        alignment=1, # Centro
        textColor=colors.HexColor('#0C2340')
    )
    
    style_tipo_sub = ParagraphStyle(
        'TipoSub',
        parent=style_normal,
        fontName='Helvetica-Bold',
        fontSize=6.5,
        leading=7.5,
        alignment=1, # Centro
        textColor=colors.HexColor('#0C2340')
    )
    
    style_doc_title = ParagraphStyle(
        'DocTitle',
        parent=style_normal,
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        alignment=2, # Derecha
        textColor=colors.HexColor('#0C2340')
    )
    
    style_doc_info = ParagraphStyle(
        'DocInfo',
        parent=style_normal,
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        alignment=2, # Derecha
        textColor=colors.HexColor('#0C2340')
    )
    
    style_th = ParagraphStyle(
        'TableHead',
        parent=style_normal,
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=10,
        textColor=colors.white
    )
    
    style_td = ParagraphStyle(
        'TableBody',
        parent=style_normal,
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#0C2340')
    )
    
    style_td_num = ParagraphStyle(
        'TableBodyNum',
        parent=style_td,
        alignment=2 # Derecha
    )

    style_td_center = ParagraphStyle(
        'TableBodyCenter',
        parent=style_td,
        alignment=1 # Centro
    )

    story = []

    # Ancho total disponible en A4 = 595.27 - 56 = 539.27 pt
    ancho_util = A4[0] - 56

    # ══════════════════════════════════════════════════
    # 1. ENCABEZADO: LADO IZQ | TIPO X | LADO DER
    # ══════════════════════════════════════════════════
    ancho_izq = 230
    ancho_centro = 79.27
    ancho_der = 230

    # Lado Izquierdo: Logo y Razón Social
    elems_izq = []
    if logo_path and os.path.exists(logo_path):
        try:
            # Mantener proporción aproximada
            img = Image(logo_path, width=120, height=45)
            img.hAlign = 'LEFT'
            elems_izq.append(img)
            elems_izq.append(Spacer(1, 4))
        except Exception:
            pass
            
    elems_izq.append(Paragraph(razon_social, style_empresa_title))
    if telefono:
        elems_izq.append(Paragraph(f"Teléfono: <b>{telefono}</b>", style_empresa_info))
    elems_izq.append(Paragraph("Venta por Mayor y Menor — Distribuidora", style_empresa_info))

    # Centro: Cuadro de Letra "X"
    elems_centro = [
        Spacer(1, 2),
        Paragraph("X", style_tipo_letra),
        Spacer(1, 2),
    ]

    # Lado Derecho: Título comprobante, Número y Fecha
    nro_factura_str = f"00001-{id_factura:08d}" if isinstance(id_factura, int) else f"00001-{int(id_factura or 1):08d}"
    elems_der = [
        Paragraph("COMPROBANTE X", style_doc_title),
        Spacer(1, 4),
        Paragraph(f"Nº: <b>{nro_factura_str}</b>", style_doc_info),
        Paragraph(f"Fecha de Emisión: <b>{fecha_str}</b>", style_doc_info),
        Spacer(1, 4)
    ]

    tabla_header_data = [
        [elems_izq, elems_centro, elems_der]
    ]

    tabla_header = Table(
        tabla_header_data,
        colWidths=[ancho_izq, ancho_centro, ancho_der]
    )
    
    tabla_header.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#0C2340')),
        ('BOX', (1, 0), (1, 0), 1.5, colors.HexColor('#0C2340')), # Borde más marcado para el centro
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F7F9FC')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (0, 0), 10),
        ('RIGHTPADDING', (-1, 0), (-1, 0), 10),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
    ]))

    story.append(tabla_header)
    story.append(Spacer(1, 6))

    # ══════════════════════════════════════════════════
    # 2. BLOQUE DE DATOS DEL CLIENTE
    # ══════════════════════════════════════════════════
    cliente_data_table = [
        [
            Paragraph(f"<b>Señor(es) / Cliente:</b> {nombre_cliente}", style_normal),
        ]
    ]

    tabla_cliente = Table(cliente_data_table, colWidths=[ancho_util])
    tabla_cliente.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#0C2340')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E8EEF5')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    story.append(tabla_cliente)
    story.append(Spacer(1, 8))

    # ══════════════════════════════════════════════════
    # 3. TABLA DE ÍTEMS / PRODUCTOS
    # ══════════════════════════════════════════════════
    col_cant = 45
    col_subtotal = 95
    col_precio = 95
    col_desc = ancho_util - col_cant - col_precio - col_subtotal

    th_cant = Paragraph("CANT.", ParagraphStyle('THC', parent=style_th, alignment=1))
    th_desc = Paragraph("DESCRIPCIÓN / PRODUCTO", style_th)
    th_precio = Paragraph("PRECIO UNIT.", ParagraphStyle('THP', parent=style_th, alignment=2))
    th_subtotal = Paragraph("SUBTOTAL", ParagraphStyle('THS', parent=style_th, alignment=2))

    tabla_items_data = [
        [th_cant, th_desc, th_precio, th_subtotal]
    ]

    total_general = 0.0

    for idx, item in enumerate(items_data):
        cant = int(item.get('cantidad', 1) or 1)
        desc = item.get('descripcion') or 'Producto'
        precio_unit = float(item.get('precio_unitario', 0.0) or 0.0)
        subtotal = cant * precio_unit
        total_general += subtotal

        p_cant = Paragraph(str(cant), style_td_center)
        p_desc = Paragraph(desc, style_td)
        p_precio = Paragraph(format_currency(precio_unit), style_td_num)
        p_subtotal = Paragraph(format_currency(subtotal), style_td_num)

        tabla_items_data.append([p_cant, p_desc, p_precio, p_subtotal])

    # Si hay pocos ítems, agregar renglones visuales vacíos para darle cuerpo
    filas_minimas = 8
    filas_actuales = len(items_data)
    if filas_actuales < filas_minimas:
        for _ in range(filas_minimas - filas_actuales):
            tabla_items_data.append([
                Paragraph("", style_td),
                Paragraph("", style_td),
                Paragraph("", style_td),
                Paragraph("", style_td)
            ])

    tabla_items = Table(
        tabla_items_data,
        colWidths=[col_cant, col_desc, col_precio, col_subtotal],
        repeatRows=1
    )

    t_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0C2340')),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#0C2340')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E8EEF5')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]

    # Alternar color suave en filas
    for r in range(1, len(tabla_items_data)):
        if r % 2 == 0:
            t_style.append(('BACKGROUND', (0, r), (-1, r), colors.HexColor('#F7F9FC')))

    tabla_items.setStyle(TableStyle(t_style))
    story.append(tabla_items)
    story.append(Spacer(1, 8))

    # ══════════════════════════════════════════════════
    # 4. CUADRO DE TOTAL
    # ══════════════════════════════════════════════════
    style_total_label = ParagraphStyle(
        'TotalLabel',
        parent=style_normal,
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=14,
        alignment=2,
        textColor=colors.HexColor('#0C2340')
    )
    
    style_total_val = ParagraphStyle(
        'TotalVal',
        parent=style_normal,
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=16,
        alignment=2,
        textColor=colors.HexColor('#0C2340')
    )

    tabla_total_data = [
        [
            Paragraph("<b>TOTAL A PAGAR:</b>", style_total_label),
            Paragraph(format_currency(total_general), style_total_val)
        ]
    ]

    tabla_total = Table(
        tabla_total_data,
        colWidths=[ancho_util - col_subtotal - 30, col_subtotal + 30]
    )
    tabla_total.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#0C2340')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E8EEF5')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))

    story.append(tabla_total)

    # Construir documento usando NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    
    return output_path, url_relativa
