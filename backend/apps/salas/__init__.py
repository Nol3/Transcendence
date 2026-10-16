"""Salas de juego: la capa común a todos los juegos online.

Aquí vive lo que no cambia de un juego a otro —códigos, asientos, reconexión, el WebSocket, los
endpoints de sala— y en `juegos.py` el contrato que cumple cada juego. Añadir un juego online es
escribir ese contrato sobre su motor y registrarlo: no se copia nada.
"""
