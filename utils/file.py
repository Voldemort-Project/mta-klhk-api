import base64
from io import BytesIO


def decoding_file(base64_file: str) -> BytesIO:
    file_bytes = base64.b64decode(base64_file)
    file_io = BytesIO(file_bytes)
    return file_io
