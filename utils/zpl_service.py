import base64

class ZPLService:
    """
    Servicio para generar código ZPL (Zebra Programming Language)
    optimizado para la impresora Honeywell PC42t Plus.
    """

    def __init__(self):
        # Dimensiones estándar para etiquetas de ropa (en mm)
        self.label_width_mm = 60
        self.label_height_mm = 40
        self.dpmm = 8  # 203 DPI = 8 puntos por mm

    def generate_barcode_zpl(self, barcode, product_info=None, options=None):
        """
        Genera el string ZPL para una etiqueta de producto.
        """
        if product_info is None:
            product_info = {}
        
        name = product_info.get("product_name", "Producto")
        # Truncar nombre si es muy largo
        if len(name) > 25:
            name = name[:22] + "..."
            
        price = product_info.get("sale_price", "0.00")
        size = product_info.get("size_name", "")
        color = product_info.get("color_name", "")
        
        # Formatear precio con signo de peso y miles
        try:
            if isinstance(price, (int, float)):
                formatted_price = f"${price:,.2f}"
            else:
                formatted_price = f"${float(price):,.2f}"
        except:
            formatted_price = f"${price}"

        # Iniciar ZPL
        # ^XA: Inicio de etiqueta
        # ^CI28: Codificación UTF-8 para caracteres especiales (Eñes, acentos)
        zpl = [
            "^XA",
            "^CI28",  
            # Nombre del producto (centrado o a la izquierda)
            f"^FO25,30^A0N,30,30^FD{name}^FS",
            # Precio destacado
            f"^FO25,70^A0N,40,40^FD{formatted_price}^FS",
            # Talle y Color
            f"^FO25,120^A0N,25,25^FDT: {size}  C: {color}^FS",
            # Código de barras (Code 128)
            # ^BC: Barcode 128 (Normal, Altura 70, Mostrar texto abajo, No, No)
            f"^FO25,160^BCN,70,Y,N,N",
            f"^FD{barcode}^FS",
            # ^XZ: Fin de etiqueta
            "^XZ"
        ]
        
        return "\n".join(zpl)

    def generate_base64_zpl(self, barcode, product_info=None, options=None):
        """
        Genera el código ZPL y lo devuelve en base64 para el frontend.
        """
        zpl_string = self.generate_barcode_zpl(barcode, product_info, options)
        return base64.b64encode(zpl_string.encode('utf-8')).decode('utf-8')
