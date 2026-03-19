"""
Paq.ar - Correo Argentino API v2.0
Servicio de integración HTTP.

Referencia oficial:
  - Producción : https://api.correoargentino.com.ar/paqar/v1/
  - Test       : https://apitest.correoargentino.com.ar/paqar/v1/

Headers obligatorios en todas las peticiones:
  Authorization : Apikey <TOKEN>
  agreement     : <AGREEMENT_ID>

Variables de entorno requeridas (.env):
  PAQAR_API_KEY      → Token de autenticación
  PAQAR_AGREEMENT_ID → ID de convenio/acuerdo
  PAQAR_ENV          → "production" | "test"  (default: "test")
"""

import os
import re
import base64
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuración de entornos
# ---------------------------------------------------------------------------

PAQAR_BASE_URLS: Dict[str, str] = {
    "production": "https://api.correoargentino.com.ar/paqar/v1",
    "test":       "https://apitest.correoargentino.com.ar/paqar/v1",
}


def _get_base_url() -> str:
    """Devuelve la URL base según la variable de entorno PAQAR_ENV."""
    env = os.getenv("PAQAR_ENV", "test").strip().lower()
    if env not in PAQAR_BASE_URLS:
        raise ValueError(
            f"PAQAR_ENV inválido: '{env}'. Debe ser 'production' o 'test'."
        )
    return PAQAR_BASE_URLS[env]


# ---------------------------------------------------------------------------
# Enum de provincias argentinas (código oficial Correo Argentino)
# ---------------------------------------------------------------------------

class Provincia(str, Enum):
    """
    Códigos de provincia según la especificación de Paq.ar.
    Todos los valores son letras mayúsculas de una sola letra.
    Nota: las letras I y O no están asignadas (evitan confusión con 1 y 0).
    """
    SALTA                      = "A"
    BUENOS_AIRES               = "B"
    CIUDAD_AUTONOMA_BS_AS      = "C"
    SAN_LUIS                   = "D"
    ENTRE_RIOS                 = "E"
    LA_RIOJA                   = "F"
    SANTIAGO_DEL_ESTERO        = "G"
    CHACO                      = "H"
    SAN_JUAN                   = "J"
    CATAMARCA                  = "K"
    LA_PAMPA                   = "L"
    MENDOZA                    = "M"
    MISIONES                   = "N"
    FORMOSA                    = "P"
    NEUQUEN                    = "Q"
    RIO_NEGRO                  = "R"
    SANTA_FE                   = "S"
    TUCUMAN                    = "T"
    CHUBUT                     = "U"
    TIERRA_DEL_FUEGO           = "V"
    CORRIENTES                 = "W"
    CORDOBA                    = "X"
    JUJUY                      = "Y"
    SANTA_CRUZ                 = "Z"

    @classmethod
    def nombre(cls, codigo: str) -> str:
        """
        Devuelve el nombre legible de la provincia a partir del código.

        Ejemplo:
            >>> Provincia.nombre("B")
            'Provincia de Buenos Aires'
        """
        _nombres: Dict[str, str] = {
            "A": "Salta",
            "B": "Provincia de Buenos Aires",
            "C": "Ciudad Autónoma de Buenos Aires",
            "D": "San Luis",
            "E": "Entre Ríos",
            "F": "La Rioja",
            "G": "Santiago del Estero",
            "H": "Chaco",
            "J": "San Juan",
            "K": "Catamarca",
            "L": "La Pampa",
            "M": "Mendoza",
            "N": "Misiones",
            "P": "Formosa",
            "Q": "Neuquén",
            "R": "Río Negro",
            "S": "Santa Fe",
            "T": "Tucumán",
            "U": "Chubut",
            "V": "Tierra del Fuego",
            "W": "Corrientes",
            "X": "Córdoba",
            "Y": "Jujuy",
            "Z": "Santa Cruz",
        }
        codigo = codigo.upper().strip()
        nombre = _nombres.get(codigo)
        if nombre is None:
            raise ValueError(f"Código de provincia desconocido: '{codigo}'")
        return nombre

    @classmethod
    def todos(cls) -> Dict[str, str]:
        """Devuelve el diccionario completo {código: nombre}."""
        return {p.value: cls.nombre(p.value) for p in cls}


