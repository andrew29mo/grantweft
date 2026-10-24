"""One session per tunnel. TLS EOF is not application half-close."""
import asyncio
import json
import struct

DATA, EOF, CLOSE, OPEN, OK, ERROR = range(1, 7)
MAX_FRAME = 16384
HEADER = struct.Struct('!BI')

class Refused(Exception):
    pass

async def read_frame(reader, timeout=3):
    async def read():
        kind, n = HEADER.unpack(await reader.readexactly(HEADER.size))
        if kind not in (DATA, EOF, CLOSE, OPEN, OK, ERROR) or n > MAX_FRAME:
            raise Refused('FRAME_FORMAT')
        if kind in (EOF, CLOSE) and n:
            raise Refused('CONTROL_PAYLOAD')
        return kind, await reader.readexactly(n)
    return await asyncio.wait_for(read(), timeout) if timeout else await read()

def frame(writer, kind, data=b''):
    if len(data) > MAX_FRAME:
        raise Refused('FRAME_SIZE')
    writer.write(HEADER.pack(kind, len(data)) + data)

def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def decode(data):
    def reject(value):
        raise Refused('NONFINITE')
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise Refused('DUPLICATE_KEY')
            out[k] = v
        return out
    try:
        return json.loads(data, parse_constant=reject, object_pairs_hook=pairs)
    except (ValueError, UnicodeError) as exc:
        raise Refused('JSON') from exc

def abort(writer):
    if writer is not None:
        writer.transport.abort()
