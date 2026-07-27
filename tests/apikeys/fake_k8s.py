"""内存版 CoreV1Api（仅 Secret 四个操作），模拟 string_data→data 的 base64 行为。"""
import base64

from kubernetes.client.rest import ApiException


class FakeCoreV1:
    def __init__(self):
        self.secrets = {}  # (namespace, name) -> V1Secret
        self.read_calls = 0

    def create_namespaced_secret(self, namespace, body):
        if body.string_data:
            body.data = {k: base64.b64encode(v.encode()).decode()
                         for k, v in body.string_data.items()}
            body.string_data = None
        key = (namespace, body.metadata.name)
        if key in self.secrets:
            raise ApiException(status=409, reason="AlreadyExists")
        self.secrets[key] = body
        return body

    def read_namespaced_secret(self, name, namespace):
        self.read_calls += 1
        try:
            return self.secrets[(namespace, name)]
        except KeyError:
            raise ApiException(status=404, reason="NotFound")

    def list_namespaced_secret(self, namespace, label_selector=None):
        class _Result:
            pass
        items = []
        for (ns, _), secret in self.secrets.items():
            if ns != namespace:
                continue
            if label_selector:
                k, _, v = label_selector.partition("=")
                if (secret.metadata.labels or {}).get(k) != v:
                    continue
            items.append(secret)
        r = _Result()
        r.items = items
        return r

    def delete_namespaced_secret(self, name, namespace):
        try:
            del self.secrets[(namespace, name)]
        except KeyError:
            raise ApiException(status=404, reason="NotFound")
