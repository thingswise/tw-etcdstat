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
import module

class Memory(module.BaseModule):

    """
    * {{memory_usage_pct}} - physical memory usage (percent)
    * {{total_memory}} - total phycal memory
    * {{available_memory}} - available memory
    """

    def keys(self):
        return ["memory_usage_pct", "total_memory", "available_memory"]

    def get(self, key):
        if key == "memory_usage_pct":
            mem = psutil.virtual_memory()
            return 1 - float(mem.available) / mem.total
        elif key == "total_memory":
            mem = psutil.virtual_memory()
            return float(mem.total)
        elif key == "available_memory":
            mem = psutil.virtual_memory()
            return float(mem.available)
        else:
            raise KeyError()