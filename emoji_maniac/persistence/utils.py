import base64
import struct


def pack2b64_bin(fmt: str, *data) -> bytes:
    return base64.b64encode(struct.pack(fmt, *data))


def pack2b64(fmt: str, *data) -> str:
    return pack2b64_bin(fmt, *data).decode('ascii')


def unpack_from_b64(fmt: str, s: str):
    return struct.unpack(fmt, base64.b64decode(s))

