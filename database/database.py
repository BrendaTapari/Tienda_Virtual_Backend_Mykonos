class TABLES(Enum):
    ENTITIES = "entities"
    FILE_ATTACHMENTS = "file_attachments"
    ACCOUNT_MOVEMENTS = "account_movements"
    GROUP = "groups"
    USERS = "users"
    WEB_USERS = "web_users"
    WEB_CARTS = "web_carts"
    WEB_CART_ITEMS = "web_cart_items"
    SIZE_CATEGORIES = "size_categories"  # Categorias de los talles
    SIZES = "sizes"  # talles de los productos
    COLORS = "colors"  # colores que pueden ser los productos
    STORAGE = "storage"
    PRODUCTS = "products"
    PRODUCT_SIZES = "product_sizes"  # Relacion muchos a muchos entre productos y talles
    PRODUCT_COLORS = "product_colors"
    IMAGES = "images"  # guarda las imagenes de los productos
    WAREHOUSE_STOCK = (
        "warehouse_stock"  # Relacion muchos a muchos entre sucursal y productos
    )
    WAREHOUSE_STOCK_VARIANTS = (
        "warehouse_stock_variants"  # Stock detallado por talle y color
    )
    INVENTORY_MOVEMETNS = "inventory_movements"
    INVENTORY_MOVEMETNS_GROUPS = "inventory_movements_groups"
    RESPONSABILIDADES_AFIP = "responsabilidades_afip"
    BRANDS = "brands"
    PURCHASES = "purchases"  # compra de mercaderia
    PURCHASES_DETAIL = "purchases_detail"  # detalle de la compra de mercaderia
    SALES = "sales"  # venta de productos
    SALES_DETAIL = "sales_detail"  # detalle de la venta de productos
    PROVEEDORXMARCA = "proveedorxmarca"
    USERSXSTORAGE = "usersxstorage"
    SESSIONS = "sessions"
    PAYMENT_METHODS = "payment_methods"
    BANKS = "banks"
    BANKS_PAYMENT_METHODS = "bank_payment_methods"
    SALES_PAYMENTS = (
        "sales_payments"  # Relación muchos a muchos entre bancos y métodos de pago
    )
    PURCHASES_PAYMENTS = "purchases_payments"
    WEB_VARIANTS = "web_variants"
    DISCOUNTS = "discounts"


