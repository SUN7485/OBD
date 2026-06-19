import pathlib

p = pathlib.Path(r'D:/obd/backend/services/mqtt_client.py')
text = p.read_text(encoding='utf-8')
old = """        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._client = None"""
new = """        if self._client:
            try:
                disconnect = self._client.disconnect
                if disconnect and callable(disconnect):
                    result = disconnect()
                    if result and hasattr(result, '__await__'):
                        await result
            except Exception:
                pass
            self._client = None"""
if old in text:
    text = text.replace(old, new)
    p.write_text(text, encoding='utf-8')
    print('mqtt patched')
else:
    print('old not found')
