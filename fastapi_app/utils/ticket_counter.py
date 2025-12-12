from pathlib import Path

def obtener_siguiente_numero_ticket(tickets_dir: Path) -> int:
    counter_file = tickets_dir / "ticket_counter.txt"

    # Si no existe, inicializar en 1
    if not counter_file.exists():
        counter_file.write_text("1")
        return 1

    # Leer número actual
    try:
        numero_actual = int(counter_file.read_text().strip())
    except:
        numero_actual = 1

    siguiente = numero_actual + 1

    # Si pasa de 100, reiniciar y borrar todos los tickets previos
    if siguiente > 100:
        siguiente = 1

        # borrar archivos .pdf
        for archivo in tickets_dir.iterdir():
            if archivo.is_file() and archivo.name.endswith(".pdf"):
                archivo.unlink()

    # guardar número actualizado
    counter_file.write_text(str(siguiente))

    return siguiente
