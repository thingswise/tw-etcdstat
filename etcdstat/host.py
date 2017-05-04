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

import psutil
import time
import module
import socket

class Host(module.BaseModule):

    """
    * {{addr(family)}} - get address for the given address family 
      (one of ip, ip6, link)
    * {{ip}} - get IPv4 address 
    """

    def __init__(self, ttl=300):        
        self.interfaces = None
        self.ttl = ttl

    def keys(self):
        return ["addr", "ip"]

    def get(self, key):        
        def addr(device, address_family):
            if address_family == "ip":
                af = socket.AF_INET
            elif address_family == "ip6":
                af = socket.AF_INET6
            elif address_family == "link":
                af = psutil.AF_LINK
            else:
                raise ValueError("Unsupported address family: %s" % address_family)
            
            curtime = time.time()
            if self.interfaces is None or curtime - self.last_query > self.ttl:
                self.interfaces = psutil.net_if_addrs()
                self.last_query = curtime

            for addr in self.interfaces[device]:
                if addr.family == af:
                    return addr.address

            raise ValueError("Device %s doesn't have address of the address family %s" % (device, address_family))
        def ip(device):
            return addr(device, "ip")
        if key == "addr":
            return addr
        if key == "ip":                
            return ip
        else:
            raise KeyError()