"""Subir y bajar de Google Drive para la entrega a un editor externo.

Cada función que toca la red recibe el CLIENTE ya armado como parámetro
--nunca lo construye ella misma-- para poder probarse con un doble sin
tocar la red (spec 2026-09-18 §8). Quien arma el cliente real, con las
credenciales de Bruno, es `cliente_autorizado()`, y esa función no se
prueba con pytest: se prueba a mano, con la cuenta de Bruno.

El cliente esperado (real o falso) implementa:
  - crear_carpeta(nombre, carpeta_padre_id=None) -> id
  - subir_archivo(ruta_local, carpeta_id) -> id
  - listar_en_carpeta(carpeta_id) -> list de objetos con
    .id, .name, .modified_time, .mime_type
  - descargar_archivo(archivo_id, destino: Path) -> None
  - link_de_carpeta(carpeta_id) -> str
  - colorear_carpeta(carpeta_id, color: str) -> None
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CARPETA_PROXIES = "Proxies"
CARPETA_MATERIAL_NUEVO = "material nuevo"
CARPETA_ENTREGAS = "Proyectos para edición externa"
CARPETA_MIME = "application/vnd.google-apps.folder"
_RAIZ_DE_DRIVE = "root"

# De la paleta fija de colores que acepta Drive para carpetas (no
# cualquier hexadecimal sirve). Reflejan el mismo EstadoEntrega que ya
# existe -- no es un dato nuevo, es el mismo pintado en otro lugar.
COLOR_FALTA_EDITAR = "#fa573c"  # rojo -- recién subido, con el editor
COLOR_YA_REGRESO = "#16a765"    # verde -- el editor ya contestó


@dataclass(frozen=True)
class ResultadoDeSubida:
    folder_id: str
    folder_link: str
    prproj_modificado_en: str | None


def _subcarpeta_existente_o_nueva(cliente, carpeta_padre_id: str, nombre: str) -> str:
    """Reusa una subcarpeta con ese nombre o la crea si no existe."""
    for hijo in cliente.listar_en_carpeta(carpeta_padre_id):
        if hijo.name == nombre and hijo.mime_type == CARPETA_MIME:
            return hijo.id
    return cliente.crear_carpeta(nombre, carpeta_padre_id=carpeta_padre_id)


def _fecha_del_prproj(cliente, carpeta_id: str) -> str | None:
    archivos = cliente.listar_en_carpeta(carpeta_id)
    prproj = next((a for a in archivos if a.name.endswith(".prproj")), None)
    return prproj.modified_time if prproj is not None else None


def subir_paquete(cliente, nombre_proyecto: str, prproj: Path, proxies: list[Path],
                   carpeta_existente: str | None = None) -> ResultadoDeSubida:
    """Crea o reusa la carpeta de la entrega, sube su contenido y devuelve
    el link junto con la fecha del `.prproj` que acaba de quedar en Drive.

    Una carpeta nueva se crea DENTRO de `CARPETA_ENTREGAS` (se reusa si ya
    existe), nunca suelta en la raíz de Drive -- Bruno la mueve una vez a
    donde quiera dentro de su Drive y de ahí en adelante las entregas
    siguen cayendo ahí. `carpeta_existente` (de "Subir de nuevo") ya vive
    donde vive, no se vuelve a tocar su ubicación.
    """
    if carpeta_existente:
        carpeta_id = carpeta_existente
    else:
        entregas_id = _subcarpeta_existente_o_nueva(cliente, _RAIZ_DE_DRIVE, CARPETA_ENTREGAS)
        carpeta_id = cliente.crear_carpeta(nombre_proyecto, carpeta_padre_id=entregas_id)
    cliente.subir_archivo(prproj, carpeta_id)
    proxies_id = _subcarpeta_existente_o_nueva(cliente, carpeta_id, CARPETA_PROXIES)
    for proxy in proxies:
        cliente.subir_archivo(proxy, proxies_id)
    cliente.colorear_carpeta(carpeta_id, COLOR_FALTA_EDITAR)
    return ResultadoDeSubida(
        folder_id=carpeta_id, folder_link=cliente.link_de_carpeta(carpeta_id),
        prproj_modificado_en=_fecha_del_prproj(cliente, carpeta_id),
    )


@dataclass(frozen=True)
class ResultadoDeRevision:
    hay_cambios: bool
    prproj_modificado_en: str | None
    tiene_material_nuevo: bool


def revisar_cambios(cliente, carpeta_id: str,
                    prproj_modificado_en_la_subida: str | None) -> ResultadoDeRevision:
    """¿El `.prproj` de Drive es más nuevo que el que se subió, o ya hay
    algo en `material nuevo/`? Ninguna de las dos cosas se descarga
    todavía -- esto solo mira fechas y nombres."""
    archivos = cliente.listar_en_carpeta(carpeta_id)
    prproj = next((a for a in archivos if a.name.endswith(".prproj")), None)
    modificado_en = prproj.modified_time if prproj is not None else None
    hay_cambios = (
        modificado_en is not None
        and modificado_en != prproj_modificado_en_la_subida
    )
    tiene_material_nuevo = any(
        a.name == CARPETA_MATERIAL_NUEVO and a.mime_type == CARPETA_MIME
        for a in archivos
    )
    return ResultadoDeRevision(
        hay_cambios=hay_cambios, prproj_modificado_en=modificado_en,
        tiene_material_nuevo=tiene_material_nuevo,
    )


def hay_token_guardado() -> bool:
    """Si Google Drive ya se conectó alguna vez en esta computadora.

    Sirve para evitar abrir OAuth por sorpresa al refrescar una fila de la
    lista; ese flujo solo debe abrirse desde Configuración.
    """
    return _RUTA_TOKEN.exists()


def revisar_y_persistir(ruta_cvproj: Path, cliente) -> bool:
    """Revisa Drive y guarda el estado de respuesta del editor si cambió."""
    import json
    from dataclasses import replace

    from clasificador_video import proyecto
    from clasificador_video.entrega import EstadoEntrega

    try:
        data = json.loads(ruta_cvproj.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    estado = EstadoEntrega.de_dict(data.get("entrega"))
    if estado is None or estado.drive_folder_id is None:
        return False
    resultado = revisar_cambios(
        cliente, estado.drive_folder_id, estado.drive_prproj_modificado_en)
    if not (resultado.hay_cambios or resultado.tiene_material_nuevo):
        return False
    cliente.colorear_carpeta(estado.drive_folder_id, COLOR_YA_REGRESO)
    data["entrega"] = replace(
        estado, estado=EstadoEntrega.EDITOR_CONTESTO).to_dict()
    proyecto.guardar(ruta_cvproj, data)
    return True


def traer_prproj(cliente, carpeta_id: str, destino: Path) -> None:
    """Baja el `.prproj` de esa carpeta al destino, reemplazándolo.

    Lanza RuntimeError si el editor borró el proyecto o le cambió la extensión.
    """
    archivos = cliente.listar_en_carpeta(carpeta_id)
    prproj = next((a for a in archivos if a.name.endswith(".prproj")), None)
    if prproj is None:
        raise RuntimeError("No se encontró ningún .prproj en la carpeta de Drive.")
    cliente.descargar_archivo(prproj.id, destino)


def traer_material_nuevo(cliente, carpeta_id: str,
                          destino_por_categoria: dict[str, Path]) -> list[str]:
    """Baja cada subcarpeta de `material nuevo/` a su categoría en disco.

    `destino_por_categoria` mapea el nombre de la subcarpeta de Drive a la
    ruta local absoluta donde debe quedar. Devuelve las categorías que sí
    tenían archivos.
    """
    archivos = cliente.listar_en_carpeta(carpeta_id)
    material_nuevo = next(
        (a for a in archivos
         if a.name == CARPETA_MATERIAL_NUEVO and a.mime_type == CARPETA_MIME),
        None,
    )
    if material_nuevo is None:
        return []
    bajadas = []
    for categoria in cliente.listar_en_carpeta(material_nuevo.id):
        if categoria.mime_type != CARPETA_MIME:
            continue
        destino = destino_por_categoria.get(categoria.name)
        if destino is None:
            continue
        archivos_de_categoria = [
            archivo for archivo in cliente.listar_en_carpeta(categoria.id)
            if archivo.mime_type != CARPETA_MIME
        ]
        if not archivos_de_categoria:
            continue
        destino.mkdir(parents=True, exist_ok=True)
        for archivo in archivos_de_categoria:
            cliente.descargar_archivo(archivo.id, destino / archivo.name)
        bajadas.append(categoria.name)
    return bajadas


def mapa_de_categorias_de_material_nuevo() -> dict[str, str]:
    """De la subcarpeta de `material nuevo/` a su categoría real en disco,
    relativa a la raíz del proyecto (spec original §6). Confirmado contra
    un proyecto real de Bruno: no usa la estructura de bins de Premiere.
    """
    return {
        "musica y audio": "01. ASSETS VIDEO/05. MUSICA Y AUDIO",
        "fotos": "03. ASSETS PHOTOS",
        "graficos y branding": "06. GRAFICOS Y BRANDING",
    }


_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
_RUTA_TOKEN = Path.home() / ".clasificador_video" / "drive_token.json"


# Igual que `proxy_gen.generar`, baja primero a `.parcial` para no truncar el `.prproj` local si la red falla.
class _ClienteDrive:
    """El envoltorio real sobre `googleapiclient.discovery.Resource`,
    con la misma forma que el doble de pruebas."""

    def __init__(self, servicio):
        self._s = servicio

    def crear_carpeta(self, nombre, carpeta_padre_id=None):
        metadata = {"name": nombre, "mimeType": CARPETA_MIME}
        if carpeta_padre_id:
            metadata["parents"] = [carpeta_padre_id]
        creada = self._s.files().create(body=metadata, fields="id").execute()
        return creada["id"]

    def subir_archivo(self, ruta_local, carpeta_id):
        from googleapiclient.http import MediaFileUpload
        metadata = {"name": ruta_local.name, "parents": [carpeta_id]}
        media = MediaFileUpload(str(ruta_local), resumable=True)
        subido = self._s.files().create(
            body=metadata, media_body=media, fields="id").execute()
        return subido["id"]

    def listar_en_carpeta(self, carpeta_id):
        archivos = []
        page_token = None
        while True:
            respuesta = self._s.files().list(
                q=f"'{carpeta_id}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, modifiedTime, mimeType)",
                pageToken=page_token,
            ).execute()
            archivos.extend(_Archivo(a) for a in respuesta.get("files", []))
            page_token = respuesta.get("nextPageToken")
            if not page_token:
                break
        return archivos

    def descargar_archivo(self, archivo_id, destino):
        from googleapiclient.http import MediaIoBaseDownload
        import os

        destino.parent.mkdir(parents=True, exist_ok=True)
        parcial = destino.with_name(destino.name + ".parcial")
        try:
            with open(parcial, "wb") as f:
                descargador = MediaIoBaseDownload(f, self._s.files().get_media(fileId=archivo_id))
                terminado = False
                while not terminado:
                    _, terminado = descargador.next_chunk()
        except Exception:
            parcial.unlink(missing_ok=True)
            raise
        os.replace(parcial, destino)

    def link_de_carpeta(self, carpeta_id):
        return f"https://drive.google.com/drive/folders/{carpeta_id}"

    def colorear_carpeta(self, carpeta_id, color):
        self._s.files().update(fileId=carpeta_id, body={"folderColorRgb": color}).execute()


class _Archivo:
    def __init__(self, datos: dict):
        self.id = datos["id"]
        self.name = datos["name"]
        self.modified_time = datos.get("modifiedTime")
        self.mime_type = datos.get("mimeType", "")


def cliente_autorizado(credenciales_oauth_json: Path):
    """Abre el flujo de OAuth de Google en el navegador la primera vez
    (permiso acotado: `drive.file`, Clipify solo toca lo que ella misma
    sube -- spec original, "Por qué Drive y con qué permiso") y guarda el
    token en `~/.clasificador_video/drive_token.json` para las próximas
    veces. NO se prueba con pytest: necesita la cuenta real de Bruno.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if _RUTA_TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(_RUTA_TOKEN), _SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credenciales_oauth_json), _SCOPES)
            creds = flow.run_local_server(port=0)
        _RUTA_TOKEN.parent.mkdir(parents=True, exist_ok=True)
        _RUTA_TOKEN.write_text(creds.to_json())

    from googleapiclient.discovery import build
    return _ClienteDrive(build("drive", "v3", credentials=creds))