DATABASE_TABLES = {
    TABLES.ENTITIES: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada entidad, se incrementa automáticamente.
            "entity_name": "TEXT NOT NULL",  # Nombre de la entidad (puede ser cliente o proveedor).
            "entity_type": "TEXT NOT NULL",  # Tipo de entidad (ejemplo: 'cliente', 'proveedor').
            "razon_social": "TEXT NOT NULL",  # Razón social de la entidad, importante para facturación.
            "responsabilidad_iva": "INTEGER NOT NULL",  # Indica la categoría de responsabilidad ante el IVA (ej: responsable inscripto).
            "domicilio_comercial": "TEXT NOT NULL",  # Dirección comercial de la entidad, necesaria para correspondencia y facturación.
            "cuit": "TEXT NOT NULL UNIQUE",  # CUIT (Clave Única de Identificación Tributaria), único para cada entidad.
            "inicio_actividades": "TEXT",  # Fecha de inicio de actividades de la entidad.
            "ingresos_brutos": "TEXT",  # Información sobre los ingresos brutos, puede ser útil para reportes.
            "contact_name": "TEXT",  # Nombre del contacto principal en la entidad, si aplica.
            "phone_number": "TEXT",  # Número de teléfono de la entidad para contacto directo.
            "email": "TEXT",  # Correo electrónico de la entidad para enviar comunicaciones.
            "observations": "TEXT",  # Notas adicionales o comentarios sobre la entidad, para uso interno.
        }
    },
    TABLES.PROVEEDORXMARCA: {
        "columns": {
            "id_brand": "INTEGER NOT NULL",  # Identificador de la marca.
            "id_provider": "INTEGER NOT NULL",  # Identificador del proveedor.
        },
        "primary_key": [
            "id_brand",
            "id_provider",
        ],  # Definimos la clave primaria compuesta
        "foreign_keys": [
            {  # Relación con la tabla de brand.
                "column": "id_brand",
                "reference_table": TABLES.BRANDS,
                "reference_column": "id",
                "export_column_name": "brand_name",  # <- columna de referencia cuando se exportan tablas
            },
            {  # Relación con la tabla de entidades (proveedores).
                "column": "id_provider",
                "reference_table": TABLES.ENTITIES,
                "reference_column": "id",
                "export_column_name": "entity_name",  # <- columna de referencia cuando se exportan tablas
            },
        ],
    },
    TABLES.FILE_ATTACHMENTS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada archivo adjunto, se incrementa automáticamente.
            "file_name": "TEXT",  # Nombre del archivo original
            "file_extension": "TEXT",  # Extensión del archivo (ej: pdf, jpg, png)
            "file_content": "bytea",  # Contenido del archivo
            "upload_date": "timestamp NULL",  # Fecha de carga del archivo
            "comment": "TEXT",  # Comentario opcional sobre el archivo
        }
    },
    TABLES.ACCOUNT_MOVEMENTS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada movimiento de cuenta, se incrementa automáticamente.
            "numero_operacion": "INTEGER NOT NULL CHECK (numero_operacion > 0)",  # Número de operación, debe ser positivo.
            "entity_id": "INTEGER NOT NULL",  # ID de la entidad relacionada (cliente o proveedor).
            "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",  # Fecha y hora en que se creó el movimiento.
            "descripcion": "TEXT",  # Descripción del movimiento para un seguimiento más detallado.
            "payment_method": "INTEGER",  # Medio de pago utilizado (efectivo, tarjeta de crédito, transferencia, etc.).
            "numero_de_comprobante": "TEXT",  # Número de comprobante asociado al movimiento, si aplica.
            "purchase_id": "INTEGER",  # ID de la compra asociada a este movimiento
            "debe": "REAL",  # Monto que se debe (cargos).
            "haber": "REAL",  # Monto que se acredita (abonos).
            "saldo": "REAL",  # Saldo actual después de realizar el movimiento.
            "file_id": "INTEGER",  # ID del archivo asociado, si existe (documentación adjunta).
            "updated_at": "TEXT DEFAULT CURRENT_TIMESTAMP",  # Fecha de la última modificación del movimiento.
        },
        "foreign_keys": [
            {  # Relación con la tabla de entidades.
                "column": "entity_id",
                "reference_table": TABLES.ENTITIES,
                "reference_column": "id",
                "export_column_name": "entity_name",  # <- columna de referencia cuando se exportan tablas
            },  # Relación con la tabla de archivos adjuntos.
            {
                "column": "file_id",
                "reference_table": TABLES.FILE_ATTACHMENTS,
                "reference_column": "id",
                "export_column_name": "file_name",
            },
            {  # Relación con la tabla de compras.
                "column": "purchase_id",
                "reference_table": TABLES.PURCHASES,
                "reference_column": "id",
                "export_column_name": "id",
            },
            {
                "column": "payment_method",
                "reference_table": TABLES.BANKS_PAYMENT_METHODS,
                "reference_column": "id",
                "export_column_name": "payment_method_name",
            },
        ],
    },
    TABLES.GROUP: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada grupo, se incrementa automáticamente.
            "group_name": "TEXT NOT NULL",  # Nombre del grupo, requerido.
            "parent_group_id": "INTEGER",  # ID del grupo padre, si aplica (permite crear jerarquías).
            "marked_as_root": "INTEGER NOT NULL DEFAULT 0",  # Indica si el grupo es raíz (0) o no (1).
        },
        "foreign_keys": [
            {  # Relación con la tabla de grupos.
                "column": "parent_group_id",
                "reference_table": TABLES.GROUP,
                "reference_column": "id",
                "export_column_name": "group_name",
            }
        ],
    },
    TABLES.USERS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada usuario, se incrementa automáticamente.
            "username": "TEXT UNIQUE",  # Nombre de usuario, debe ser único y no nulo.
            "fullname": "TEXT",  # Nombre completo del usuario, requerido.
            "password": "TEXT",  # Contraseña del usuario, requerida.
            "email": "TEXT",  # Correo electrónico del usuario.
            "phone": "TEXT",
            "domicilio": "TEXT",  # Número de teléfono del usuario.
            "cuit": "TEXT NOT NULL UNIQUE",  # Número de teléfono del usuario.
            "role": "TEXT",  # Rol del usuario (ejemplo: admin, employee).
            "status": "TEXT",  # Estado del usuario (activo, inactivo, etc.).
            "session_token": "TEXT",  # Token de sesión para la autenticación del usuario.
            "profile_image": "BLOB",  # Imagen de perfil del usuario, almacenada como BLOB.
            "created_at": "TEXT DEFAULT (datetime('now','localtime'))",  # Fecha de creación del registro, se establece por defecto a la fecha y hora actuales.
        }
    },
    #Las siguientes 3 tablas hay que agregarlas.
    TABLES.WEB_USERS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada usuario, se incrementa automáticamente.
            "username": "TEXT UNIQUE",  # Nombre de usuario, debe ser único y no nulo.
            "fullname": "TEXT",  # Nombre completo del usuario, requerido.
            "password": "TEXT",  # Contraseña del usuario, requerida.
            "email": "TEXT",  # Correo electrónico del usuario.
            "phone": "TEXT",
            "domicilio": "TEXT",  # Número de teléfono del usuario.
            "cuit": "TEXT NOT NULL UNIQUE",  # Número de teléfono del usuario.
            "role": "TEXT",  # Rol del usuario (ejemplo: admin, employee).
            "status": "TEXT",  # Estado del usuario (activo, inactivo, etc.).
            "session_token": "TEXT",  # Token de sesión para la autenticación del usuario.
            "verification_token": "TEXT",  # Token de verificación para la autenticación del usuario.
            "email_verified": "BOOLEAN NOT NULL DEFAULT 0",  # Indica si el correo electrónico del usuario ha sido verificado.
            "profile_image_url": "TEXT",  # Imagen de perfil del usuario, almacenada como BLOB.
            "created_at": "TEXT DEFAULT (datetime('now','localtime'))",  # Fecha de creación del registro, se establece por defecto a la fecha y hora actuales.
        }
    },
    TABLES.WEB_CARTS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada carrito, se incrementa automáticamente.
            "user_id": "INTEGER NOT NULL",  # ID del usuario al que pertenece el carrito.
            "created_at": "TEXT DEFAULT (datetime('now','localtime'))",  # Fecha de creación del carrito, se establece por defecto a la fecha y hora actuales.
        }
        "foreign_keys": [
            {  # Relación con tabla de usuarios
                "column": "user_id",
                "reference_table": TABLES.WEB_USERS,
                "reference_column": "id",
                "export_column_name": "user_id",  # <- columna de referencia cuando se exportan tablas
            },
        ],
    },
    TABLES.WEB_CART_ITEMS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada ítem del carrito, se incrementa automáticamente.
            "cart_id": "INTEGER NOT NULL",  # ID del carrito al que pertenece el ítem.
            "product_id": "INTEGER NOT NULL",  # ID del producto que se agrega al carrito.
            "variant_id": "INTEGER NOT NULL",  # ID de la variante del producto que se agrega al carrito.
            "quantity": "INTEGER NOT NULL",  # Cantidad del producto en el carrito.
            "created_at": "TEXT DEFAULT (datetime('now','localtime'))",  # Fecha de creación del ítem, se establece por defecto a la fecha y hora actuales.
        }
        "foreign_keys": [
            {  # Relación con tabla de carritos
                "column": "cart_id",
                "reference_table": TABLES.WEB_CARTS,
                "reference_column": "id",
                "export_column_name": "cart_id",  # <- columna de referencia cuando se exportan tablas
            },
            {  # Relación con tabla de productos
                "column": "product_id",
                "reference_table": TABLES.PRODUCTS,
                "reference_column": "id",
                "export_column_name": "product_id",  # <- columna de referencia cuando se exportan tablas
            },
            {  # Relación con tabla de variantes
                "column": "variant_id",
                "reference_table": TABLES.WEB_VARIANTS,
                "reference_column": "id",
                "export_column_name": "variant_id",  # <- columna de referencia cuando se exportan tablas
            },
        ],
    },

    TABLES.SIZE_CATEGORIES: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada categoría de tamaño, se incrementa automáticamente.
            "category_name": "TEXT NOT NULL UNIQUE",  # Nombre de la categoría de tamaño, debe ser único y no nulo.
            "permanent": "BOOLEAN NOT NULL DEFAULT 0",  # Indica si la categoría es permanente (1) o no (0).
        }
    },
    TABLES.SIZES: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada tamaño, se incrementa automáticamente.
            "size_name": "TEXT NOT NULL",  # Nombre del tamaño, requerido.
            "category_id": "INTEGER NOT NULL",  # ID de la categoría de tamaño a la que pertenece.
            "description": "TEXT",  # Descripción del tamaño, opcional.
        },
        "foreign_keys": [
            {
                "column": "category_id",
                "reference_table": TABLES.SIZE_CATEGORIES,
                "reference_column": "id",
                "export_column_name": "category_name",
            }  # Relación con la tabla de categorías de tamaño.
        ],
    },
    TABLES.COLORS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada color, se incrementa automáticamente.
            "color_name": "TEXT NOT NULL",  # Nombre del color, requerido.
            "color_hex": "TEXT NOT NULL",  # Código hexadecimal del color, requerido.
        }
    },
    TABLES.STORAGE: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada almacenamiento, se incrementa automáticamente.
            "name": "TEXT NOT NULL",  # Nombre del almacenamiento, requerido.
            "address": "TEXT",  # Dirección del almacenamiento.
            "postal_code": "TEXT",  # Código postal del almacenamiento.
            "phone_number": "TEXT",  # Número de teléfono del almacenamiento.
            "area": "TEXT",  # Área o sección dentro del almacenamiento.
            "description": "TEXT",  # Área o sección dentro del almacenamiento.
            "created_at": "TEXT DEFAULT (datetime('now','localtime'))",  # Fecha de creación del registro, se establece por defecto a la fecha y hora actuales.
            "status": "TEXT DEFAULT 'Activo'",  # Estado del almacenamiento (activo, inactivo, etc.).
        }
    },
    TABLES.PRODUCTS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada producto, se incrementa automáticamente.
            "provider_code": "TEXT",  # Código del proveedor
            "product_name": "TEXT NOT NULL",  # Nombre del producto, requerido.
            "group_id": "INTEGER",  # ID del grupo al que pertenece el producto.
            "provider_id": "INTEGER",  # ID del proveedor, se relaciona con la tabla de entidades.
            "description": "TEXT",  # Descripción del producto, opcional.
            "cost": "REAL",  # Costo del producto.
            "sale_price": "REAL",  # Precio de venta del producto.
            "tax": "REAL",  # Impuesto aplicable al producto.
            "discount": "REAL",  # Descuento aplicado al producto.
            "original_price": "REAL DEFAULT 0",  # Precio original antes del descuento.
            "discount_percentage": "REAL DEFAULT 0",  # Porcentaje de descuento.
            "discount_amount": "REAL DEFAULT 0",  # Monto del descuento.
            "has_discount": "INTEGER DEFAULT 0",  # Indica si el producto tiene descuento aplicado.
            "comments": "TEXT",  # Comentarios adicionales sobre el producto.
            "user_id": "INTEGER",  # ID del usuario que creó o modificó el producto.
            "brand_id": "INTEGER",  # ID de la marca del producto.
            "creation_date": "timestamp [CURRENT_TIMESTAMP]",  # Fecha de creación del producto, se establece por defecto a la fecha y hora actuales.
            "last_modified_date": "TEXT",  # Fecha de la última modificación del producto.
            "state": "TEXT DEFAULT 'activo'",  # Estado del producto posibles: (enTienda, sinStock, esperandoArribo).
            "en_tienda_online": "BOOLEAN DEFAULT FALSE", #es si esta en la tienda online.
            "nombre_web": "TEXT", #nombre del producto para la tienda online.
            "descripcion_web": "TEXT", #descripcion del producto para la tienda online.
            "precio_web": "REAL", #precio del producto para la tienda online.
            "slug": "TEXT", #slug del producto para la tienda online es para la url.
        },
        "foreign_keys": [
            {  # Relación con la tabla de usuarios.
                "column": "user_id",
                "reference_table": TABLES.USERS,
                "reference_column": "id",
                "export_column_name": "username",
            },
            {  # Relación con la tabla de grupos.
                "column": "group_id",
                "reference_table": TABLES.GROUP,
                "reference_column": "id",
                "export_column_name": "group_name",
            },
            {  # Relación con la tabla de marcas.
                "column": "brand_id",
                "reference_table": TABLES.BRANDS,
                "reference_column": "id",
                "export_column_name": "brand_name",
            },
            {
                "column": "provider_id",
                "reference_table": TABLES.ENTITIES,
                "reference_column": "id",
                "export_column_name": "entity_name",
            },
        ],
    },
    TABLES.IMAGES: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada imagen, se incrementa automáticamente.
            "image_data": "BLOB NOT NULL",  # Datos de la imagen, almacenados como BLOB. #eliminar el not null
            "image_url": "TEXT",  # URL de la imagen.
            "product_id": "INTEGER",  # ID del producto al que corresponde la imagen.
        },
        "foreign_keys": [
            {  # Relación con la tabla de productos.
                "column": "product_id",
                "reference_table": TABLES.PRODUCTS,
                "reference_column": "id",
                "export_column_name": "product_name",
            }
        ],
    },
    TABLES.PRODUCT_SIZES: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada relación producto-talle.
            "product_id": "INTEGER NOT NULL",  # ID del producto.
            "size_id": "INTEGER NOT NULL",  # ID del talle.
            "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",  # Fecha de creación de la relación.
        },
        "foreign_keys": [
            {  # Relación con la tabla de productos.
                "column": "product_id",
                "reference_table": TABLES.PRODUCTS,
                "reference_column": "id",
                "export_column_name": "product_name",
            },
            {  # Relación con la tabla de talles.
                "column": "size_id",
                "reference_table": TABLES.SIZES,
                "reference_column": "id",
                "export_column_name": "size_name",
            },
        ],
    },
    TABLES.PRODUCT_COLORS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada relación producto-color.
            "product_id": "INTEGER NOT NULL",  # ID del producto.
            "color_id": "INTEGER NOT NULL",  # ID del color.
            "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",  # Fecha de creación de la relación.
        },
        "foreign_keys": [
            {  # Relación con la tabla de productos.
                "column": "product_id",
                "reference_table": TABLES.PRODUCTS,
                "reference_column": "id",
                "export_column_name": "product_name",
            },
            {  # Relación con la tabla de colores.
                "column": "color_id",
                "reference_table": TABLES.COLORS,
                "reference_column": "id",
                "export_column_name": "color_name",
            },
        ],
    },
    TABLES.WAREHOUSE_STOCK: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada registro en el inventario.
            "product_id": "INTEGER NOT NULL",  # Identificador del producto, relacionado con la tabla products.
            "branch_id": "INTEGER NOT NULL",  # Identificador de la sucursal que almacena el producto.
            "quantity": "INTEGER NOT NULL CHECK (quantity >= 0)",  # Cantidad actual del producto en la sucursal, no puede ser negativo.
            "last_updated": "TEXT DEFAULT CURRENT_TIMESTAMP",  # Fecha de la última actualización del stock.
            "provider_id": "INTEGER NOT NULL",
        },
        "foreign_keys": [
            {  # Relación con la tabla de productos.
                "column": "product_id",
                "reference_table": TABLES.PRODUCTS,
                "reference_column": "id",
                "export_column_name": "product_name",
            },
            {  # Relación con la tabla de sucursales.
                "column": "branch_id",
                "reference_table": TABLES.STORAGE,
                "reference_column": "id",
                "export_column_name": "name",
            },
            {
                "column": "provider_id",
                "reference_table": TABLES.ENTITIES,
                "reference_column": "id",
                "export_column_name": "name",
            },
        ],
    },
    TABLES.WAREHOUSE_STOCK_VARIANTS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada variante de stock.
            "product_id": "INTEGER NOT NULL",  # Identificador del producto.
            "size_id": "INTEGER",  # Identificador del talle (puede ser NULL si no aplica).
            "color_id": "INTEGER",  # Identificador del color (puede ser NULL si no aplica).
            "branch_id": "INTEGER NOT NULL",  # Identificador de la sucursal.
            "quantity": "INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0)",  # Cantidad específica de esta variante.
            "variant_barcode": "TEXT",  # Código de barras único para esta variante específica (talle + color).
            "last_updated": "TEXT DEFAULT CURRENT_TIMESTAMP",  # Fecha de última actualización.
        },
        "foreign_keys": [
            {  # Relación con la tabla de productos.
                "column": "product_id",
                "reference_table": TABLES.PRODUCTS,
                "reference_column": "id",
                "export_column_name": "product_name",
            },
            {  # Relación con la tabla de talles.
                "column": "size_id",
                "reference_table": TABLES.SIZES,
                "reference_column": "id",
                "export_column_name": "size_name",
            },
            {  # Relación con la tabla de colores.
                "column": "color_id",
                "reference_table": TABLES.COLORS,
                "reference_column": "id",
                "export_column_name": "color_name",
            },
            {  # Relación con la tabla de sucursales.
                "column": "branch_id",
                "reference_table": TABLES.STORAGE,
                "reference_column": "id",
                "export_column_name": "name",
            },
        ],
    },
    TABLES.INVENTORY_MOVEMETNS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada movimiento de inventario.
            "inventory_movements_group_id": "INTEGER NOT NULL",  # Identificador del grupo de transferencia.
            "product_id": "INTEGER NOT NULL",  # Identificador del producto movido.
            "quantity": "INTEGER NOT NULL CHECK (quantity > 0)",  # Cantidad de productos movidos, siempre positiva.
            "discount": "REAL DEFAULT 0.0",  # Descuento aplicado al producto
            "subtotal": "REAL NOT NULL",  # Subtotal para el producto (precio * cantidad)
            "total": "REAL NOT NULL",  # Total final después de aplicar descuentos
            "movement_date": "TEXT DEFAULT CURRENT_TIMESTAMP",  # Fecha y hora del movimiento de inventario.
        },
        "foreign_keys": [
            {  # Relación con la tabla de grupos de transferencia.
                "column": "inventory_movements_group_id",
                "reference_table": TABLES.INVENTORY_MOVEMETNS_GROUPS,
                "reference_column": "id",
                "export_column_name": "id",
            },
            {  # Relación con la tabla de productos.
                "column": "product_id",
                "reference_table": TABLES.PRODUCTS,
                "reference_column": "id",
                "export_column_name": "barcode",
            },
        ],
    },
    TABLES.INVENTORY_MOVEMETNS_GROUPS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada grupo de transferencia.
            "origin_branch_id": "INTEGER NOT NULL",  # ID de la sucursal de origen.
            "destination_branch_id": "INTEGER NOT NULL",  # ID de la sucursal de destino.
            "status": "TEXT NOT NULL DEFAULT 'empacado'",  # Estado: empacado, en_transito, entregado, recibido, no_recibido
            "movement_type": "TEXT NOT NULL DEFAULT 'transfer'",  # Tipo: transfer, shipment, delivery
            "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",  # Fecha y hora de la creación del grupo de transferencia.
            "updated_at": "TEXT DEFAULT CURRENT_TIMESTAMP",  # Fecha y hora de la última actualización.
            "shipped_at": "TEXT",  # Fecha y hora de envío (cuando cambia a en_transito).
            "delivered_at": "TEXT",  # Fecha y hora de entrega (cuando cambia a entregado).
            "received_at": "TEXT",  # Fecha y hora de recepción (cuando se confirma llegada).
            "created_by_user_id": "INTEGER",  # Usuario que creó el movimiento.
            "updated_by_user_id": "INTEGER",  # Usuario que realizó la última actualización.
            "notes": "TEXT",  # Comentarios adicionales sobre la transferencia.
        },
        "foreign_keys": [
            {  # Relación con la sucursal de origen.
                "column": "origin_branch_id",
                "reference_table": TABLES.STORAGE,
                "reference_column": "id",
                "export_column_name": "name",
            },
            {  # Relación con la sucursal de destino.
                "column": "destination_branch_id",
                "reference_table": TABLES.STORAGE,
                "reference_column": "id",
                "export_column_name": "name",
            },
            {  # Usuario que creó el movimiento.
                "column": "created_by_user_id",
                "reference_table": TABLES.USERS,
                "reference_column": "id",
                "export_column_name": "username",
            },
            {  # Usuario que actualizó el movimiento.
                "column": "updated_by_user_id",
                "reference_table": TABLES.USERS,
                "reference_column": "id",
                "export_column_name": "username",
            },
        ],
    },
    TABLES.RESPONSABILIDADES_AFIP: {
        "columns": {
            "id": "INTEGER PRIMARY KEY",  # Identificador único para cada responsabilidad, se establece como clave primaria.
            "codigo": "INTEGER NOT NULL",  # Código de responsabilidad, requerido.
            "descripcion": "TEXT NOT NULL",  # Descripción de la responsabilidad, requerida.
        }
    },
    TABLES.BRANDS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único para cada marca, se incrementa automáticamente.
            "brand_name": "TEXT NOT NULL UNIQUE",  # Nombre de la marca, debe ser único y no nulo.
            "description": "TEXT",  # Descripción de la marca, opcional.
            "creation_date": "TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))",  # Fecha de creación del registro, se establece por defecto a la fecha y hora actuales.
            "last_modified_date": "TEXT",  # Fecha de la última modificación de la marca.
        }
    },
    TABLES.PURCHASES: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único de la compra
            "entity_id": "INTEGER",  # Id de la entidad (proveedor)
            "purchase_date": "timestamp",  # Fecha y hora de la compra
            "subtotal": "REAL NOT NULL",  # Suma total antes de descuentos
            "discount": "REAL DEFAULT 0.0",  # Total de descuentos aplicados
            "total": "REAL NOT NULL",  # Total final después de aplicar descuentos
            "invoice_number": "TEXT",  # Número de factura de la compra
            "notes": "TEXT",  # Nota de texto para dejar comentarios
            "file_id": "INTEGER",  # Id del archivo adjunto de la compra
            "status": "TEXT DEFAULT 'Pendiente de entrega'",  # Estado de la compra: 'Pendiente de entrega', 'Recibido', 'Cancelado'
            "delivery_date": "timestamp",  # Fecha de entrega/recepción de la compra
            "pay": "BOOLEAN",  # Indica si la compra fue pagada o no
        },
        "foreign_keys": [
            {  # Relación con tabla de entidades (proveedores)
                "column": "entity_id",
                "reference_table": TABLES.ENTITIES,
                "reference_column": "id",
                "export_column_name": "entity_name",
            },
            {  # Relación con tabla de archivos si es necesario
                "column": "file_id",
                "reference_table": TABLES.FILE_ATTACHMENTS,
                "reference_column": "id",
                "export_column_name": "file_name",
            },
        ],
    },
    TABLES.PURCHASES_DETAIL: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único del detalle de la compra
            "purchase_id": "INTEGER NOT NULL",  # ID de la compra relacionada
            "product_id": "INTEGER",  # ID del producto
            "cost_price": "REAL NOT NULL",  # Precio de costo del producto en el momento de la compra
            "quantity": "INTEGER NOT NULL CHECK (quantity > 0)",  # Cantidad de productos comprados
            "discount": "REAL DEFAULT 0.0",  # Descuento aplicado al producto
            "subtotal": "REAL NOT NULL",  # Subtotal para el producto (precio * cantidad)
            "metadata": "TEXT",  # Información adicional de la compra
        },
        "foreign_keys": [
            {  # Relación con la tabla de ventas
                "column": "purchase_id",
                "reference_table": TABLES.PURCHASES,
                "reference_column": "id",
                "export_column_name": "id",
            },
            {  # Relación a la tabla de productos
                "column": "product_id",
                "reference_table": TABLES.PRODUCTS,
                "reference_column": "id",
                "export_column_name": "product_name",
            },
        ],
    },
    TABLES.PURCHASES_PAYMENTS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "payment_method_id": "INTEGER NOT NULL",
            "provider_id": "INTEGER NOT NULL",
            "amount": "REAL NOT NULL",  # Changed from INTEGER to REAL for decimal amounts
            "file_id": "INTEGER",
            "transaction_number": "TEXT",  # Changed from INTEGER to TEXT for flexibility
            "payment_date": "TIMESTAMP",  # When the payment was made
            "description": "TEXT",  # Payment description/notes
            "created_at": "TIMESTAMP",
            "updated_at": "TIMESTAMP",
        },
        "foreign_keys": [
            {
                "column": "payment_method_id",
                "reference_table": TABLES.BANKS_PAYMENT_METHODS,
                "reference_column": "id",
                "export_column_name": "payment_method_name",
            },
            {
                "column": "provider_id",
                "reference_table": TABLES.ENTITIES,
                "reference_column": "id",
                "export_column_name": "entity_name",
            },
            {
                "column": "file_id",
                "reference_table": TABLES.FILE_ATTACHMENTS,
                "reference_column": "id",
                "export_column_name": "file_name",
            },
        ],
    },
    TABLES.SALES: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único de la venta
            "customer_id": "INTEGER",  # Id del cliente (puede ser NULL para ventas sin cliente registrado)
            "employee_id": "INTEGER NOT NULL",  # Id del empleado que realizó la venta
            "cashier_user_id": "INTEGER NOT NULL",  # Id del usuario/cajero que procesó la venta
            "storage_id": "INTEGER NOT NULL",  # Id de la sucursal donde se realizó la venta
            "sale_date": "TEXT DEFAULT CURRENT_TIMESTAMP",  # Fecha y hora de la venta
            "subtotal": "REAL NOT NULL",  # Suma total antes de descuentos e impuestos
            "tax_amount": "REAL DEFAULT 0.0",  # Monto total de impuestos
            "discount": "REAL DEFAULT 0.0",  # Total de descuentos aplicados
            "total": "REAL NOT NULL",  # Total final después de aplicar descuentos e impuestos
            "payment_reference": "TEXT",  # Referencia del pago (número de transacción, comprobante, etc.)
            "invoice_number": "TEXT",  # Número de factura si se emitió
            "receipt_number": "TEXT",  # Número de ticket/recibo
            "notes": "TEXT",  # Notas adicionales sobre la venta
            "status": "TEXT DEFAULT 'Completada'",  # Estado de la venta: 'Completada', 'Cancelada', 'Pendiente', 'Reembolsada'
            "refund_reason": "TEXT",  # Razón del reembolso si aplica
            "refunded_at": "TEXT",  # Fecha y hora del reembolso
            "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",  # Fecha de creación del registro
            "updated_at": "TEXT DEFAULT CURRENT_TIMESTAMP",  # Fecha de última actualización
            "en_tienda_online": "BOOLEAN",  # Indica si se compro en la tienda lonline
            "origin": "TEXT DEFAULT 'local'", # Valores: 'local', 'web'
            "shipping_address": "TEXT",       # Dirección de envío (solo si es web)
            "shipping_status": "TEXT",        # 'pendiente', 'enviado', 'entregado'
            "external_payment_id": "TEXT"     # El ID que te da MercadoPago/Stripe
            "web_user_id": "INTEGER", # Para vincular con WEB_USERS
            "shipping_cost": "REAL DEFAULT 0", # Por si cobras envío aparte
            "delivery_type": "TEXT DEFAULT 'envio'", # Valores sugeridos: 'domicilio', 'sucursal' (retiro)
        },
        "foreign_keys": [
            {  # Relación con tabla de clientes (entidades)
                "column": "customer_id",
                "reference_table": TABLES.ENTITIES,
                "reference_column": "id",
                "export_column_name": "entity_name",
            },
            {  # Relación con tabla de empleados (entidades)
                "column": "employee_id",
                "reference_table": TABLES.ENTITIES,
                "reference_column": "id",
                "export_column_name": "entity_name",
            },
            {  # Relación con tabla de usuarios (cajero)
                "column": "cashier_user_id",
                "reference_table": TABLES.USERS,
                "reference_column": "id",
                "export_column_name": "username",
            },
            {  # Relación con tabla de sucursales
                "column": "storage_id",
                "reference_table": TABLES.STORAGE,
                "reference_column": "id",
                "export_column_name": "name",
            },
            {  # Relación con tabla de usuarios (cajero)
                "column": "web_user_id",
                "reference_table": TABLES.WEB_USERS,
                "reference_column": "id",
                "export_column_name": "username",
            },
        ],
    },
    TABLES.SALES_DETAIL: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # Identificador único del detalle de la venta
            "sale_id": "INTEGER NOT NULL",  # ID de la venta relacionada
            "product_id": "INTEGER NOT NULL",  # ID del producto vendido
            "variant_id": "INTEGER",  # ID de la variante específica (talle/color) si aplica
            "product_name": "TEXT NOT NULL",  # Nombre del producto al momento de la venta (histórico)
            "product_code": "TEXT",  # Código del producto al momento de la venta
            "size_name": "TEXT",  # Nombre del talle vendido (histórico)
            "color_name": "TEXT",  # Nombre del color vendido (histórico)
            "cost_price": "REAL NOT NULL",  # Precio de costo del producto al momento de la venta
            "sale_price": "REAL NOT NULL",  # Precio de venta unitario del producto
            "quantity": "INTEGER NOT NULL CHECK (quantity > 0)",  # Cantidad de productos vendidos
            "discount_percentage": "REAL DEFAULT 0.0",  # Porcentaje de descuento aplicado
            "discount_amount": "REAL DEFAULT 0.0",  # Monto del descuento aplicado
            "tax_percentage": "REAL DEFAULT 0.0",  # Porcentaje de impuesto aplicado
            "tax_amount": "REAL DEFAULT 0.0",  # Monto del impuesto aplicado
            "subtotal": "REAL NOT NULL",  # Subtotal para el producto (precio * cantidad)
            "total": "REAL NOT NULL",  # Total final después de aplicar descuentos e impuestos
            "profit_margin": "REAL",  # Margen de ganancia (sale_price - cost_price)
            "barcode_scanned": "TEXT",  # Código de barras si es un regalo
            "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",  # Fecha de creación del registro
        },
        "foreign_keys": [
            {  # Relación con la tabla de ventas
                "column": "sale_id",
                "reference_table": TABLES.SALES,
                "reference_column": "id",
                "export_column_name": "id",
            },
            {  # Relación con la tabla de productos
                "column": "product_id",
                "reference_table": TABLES.PRODUCTS,
                "reference_column": "id",
                "export_column_name": "product_name",
            },
            {  # Relación con la tabla de variantes de stock
                "column": "variant_id",
                "reference_table": TABLES.WAREHOUSE_STOCK_VARIANTS,
                "reference_column": "id",
                "export_column_name": "id",
            },
        ],
    },
    TABLES.SALES_TRACKING_HISTORY: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "sale_id": "INTEGER NOT NULL",      # Vinculado a la venta
            "status": "TEXT NOT NULL",          # El estado (preparando, despachado, etc.)
            "description": "TEXT",              # Ej: "Empaquetado por Juan", "Entregado a Correo Andreani"
            "location": "TEXT",                 # Ej: "Sucursal Centro", "Centro de Distribución"
            "changed_by_user_id": "INTEGER",    # Quién actualizó el estado
            "created_at": "timestamp DEFAULT CURRENT_TIMESTAMP", # Cuándo ocurrió
        },
        "foreign_keys": [
            {
                "column": "sale_id",
                "reference_table": TABLES.SALES,
                "reference_column": "id",
                "export_column_name": "id",
            },
            {
                "column": "changed_by_user_id",
                "reference_table": TABLES.USERS,
                "reference_column": "id",
                "export_column_name": "username",
            },
        ],
    },
    TABLES.USERSXSTORAGE: {
        "columns": {
            "id_user": "INTEGER NOT NULL",  # Identificador del usuario.
            "id_storage": "INTEGER NOT NULL",  # Identificador del almacén.
        },
        "primary_key": [
            "id_user",
            "id_storage",
        ],  # Definimos la clave primaria compuesta
        "foreign_keys": [
            {  # Relación con la tabla de usuarios.
                "column": "id_user",
                "reference_table": TABLES.USERS,
                "reference_column": "id",
                "export_column_name": "username",  # <- columna de referencia cuando se exportan tablas
            },
            {  # Relación con la tabla de almacenes.
                "column": "id_storage",
                "reference_table": TABLES.STORAGE,
                "reference_column": "id",
                "export_column_name": "name",  # <- columna de referencia cuando se exportan tablas
            },
        ],
    },
    TABLES.SESSIONS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",  # ID único de la sesión
            "user_id": "INTEGER NOT NULL",  # ID del usuario logueado
            "storage_id": "INTEGER",  # ID de la sucursal seleccionada (nullable para login sin sucursales)
            "session_token": "TEXT NOT NULL UNIQUE",  # Token único de sesión
            "login_time": "TEXT DEFAULT CURRENT_TIMESTAMP",  # Hora de inicio de sesión
            "last_activity": "TEXT DEFAULT CURRENT_TIMESTAMP",  # Última actividad
            "is_active": "INTEGER DEFAULT 1",  # Sesión activa (1) o inactiva (0)
            "ip_address": "TEXT",  # Dirección IP del cliente
            "user_agent": "TEXT",  # Información del navegador/cliente
        },
        "foreign_keys": [
            {  # Relación con la tabla de usuarios.
                "column": "user_id",
                "reference_table": TABLES.USERS,
                "reference_column": "id",
                "export_column_name": "username",
            },
            {  # Relación con la tabla de almacenes.
                "column": "storage_id",
                "reference_table": TABLES.STORAGE,
                "reference_column": "id",
                "export_column_name": "name",
            },
        ],
    },
    TABLES.PAYMENT_METHODS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "method_name": "TEXT NOT NULL UNIQUE",
            "display_name": "TEXT NOT NULL",
            "description": "TEXT",
            "is_active": "BOOLEAN NOT NULL DEFAULT 1",
            "requires_reference": "BOOLEAN NOT NULL DEFAULT 0",
            "icon_name": "TEXT",
            "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
            "provider_use_it": "BOOLEAN",
            "client_use_it": "BOOLEAN",
        },
        "foreign_keys": [],
    },
    TABLES.BANKS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT NOT NULL",
            "swift_code": "NULL",
        },
        "foreign_keys": [],
    },
    # Tabla puente: relación muchos-a-muchos entre bancos y métodos de pago
    TABLES.BANKS_PAYMENT_METHODS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "bank_id": "INTEGER NOT NULL",
            "payment_method_id": "INTEGER NOT NULL",
            "amount": "numeric(12,2) [0.00] NOT NULL",
        },
        "foreign_keys": [
            {
                "column": "bank_id",
                "reference_table": TABLES.BANKS,
                "reference_column": "id",
                "export_column_name": "name",
            },
            {
                "column": "payment_method_id",
                "reference_table": TABLES.PAYMENT_METHODS,
                "reference_column": "id",
                "export_column_name": "method_name",
            },
        ],
    },
    TABLES.SALES_PAYMENTS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "sale_id": "INTEGER NOT NULL",
            "payment_method_id": "INTEGER NOT NULL",
            "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
        },
        "foreign_keys": [
            {
                "column": "sale_id",
                "reference_table": TABLES.SALES,
                "reference_column": "id",
                "export_column_name": "sale_id",
            },
            {
                "column": "payment_method",
                "reference_table": TABLES.BANKS_PAYMENT_METHODS,
                "reference_column": "id",
                "export_column_name": "method_name",
            },
        ],
    },
    TABLES.WEB_VARIANTS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "product_id": "INTEGER NOT NULL",
            "size_id": "INTEGER NOT NULL",
            "color_id": "INTEGER NOT NULL",
            "displayed_stock": "INTEGER DEFAULT 0", 
            "is_active": "BOOLEAN DEFAULT 1",
            "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP"
        },
        "foreign_keys": [
             {
                "column": "product_id",
                "reference_table": TABLES.PRODUCTS,
                "reference_column": "id",
                "export_column_name": "product_name",
            },
            {
                "column": "size_id",
                "reference_table": TABLES.SIZES,
                "reference_column": "id",
                "export_column_name": "size_name",
            },
            {
                "column": "color_id",
                "reference_table": TABLES.COLORS,
                "reference_column": "id",
                "export_column_name": "color_name",
            },
        ],
        # constraint para evitar duplicados de variantes en la web
        "constraints": ["UNIQUE(product_id, size_id, color_id)"] 
    },
    TABLES.DISCOUNTS: {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "discount_type": "TEXT NOT NULL",
            "target_id": "INTEGER",
            "target_name": "TEXT",
            "discount_percentage": "REAL NOT NULL",
            "start_date": "timestamp",
            "end_date": "timestamp",
            "is_active": "BOOLEAN DEFAULT 1",
            "apply_to_children": "BOOLEAN DEFAULT 0",
            "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
            "created_by_user_id": "INTEGER",
            "updated_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
        },
        "foreign_keys": [
            {
                "column": "created_by_user_id",
                "reference_table": TABLES.USERS,
                "reference_column": "id",
                "export_column_name": "username",
            },
        ],
    },
}
