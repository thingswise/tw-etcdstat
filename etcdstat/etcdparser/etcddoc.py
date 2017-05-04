import json

class EtcdDocument(object):

    def __init__(self, client, root_path, root=None):
        if root is None:
            self.root = client.read(root_path, recursive=True)
        else:
            self.root = root

    def _get_node(self, path):
        d = self.root
        for s in path:
            if s == ".":
                pass
            else:
                if hasattr(d, "_children"):
                    children = d._children
                    for child in children:
                        if child.key.split("/")[-1] == s:
                            d = etcd.EtcdResult(None, node=child)
                            break
                    else:
                        return None
                else:
                    return None
        return d

    def get_value(self, path):
        node = self._get_node(path)
        try:
            val = node.value
        except AttributeError:
            val = None
        if val is not None:
            try:
                return json.loads(val)
            except:
                return val 

    def subdocument(self, path):
        return EtcdDocument(None, None, self._get_node(path))

    def children(self):
        if self.root is None or not hasattr(self.root, "_children"):
            return []
        else:
            return [(child.key.split("/")[-1], EtcdDocument(None, None, node=child)) for child in self.root._children]
