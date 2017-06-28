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

class OS(module.BaseModule):

    """
    * {{os_name}} - get the pretty printed OS name
    """

    HOSTNAME = "org.freedesktop.hostname1"

    def __init__(self):
        pass

    def hostname_props(self):
        bus = dbus.SystemBus()
        hostname1 = bus.get_object(OS.HOSTNAME, "/org/freedesktop/hostname1")
        return dbus.Interface(hostname1, dbus_interface="org.freedesktop.DBus.Properties")

    def keys(self):
        return ["os_name"]

    def get(self, key):
        if key == "os_name":
            try:
                return hostname_props().Get("org.freedesktop.hostname1", "OperatingSystemPrettyName")
            except dbus.DBusException:
                logging.error("Error getting OS name", exc_info=True)
                return ""
        else:
            raise KeyError(key)
