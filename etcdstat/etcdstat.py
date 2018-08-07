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
import threading

class Client(object):

    def write(self, name, value, ttl=None):
        assert False

    def append(self, name, value, ttl=None):
        assert False

    def close(self):
        pass

    def add_handler(self, context, defaults, name, ntemp, vtemp):
        pass

class StdoutClient(Client):

    def write(self, name, value, ttl=None):
        print "%s = %s" % (name, value)

class EtcdClient(Client):

    def __init__(self, host, protocol, cert, ca_cert):
        """
       Initialize the client.

       Args:
           host (mixed):
                          a tuple ((host, port), (host, port), ...)

           protocol (str):  Protocol used to connect to etcd.

           cert (mixed):   If a string, the whole ssl client certificate;
                           if a tuple, the cert and key file names.

           ca_cert (str): The ca certificate. If pressent it will enable
                          validation.
       """
        import etcd
        self.client = etcd.Client(host=host, protocol=protocol, cert=cert, ca_cert=ca_cert)

    def write(self, name, value, ttl=None):
        self.client.write(name, value, ttl=ttl)

    def append(self, name, value, ttl=None):
        self.client.write(name, value, append=True, ttl=ttl)

    def close(self):
        pass

    def add_handler(self, context, defaults, name, ntemp, vtemp):
        EtcdHandlerThread(name, ntemp, vtemp, self.client, defaults, context).start()

class EtcdHandlerThread(threading.Thread):

    def __init__(self, name, ntemp, vtemp, client, defaults, context):
        super(EtcdHandlerThread, self).__init__(name=name)
        self.daemon = True
        self.ntemp = ntemp
        self.vtemp = vtemp
        self.client = client
        self.defaults = defaults
        self.context = context

    def run(self):
        defaults = self.defaults.render(self.context)
        ctx = dict(self.context)
        ctx.update(defaults)
        key = self.ntemp.render(ctx)
        for event in self.client.eternal_watch(key=key,recursive=True):
            if event.action == "create":
                ctx = dict(self.context)
                ctx.update(defaults)
                ctx["event"] = event.value
                try:
                    self.vtemp.render(ctx)
                except:
                    logging.error("Error processing action on %s" % key, exc_info=True)


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

    def __init__(self, endpoints, cert, ca_cert, interval, items, handlers, defaults):
        from urlparse import urlparse
        from jinja2 import Environment
        env = Environment()
        self.items = { n : (Template(n, env.from_string(n)), Template(v, env.from_string(v))) for (n,v) in items }
        self.handlers = { n : (Template(n, env.from_string(n)), Template(v, env.from_string(v))) for (n,v) in handlers }
        self.interval = interval

        parsed_endpoints = map(urlparse, endpoints.split(','))

        if len(parsed_endpoints) <= 0:
            raise ValueError("Endpoint parameter is empty or missing")

        scheme = parsed_endpoints[0].scheme

        if scheme == "stdout":
            self.client = StdoutClient()
        else:
            self.client = EtcdClient(
                map(lambda e: (e.hostname, e.port if e.port else 80 if e.scheme == "http" else 443), parsed_endpoints),
                scheme, cert, ca_cert)

        self.defaults = TemplateDict({ n : Template(v, env.from_string(v)) for (n,v) in defaults })

        self.context = Context()

        import cpu
        import memory
        import disk
        import host
        import systemd
        import os_support
        self.context.add_module(cpu.Cpu())
        self.context.add_module(memory.Memory())
        self.context.add_module(disk.Disk())                
        self.context.add_module(host.Host())
        self.context.add_module(systemd.Systemd())
        self.context.add_module(os_support.OS())

        for n in self.handlers:
            self.client.add_handler(self.context, self.defaults, n, *(self.handlers[n]))

    def update_etcd(self):
        import jinja2

        defaults = self.defaults.render(self.context)
        #print "defaults =", defaults 
        ctx = dict(self.context)
        ctx.update(defaults)

        for p in self.items:
            (name, value) = self.items[p]
            try:
                _name = name.render(ctx)
            except:
                logging.error("Error rendering %s" % name, exc_info=True)
                continue
            try:
                _value = value.render(ctx)
            except:
                logging.error("Error rendering %s" % value, exc_info=True)
                continue
            try:
                self.client.write(_name, _value, ttl=int(self.interval*2))
            except:
                logging.error("Error writing %s" % _name, exc_info=True)
                continue

    def run(self):
        import time        
        while True:
            try:
                self.update_etcd()
            except:
                logging.error("Error", exc_info=True)
                pass
            time.sleep(self.interval)

    def close(self):
        self.client.close()

class TemplateDict(object):

    def __init__(self, src):
        self.items = src

    def render(self, context):
        return { name: value.render(context) for (name, value) in self.items.iteritems() }

def main():
    import argparse
    import complexini
    import os.path
    # make dbus thread-safe
    import dbus.mainloop.glib
    dbus.mainloop.glib.threads_init()

    parser = argparse.ArgumentParser()
    parser.add_argument("url", metavar="URL", help="Etcd URL", default="http://localhost:2379")
    parser.add_argument("-c", "--config", metavar="CONFIG", help="Configuration file", default="/etc/etcdstat.cfg")
    parser.add_argument("-i", "--interval", metavar="INTERVAL", help="Poll interval (sec)", type=float, default="10")

    args = parser.parse_args()
    
    config_dir = os.path.dirname(args.config)
    config = complexini.ComplexIniFile(root_dir=config_dir if config_dir else None)
    config.read(args.config)

    defaults = []
    for sect in ["Defaults"]:
        for name, value in config.items(sect):
            defaults.append((name, value))
    #print defaults

    items = []
    for sect in ["System","Services"]:
        for name, value in config.items(sect):
            items.append((name, value))

    handlers = []
    for sect in ["Handlers"]:
        for name, value in config.items(sect):
            handlers.append((name, value))

    endpoints = os.environ.get("ETCDCTL_ENDPOINT", args.url)
    cert_file = os.environ.get("ETCDCTL_CERT_FILE")
    key_file = os.environ.get("ETCDCTL_KEY_FILE")
    ca_cert = os.environ.get("ETCDCTL_CACERT")

    if cert_file and key_file:
        cert = (cert_file, key_file)
    else:
        cert = None

    with create_etcdstat(endpoints, cert, ca_cert, args.interval, items, handlers, defaults) as etcdstat:
        etcdstat.run()

@contextlib.contextmanager
def create_etcdstat(endpoints, cert, ca_cert, interval, items, handlers, defaults):
    etcdstat = EtcdStat(endpoints, cert, ca_cert, interval, items, handlers, defaults)
    try:
        yield etcdstat
    finally:
        etcdstat.close()

if __name__ == "__main__":
    main()        