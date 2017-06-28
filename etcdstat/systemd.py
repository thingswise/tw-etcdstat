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

    """
    * {{...cpu_time_pct}} - percent share of CPU core time by the given cgroup
    * {{...rss}} - total RSS memory in bytes by the given cgroup 
    """

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
            # processes approaches 5000 (see decorator), then
            # the returned value becomes incorrect
            cpu_percent += _get_process(pid).cpu_percent()
        return float(cpu_percent) / 100

    @property
    def rss(self):
        procs = self._get_procs()
        memory = 0.0
        for pid in procs:
            memory += _get_process(pid).memory_info().rss
        return memory

class UnitWrapper(object):

    """
    * {{...properties}} - return the object which contains unit properties 
      (see https://wiki.freedesktop.org/www/Software/systemd/dbus/)
    * {{...cgroup}} - return the CGroup properties representation (see CGroupWrapper)
    * {{...handle(action)}} - execute unit action (one of start, stop, restart)
    """

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
        elif name == "handle":
            def handle(action):
                if action == "start":
                    self.unit.Start("replace")
                elif action == "stop":
                    self.unit.Stop("replace")
                elif action == "restart":
                    self.unit.Restart("replace")
                else:
                    raise ValueError(action)                    
            return handle
        else:        
            return getattr(self.unit, name)


class Systemd(module.BaseModule):

    """
    * {{unit(name)}} - get the systemd unit object (see UnitWrapper)
    """    

    SYSTEMD = "org.freedesktop.systemd1"

    def __init__(self):
        pass  

    def bus(self):
        return dbus.SystemBus()

    def manager(self):        
        systemd1 = self.bus().get_object(Systemd.SYSTEMD, "/org/freedesktop/systemd1")
        return dbus.Interface(systemd1, dbus_interface="org.freedesktop.systemd1.Manager")

    def manager_props(self):
        systemd1 = self.bus().get_object(Systemd.SYSTEMD, "/org/freedesktop/systemd1")
        return PropWrapper("org.freedesktop.systemd1.Manager", 
            dbus.Interface(systemd1, dbus_interface="org.freedesktop.DBus.Properties"))

    def keys(self):
        return ["unit" ,"reboot", "boot_time"]

    def get(self, key):
        if key == "unit":
            def unit(name):
                unit_path = self.manager().GetUnit(name)
                unit_obj = self.bus().get_object(Systemd.SYSTEMD, unit_path)
                return UnitWrapper(unit_obj)
            return unit
        elif key == "reboot":
            def reboot():
                self.manager().Reboot()
            return reboot
        elif key == "boot_time":
            return self.manager_props().KernelTimestamp/1000000.0
        else:
            raise KeyError(key)