# ---------------------------------------------------------------------------
# Excepción específica del dominio
# ---------------------------------------------------------------------------

class PaqarOrderError(Exception):
    """Se lanza cuando la creación de orden no retorna un trackingNumber válido."""


# ---------------------------------------------------------------------------
# DTOs  (Data Transfer Objects / Pydantic v2)
#
# Orden de definición: ParcelDTO → AddressDTO → ReceiverDTO/SenderDTO
#   → OrderRequestDTO
# Todos se definen ANTES de PaqarClient para que la anotación de tipo
# en create_order() pueda resolverlos sin forward-references.
# ---------------------------------------------------------------------------

# Patrón ISO 8601 estricto: YYYY-MM-DDTHH:mm:ss-03:00
_ISO8601_RE = re.compile(
    r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])"
    r"T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d-03:00$"
)


class ParcelDTO(BaseModel):
    """
    Representa UN paquete (parcel).

    Reglas de validación:
    - productWeight : entero positivo, máximo 5 dígitos  (1 – 99 999 gramos).
    - height / width / depth : entero positivo, máximo 3 dígitos (1 – 999 cm).

    Nota crítica de la API: aunque el endpoint acepta un array de parcels,
    SOLO procesa el primero e ignora el resto. ``PaqarClient.create_order()``
    aplica este recorte automáticamente y emite un warning si se envían más.
    """

    productWeight: int
    height:        int
    width:         int
    depth:         int

    @field_validator("productWeight")
    @classmethod
    def validate_weight(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("productWeight debe ser mayor a 0.")
        if v > 99_999:
            raise ValueError(
                f"productWeight '{v}' supera el máximo de 5 dígitos enteros (99 999 g)."
            )
        return v

    @field_validator("height", "width", "depth")
    @classmethod
    def validate_dimension(cls, v: int, info) -> int:  # noqa: ANN001
        field = info.field_name
        if v <= 0:
            raise ValueError(f"'{field}' debe ser mayor a 0.")
        if v > 999:
            raise ValueError(
                f"'{field}' = {v} supera el máximo de 3 dígitos enteros (999 cm)."
            )
        return v


class AddressDTO(BaseModel):
    """
    Dirección postal.

    El campo ``state`` acepta únicamente los códigos de 1 letra definidos
    en el enum ``Provincia`` (A, B, C, D, E, F, G, H, J, K, L, M, N, P,
    Q, R, S, T, U, V, W, X, Y, Z).  Se normaliza automáticamente a
    mayúsculas antes de validar.
    """

    street:    str
    number:    str
    floor:     Optional[str] = None
    apartment: Optional[str] = None
    city:      str
    state:     str   # código de 1 letra según Provincia enum
    zipCode:   str

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        codigo = v.upper().strip()
        valid_codes = {p.value for p in Provincia}
        if codigo not in valid_codes:
            raise ValueError(
                f"Código de provincia inválido: '{v}'. "
                f"Valores aceptados: {sorted(valid_codes)}."
            )
        return codigo


class ReceiverDTO(BaseModel):
    """Datos del destinatario del envío."""

    name:      str
    surname:   str
    email:     str
    phone:     str
    docType:   Literal["DNI", "CUIT", "CUIL", "PASAPORTE"] = "DNI"
    docNumber: str
    address:   AddressDTO


class SenderDTO(BaseModel):
    """Datos del remitente (tienda / vendedor)."""

    name:      str
    surname:   str
    email:     str
    phone:     str
    docType:   Literal["DNI", "CUIT", "CUIL", "PASAPORTE"] = "CUIT"
    docNumber: str
    address:   AddressDTO


class OrderRequestDTO(BaseModel):
    """
    Payload completo para el alta de orden (POST /orders).

    Validaciones aplicadas:
    ┌──────────────────┬──────────────────────────────────────────────────────┐
    │ Campo            │ Regla                                                │
    ├──────────────────┼──────────────────────────────────────────────────────┤
    │ deliveryType     │ Literal: 'agency' | 'locker' | 'homeDelivery'        │
    │ saleDate         │ ISO 8601 estricto: YYYY-MM-DDTHH:mm:ss-03:00         │
    │ *.address.state  │ Código de provincia de 1 letra (enum Provincia)      │
    │ parcels[0].      │                                                      │
    │   productWeight  │ Entero 1-99999 (máx 5 dígitos, gramos)               │
    │   height/width/  │                                                      │
    │   depth          │ Entero 1-999   (máx 3 dígitos, cm)                   │
    │ parcels          │ ≥ 1 elemento; solo el primero es procesado por la API │
    └──────────────────┴──────────────────────────────────────────────────────┘
    """

    deliveryType:   Literal["agency", "locker", "homeDelivery"]
    saleDate:       str
    receiver:       ReceiverDTO
    sender:         SenderDTO
    parcels:        List[ParcelDTO]

    # Campos opcionales frecuentes
    declaredValue:  Optional[float] = None
    observations:   Optional[str]   = None

    @field_validator("saleDate")
    @classmethod
    def validate_sale_date(cls, v: str) -> str:
        if not _ISO8601_RE.match(v):
            raise ValueError(
                f"saleDate '{v}' no cumple el formato ISO 8601 requerido: "
                "YYYY-MM-DDTHH:mm:ss-03:00  (ej: '2026-03-18T09:00:00-03:00')."
            )
        return v

    @field_validator("parcels")
    @classmethod
    def validate_parcels(cls, v: List[ParcelDTO]) -> List[ParcelDTO]:
        if not v:
            raise ValueError("Se requiere al menos un parcel.")
        if len(v) > 1:
            logger.warning(
                "Se recibieron %d parcels. Paq.ar solo procesa el primero.", len(v)
            )
        return v


# ---------------------------------------------------------------------------
# DTOs para Obtener Rótulo  (POST /labels)
# ---------------------------------------------------------------------------

# Formatos de rótulo válidos que acepta la API
LABEL_FORMATS = frozenset({"10x15", "label"})


class LabelRequestItem(BaseModel):
    """
    Un elemento del array que POSTea a /labels.

    Cada objeto identifica unívocamente un envío ya creado mediante
    ``sellerId`` (ID del vendedor/acuerdo) y ``trackingNumber``
    (devuelto por ``create_order``).
    """

    sellerId:       str
    trackingNumber: str


class LabelResult(BaseModel):
    """
    Elemento de la respuesta por cada rótulo solicitado.

    Campos relevantes:
    - ``result``     : 'OK' si el rótulo se generó correctamente.
    - ``fileBase64`` : string Base64 del PDF del rótulo (solo presente si result='OK').
    - ``trackingNumber`` : tracking que identifica a qué envío pertenece.
    - ``error``      : mensaje de error si result != 'OK'.
    """

    trackingNumber: str
    result:         str
    fileBase64:     Optional[str] = None
    error:          Optional[str] = None

    @property
    def is_ok(self) -> bool:  # noqa: D102
        return self.result.upper() == "OK"


class LabelResponse(BaseModel):
    """Respuesta completa de POST /labels (lista de LabelResult)."""

    items: List[LabelResult]

    @property
    def successful(self) -> List[LabelResult]:
        """Retorna solo los rótulos con result='OK'."""
        return [i for i in self.items if i.is_ok]

    @property
    def failed(self) -> List[LabelResult]:
        """Retorna los rótulos con result != 'OK'."""
        return [i for i in self.items if not i.is_ok]


# ---------------------------------------------------------------------------
# Cliente HTTP base
# ---------------------------------------------------------------------------

class PaqarClient:
    """
    Cliente HTTP asíncrono para la API v2.0 de Paq.ar (Correo Argentino).

    Gestiona:
    - Headers obligatorios (Authorization y agreement) en TODAS las peticiones.
    - Elección de entorno (producción / test) vía variable PAQAR_ENV.
    - Timeout configurable.
    - Manejo centralizado de errores HTTP.

    Uso básico (dentro de un endpoint FastAPI):
        async with PaqarClient() as client:
            tracking = await client.create_order(order_dto)

    Uso con instancia reutilizable:
        client = PaqarClient()
        await client.open()
        ...
        await client.close()
    """

    DEFAULT_TIMEOUT = 30.0  # segundos

    def __init__(
        self,
        api_key:      Optional[str] = None,
        agreement_id: Optional[str] = None,
        timeout:      float = DEFAULT_TIMEOUT,
    ) -> None:
        self._api_key      = api_key      or os.getenv("PAQAR_API_KEY", "")
        self._agreement_id = agreement_id or os.getenv("PAQAR_AGREEMENT_ID", "")
        self._base_url     = _get_base_url()
        self._timeout      = timeout
        self._http: Optional[httpx.AsyncClient] = None

        if not self._api_key:
            logger.warning("PAQAR_API_KEY no está configurada.")
        if not self._agreement_id:
            logger.warning("PAQAR_AGREEMENT_ID no está configurada.")

    def _build_headers(self) -> Dict[str, str]:
        """Construye los headers obligatorios para todas las peticiones."""
        return {
            "Authorization": f"Apikey {self._api_key}",
            "agreement":     self._agreement_id,
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }

    async def open(self) -> None:
        """Abre la sesión HTTP (necesario si no se usa como context manager)."""
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=self._base_url,
                headers=self._build_headers(),
                timeout=self._timeout,
            )

    async def close(self) -> None:
        """Cierra la sesión HTTP."""
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def __aenter__(self) -> "PaqarClient":
        await self.open()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    def _ensure_open(self) -> None:
        if self._http is None:
            raise RuntimeError(
                "PaqarClient no está abierto. "
                "Usá 'async with PaqarClient() as client:' o llamá a 'await client.open()' primero."
            )

    @staticmethod
    def _handle_response(response: httpx.Response) -> Dict[str, Any]:
        """
        Valida el código de estado HTTP y retorna el JSON de la respuesta.
        Lanza httpx.HTTPStatusError ante respuestas 4xx/5xx.
        """
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Paq.ar API error %s [%s] → %s",
                exc.response.status_code,
                exc.request.url,
                exc.response.text,
            )
            raise

        # Algunas respuestas exitosas pueden ser vacías (ej: 204 No Content)
        if response.status_code == 204 or not response.content:
            return {}

        return response.json()

    # ------------------------------------------------------------------
    # Métodos HTTP genéricos
    # ------------------------------------------------------------------

    async def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """GET request al endpoint dado (relativo a la URL base)."""
        self._ensure_open()
        response = await self._http.get(endpoint, params=params)
        return self._handle_response(response)

    async def post(
        self, endpoint: str, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """POST request con body JSON."""
        self._ensure_open()
        response = await self._http.post(endpoint, json=payload or {})
        return self._handle_response(response)

    async def put(
        self, endpoint: str, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """PUT request con body JSON."""
        self._ensure_open()
        response = await self._http.put(endpoint, json=payload or {})
        return self._handle_response(response)

    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE request."""
        self._ensure_open()
        response = await self._http.delete(endpoint)
        return self._handle_response(response)

    # ------------------------------------------------------------------
    # Métodos específicos de dominio
    # ------------------------------------------------------------------

    async def validate_credentials(self) -> Dict[str, Any]:
        """
        Valida las credenciales configuradas realizando un GET a /auth.

        Retorna el JSON de respuesta si las credenciales son válidas.
        Lanza httpx.HTTPStatusError con status 401 si son inválidas.

        Ejemplo de uso:
            async with PaqarClient() as client:
                result = await client.validate_credentials()
                print(result)  # {"status": "ok", ...}
        """
        logger.info(
            "Validando credenciales Paq.ar en entorno '%s' → %s/auth",
            os.getenv("PAQAR_ENV", "test"),
            self._base_url,
        )
        try:
            result = await self.get("/auth")
            logger.info("Credenciales Paq.ar válidas.")
            return result
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                logger.error(
                    "Credenciales Paq.ar inválidas (401 Unauthorized). "
                    "Verificá PAQAR_API_KEY y PAQAR_AGREEMENT_ID en el .env."
                )
            raise

    async def create_order(self, order: OrderRequestDTO) -> str:
        """
        Alta de orden → POST /orders

        Valida el DTO, construye el payload, envía la petición y retorna
        el ``trackingNumber`` generado por Correo Argentino (status 200 OK).

        Comportamiento especial de Paq.ar:
            La API acepta un array ``parcels`` pero SOLO procesa el primer
            elemento. Este método descarta silenciosamente cualquier elemento
            adicional y emite un warning en el log.

        Args:
            order: DTO validado con todos los datos de la orden.

        Returns:
            trackingNumber como string (ej: "PQ123456789AR").

        Raises:
            pydantic.ValidationError  → si el DTO no supera las validaciones.
            PaqarOrderError           → si la API responde 200 pero no incluye
                                        trackingNumber en el cuerpo.
            httpx.HTTPStatusError     → ante respuestas HTTP 4xx / 5xx.

        Ejemplo::

            order = OrderRequestDTO(
                deliveryType="homeDelivery",
                saleDate="2026-03-18T09:00:00-03:00",
                receiver=ReceiverDTO(...),
                sender=SenderDTO(...),
                parcels=[ParcelDTO(productWeight=500, height=10, width=20, depth=5)],
            )
            async with PaqarClient() as client:
                tracking = await client.create_order(order)
                print(tracking)  # "PQ123456789AR"
        """
        payload = order.model_dump(mode="json", exclude_none=True)

        # La API solo procesa el primer parcel; truncamos silenciosamente.
        if len(payload["parcels"]) > 1:
            logger.warning(
                "Paq.ar solo procesa el primer parcel. "
                "Se descartaron %d elemento(s) adicional(es).",
                len(payload["parcels"]) - 1,
            )
            payload["parcels"] = payload["parcels"][:1]

        logger.info(
            "Creando orden Paq.ar | tipo=%s | destinatario='%s %s'",
            order.deliveryType,
            order.receiver.name,
            order.receiver.surname,
        )

        response_data = await self.post("/orders", payload)

        tracking = response_data.get("trackingNumber")
        if not tracking:
            raise PaqarOrderError(
                "La API respondió con status 200 pero no incluyó 'trackingNumber'. "
                f"Respuesta completa: {response_data}"
            )

        logger.info("Orden creada exitosamente. trackingNumber: %s", tracking)
        return tracking

    async def get_labels(
        self,
        items: List[LabelRequestItem],
        label_format: Optional[str] = None,
    ) -> LabelResponse:
        """
        Obtener Rótulo → POST /labels

        Envía un POST cuyo body es un **array** de objetos
        ``{sellerId, trackingNumber}`` y retorna un ``LabelResponse``
        que encapsula la lista de resultados.

        Args:
            items:        Lista de ``LabelRequestItem`` a solicitar.
                          Se aceptan uno o más elementos.
            label_format: Formato de impresión del rótulo.
                          Valores válidos: ``"10x15"`` o ``"label"``.
                          Si es ``None`` o un valor no reconocido **no se
                          incluye** el parámetro en la petición.

        Returns:
            ``LabelResponse`` con la lista completa de resultados.
            Usá ``.successful`` y ``.failed`` para filtrar.

        Raises:
            httpx.HTTPStatusError → ante respuestas HTTP 4xx / 5xx.
            ValueError            → si ``items`` está vacío.

        Ejemplo::

            reqs = [
                LabelRequestItem(sellerId="MITIENDA", trackingNumber="PQ123456789AR"),
            ]
            async with PaqarClient() as client:
                response = await client.get_labels(reqs, label_format="10x15")
                for label in response.successful:
                    path = save_label_pdf(label.fileBase64, label.trackingNumber)
                    print(f"PDF guardado en: {path}")
                for label in response.failed:
                    print(f"Error en {label.trackingNumber}: {label.error}")
        """
        if not items:
            raise ValueError("Se requiere al menos un LabelRequestItem.")

        # Construir body: array de dicts planos
        body: List[Dict[str, str]] = [
            item.model_dump() for item in items
        ]

        # Query params: solo incluir labelFormat si el valor es válido
        params: Dict[str, str] = {}
        if label_format is not None:
            if label_format in LABEL_FORMATS:
                params["labelFormat"] = label_format
            else:
                logger.warning(
                    "labelFormat '%s' no es válido (aceptados: %s). "
                    "No se incluirá en la petición.",
                    label_format,
                    sorted(LABEL_FORMATS),
                )

        logger.info(
            "Solicitando %d rótulo(s) a Paq.ar | formato=%s",
            len(items),
            params.get("labelFormat", "<sin formato>"),
        )

        self._ensure_open()
        response = await self._http.post("/labels", json=body, params=params or None)
        raw_list: List[Dict[str, Any]] = self._handle_response(response)

        if not isinstance(raw_list, list):
            logger.error("Respuesta inesperada de /labels (no es una lista): %s", raw_list)
            raw_list = []

        results = [LabelResult(**item) for item in raw_list]

        ok_count  = sum(1 for r in results if r.is_ok)
        err_count = len(results) - ok_count
        logger.info(
            "Rótulos recibidos: %d OK, %d con error.", ok_count, err_count
        )

        return LabelResponse(items=results)

    # ------------------------------------------------------------------
    # Propiedades de utilidad
    # ------------------------------------------------------------------

    @property
    def environment(self) -> str:
        """Devuelve el entorno activo ('production' o 'test')."""
        return os.getenv("PAQAR_ENV", "test").strip().lower()

    @property
    def base_url(self) -> str:
        """Devuelve la URL base activa."""
        return self._base_url


# ---------------------------------------------------------------------------
# Función auxiliar: guardar rótulo Base64 como PDF en disco
# ---------------------------------------------------------------------------

def save_label_pdf(
    file_base64: str,
    tracking_number: str,
    output_dir: str = "labels",
) -> Path:
    """
    Decodifica el string Base64 recibido de la API y lo persiste como
    un archivo PDF en el sistema de archivos local.

    Args:
        file_base64:     String Base64 que representa el contenido del PDF.
        tracking_number: Número de tracking del envío (se usa como nombre
                         de archivo para facilitar su identificación).
        output_dir:      Ruta del directorio donde se guardará el archivo.
                         Se crea automáticamente si no existe.
                         Por defecto: ``"labels"`` (relativo al CWD).

    Returns:
        ``pathlib.Path`` apuntando al archivo PDF creado.

    Raises:
        ValueError    → si ``file_base64`` está vacío.
        Exception     → si ocurre un error de E/S al escribir el archivo.

    Ejemplo::

        path = save_label_pdf(label.fileBase64, label.trackingNumber)
        print(f"PDF guardado en: {path}")   # labels/PQ123456789AR.pdf

        # Con directorio personalizado:
        path = save_label_pdf(label.fileBase64, label.trackingNumber,
                              output_dir="/var/mykonos/labels")
    """
    if not file_base64:
        raise ValueError(
            f"file_base64 vacío para trackingNumber '{tracking_number}'. "
            "No se puede guardar el PDF."
        )

    # Asegurar que el directorio exista
    dest_dir = Path(output_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Nombre de archivo: sanitizar el tracking para evitar caracteres inválidos
    safe_name = re.sub(r"[^\w\-]", "_", tracking_number)
    pdf_path  = dest_dir / f"{safe_name}.pdf"

    try:
        pdf_bytes = base64.b64decode(file_base64)
    except Exception as exc:
        raise ValueError(
            f"Error al decodificar Base64 para '{tracking_number}': {exc}"
        ) from exc

    pdf_path.write_bytes(pdf_bytes)
    logger.info("Rótulo PDF guardado: %s (%d bytes)", pdf_path, len(pdf_bytes))
    return pdf_path


def save_labels_batch(
    label_response: LabelResponse,
    output_dir: str = "labels",
) -> Tuple[List[Path], List[str]]:
    """
    Guarda en lote todos los rótulos exitosos de un ``LabelResponse``.

    Args:
        label_response: Respuesta completa de ``get_labels()``.
        output_dir:     Directorio destino de los PDFs.

    Returns:
        Tupla ``(guardados, fallidos)`` donde:
        - ``guardados`` : lista de ``Path`` de los PDFs creados.
        - ``fallidos``  : lista de ``trackingNumber`` que tuvieron error.

    Ejemplo::

        saved, errors = save_labels_batch(label_response)
        print(f"{len(saved)} PDFs guardados, {len(errors)} errores.")
    """
    saved:   List[Path] = []
    failed:  List[str]  = []

    for label in label_response.failed:
        logger.warning(
            "Rótulo no disponible para '%s': %s",
            label.trackingNumber, label.error
        )
        failed.append(label.trackingNumber)

    for label in label_response.successful:
        try:
            path = save_label_pdf(label.fileBase64, label.trackingNumber, output_dir)
            saved.append(path)
        except Exception as exc:
            logger.error(
                "Error al guardar rótulo '%s': %s", label.trackingNumber, exc
            )
            failed.append(label.trackingNumber)

    return saved, failed
