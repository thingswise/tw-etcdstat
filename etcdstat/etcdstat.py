#    Copyright 2017 Thingswise, LLC
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


import logging
import contextlib
import UserDict

class Client(object):

    def write(self, name, value, ttl=None):
        assert False

    def close(self):
        pass

class StdoutClient(Client):

    def write(self, name, value, ttl=None):
        print "%s = %s" % (name, value)

class EtcdClient(Client):

    def __init__(self, host, port):
        import etcd
        self.client = etcd.Client(host=host, port=port)

    def write(self, name, value, ttl=None):
        self.client.write(name, value, ttl=self.interval*2)

    def close(self):
        pass

class Context(UserDict.DictMixin):

    def __init__(self):
        self.modules = []

    def __getitem__(self, key):
        for module in self.modules:
            if module.provides(key):
                return module.get(key)
        raise KeyError(key)

    def keys(self):
        return [key for module in self.modules for key in module.keys()]

    def add_module(self, module):
        self.modules.append(module)   

class Template(object):

    def __init__(self, repr, template):
        self.repr = repr
        self.template = template

    def __repr__(self):
        return self.repr 

    def render(self, context):
        return self.template.render(context)            

class EtcdStat(object):

    def __init__(self, url, interval, items):
        from urlparse import urlparse
        from jinja2 import Environment
        env = Environment()
        self.items = { n : (Template(n, env.from_string(n)), Template(v, env.from_string(v))) for (n,v) in items }
        self.interval = interval

        parsed_url = urlparse(url)
        if parsed_url.scheme == "stdout":
            self.client = StdoutClient()
        elif parsed_url.scheme == "http":
            self.client = EtcdClient(host=parsed_url.hostname(), port=parsed_url.port if parsed_url.port else 80)
        else:
            raise ValueError("Unsupported scheme" % parsed_url.scheme)

        self.context = Context()

        import cpu
        import memory
        import disk
        import host
        import systemd
        self.context.add_module(cpu.Cpu())
        self.context.add_module(memory.Memory())
        self.context.add_module(disk.Disk())                
        self.context.add_module(host.Host())
        self.context.add_module(systemd.Systemd())

    def update_etcd(self):
        import jinja2

        for p in self.items:
            (name, value) = self.items[p]
            try:
                _name = name.render(self.context)
            except:
                logging.error("Error rendering %s" % name, exc_info=True)
                raise
            try:
                _value = value.render(self.context)
            except:
                logging.error("Error rendering %s" % value, exc_info=True)
                raise
            try:
                self.client.write(_name, _value, ttl=self.interval*2)
            except:
                logging.error("Error writing %s" % _name, exc_info=True)
                raise

    def run(self):
        import time        
        while True:
            try:
                self.update_etcd()
            except:
                pass
            time.sleep(self.interval)

    def close(self):
        self.client.close()

def main():
    import argparse
    import ConfigParser

    parser = argparse.ArgumentParser()
    parser.add_argument("url", metavar="URL", help="Etcd URL", default="http://localhost:2379")
    parser.add_argument("-c", "--config", metavar="CONFIG", help="Configuration file", default="/etc/etcdstat.cfg")
    parser.add_argument("-i", "--interval", metavar="INTERVAL", help="Poll interval (sec)", type=float, default="10")

    args = parser.parse_args()

    config = ConfigParser.ConfigParser()
    config.read(args.config)

    items = []
    for sect in ["System","Services"]:
        try:
            for name, value in config.items(sect):
                items.append((name, value))
        except ConfigParser.NoSectionError:
            pass
    
    with create_etcdstat(args.url, args.interval, items) as etcdstat:
        etcdstat.run()

@contextlib.contextmanager
def create_etcdstat(url, interval, items):
    etcdstat = EtcdStat(url, interval, items)
    try:
        yield etcdstat
    finally:
        etcdstat.close()

if __name__ == "__main__":
    main()        