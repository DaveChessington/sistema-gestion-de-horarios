"""Nombre de dominio para la ocupación confirmada del calendario.

La tabla histórica ``reservas.evento`` conserva su nombre físico para evitar
una migración destructiva. En el contrato del MVP, cada Evento activo asociado
a una Peticion representa la Reserva confirmada.
"""

from booking.app.models.evento import Evento


Reserva = Evento

__all__ = ["Reserva"]
