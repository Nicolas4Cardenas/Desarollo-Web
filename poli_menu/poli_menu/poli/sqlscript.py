"""Divide un script .sql (con DELIMITER, como lo hace el cliente mysql) en sentencias."""
from typing import Iterator


def dividir_sentencias(texto: str) -> Iterator[str]:
    delimitador = ";"
    buffer = []
    for linea in texto.splitlines():
        s = linea.strip()
        if s.startswith("--"):          # comentario de línea completa
            continue
        if not buffer:
            if not s:
                continue
            if s.upper().startswith("DELIMITER "):
                delimitador = s.split(None, 1)[1].strip()
                continue
        buffer.append(linea)
        if s.endswith(delimitador):
            sentencia = "\n".join(buffer).rstrip()
            sentencia = sentencia[: -len(delimitador)].rstrip()
            if sentencia:
                yield sentencia
            buffer = []
    resto = "\n".join(buffer).strip()
    if resto:
        yield resto
