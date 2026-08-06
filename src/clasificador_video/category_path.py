# src/clasificador_video/category_path.py
from __future__ import annotations


class CategoryTree:
    """Construye categoria_path para el manifest, con subcuartos creados
    perezosamente por padre (spec app-externa §5): 'Recamara 1 > Bano' y
    'Recamara 2 > Bano' son ramas independientes aunque compartan nombre.
    """

    def __init__(self) -> None:
        self._subrooms_by_parent: dict[str, list[str]] = {}

    def attach_subroom(self, parent: str, subroom: str) -> None:
        existing = self._subrooms_by_parent.setdefault(parent, [])
        if subroom not in existing:
            existing.append(subroom)

    def known_subrooms_for(self, parent: str) -> list[str]:
        return list(self._subrooms_by_parent.get(parent, []))

    def path_for(self, room: str, subroom: str | None = None) -> list[str]:
        if subroom is None:
            return [room]
        if subroom not in self._subrooms_by_parent.get(room, []):
            raise ValueError(
                f"'{subroom}' no ha sido creado como subcuarto de '{room}' todavia "
                f"-- usa attach_subroom primero"
            )
        return [room, subroom]
