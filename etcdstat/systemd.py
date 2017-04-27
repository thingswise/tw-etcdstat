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

import dbus
import module
import logging
import cachetools
import psutil

class PropWrapper(object):

    def __init__(self, interface, props):
        self.props = props
        self.interface = interface

    def __getattr__(self, name):
        return self.props.Get(self.interface, name)

@cachetools.cached(cache=cachetools.LRUCache(5000))
def _get_process(pid):    
    return psutil.Process(pid=pid)

class CGroupWrapper(object):

    def __init__(self, cgname):
        self.cgname = cgname

    def _get_procs(self):
        result = []
        with open("/sys/fs/cgroup/systemd%s/cgroup.procs" % self.cgname) as fp:
            for pid in fp:
                result.append(int(pid))
        return result

    @property
    def cpu_time_pct(self):
        procs = self._get_procs()
        cpu_percent = 0.0
        for pid in procs:
            # The line below will get the CPU usage pct
            # since the last invocation of cpu_percent(). 
            # The important point here is memoization of the
            # process object. If the process object is brand
            # new, then cpu_percent() returns 0. The memoization
            # occurs in _get_process() and is mostly controlled 
            # by the LRUCache settings. If the number of monitored
            # processes approaches 5000 (see decotator), then
            # the returned value becomes incorrect
            cpu_percent += _get_process(pid).cpu_percent()
        return cpu_percent

    @property
    def rss(self):
        procs = self._get_procs()
        memory = 0.0
        for pid in procs:
            memory += _get_process(pid).memory_info().rss
        return memory

class UnitWrapper(object):

    def __init__(self, obj):
        self.unit = dbus.Interface(obj, dbus_interface="org.freedesktop.systemd1.Unit")
        self.props = PropWrapper(
            "org.freedesktop.systemd1.Unit", 
            dbus.Interface(obj, dbus_interface="org.freedesktop.DBus.Properties"))
        self.service_props = PropWrapper(
            "org.freedesktop.systemd1.Service",
            dbus.Interface(obj, dbus_interface="org.freedesktop.DBus.Properties"))
        self.cgroup = CGroupWrapper(str(self.service_props.ControlGroup))

    def __getattr__(self, name):
        if name == "properties":
            return self.props
        elif name == "cgroup":
            return self.cgroup
        else:        
            return getattr(self.unit, name)


class Systemd(module.BaseModule):

    SYSTEMD = "org.freedesktop.systemd1"

    def __init__(self):
        self.bus = dbus.SystemBus()
        systemd1 = self.bus.get_object(Systemd.SYSTEMD, "/org/freedesktop/systemd1")
        self.manager = dbus.Interface(systemd1, dbus_interface="org.freedesktop.systemd1.Manager")        

    def keys(self):
        return ["unit"]

    def get(self, key):
        def unit(name):
            unit_path = self.manager.GetUnit(name)
            unit_obj = self.bus.get_object(Systemd.SYSTEMD, unit_path)
            return UnitWrapper(unit_obj)
        if key == "unit":
            return unit
        else:
            raise KeyError(key)
