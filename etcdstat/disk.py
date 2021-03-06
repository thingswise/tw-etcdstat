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

class Disk(module.BaseModule):

    def keys(self):
        return ["disk_usage_pct", "available_storage", "total_storage"]

    def get(self, key):
        if key == "disk_usage_pct":
            def disk_usage(path):
                return float(psutil.disk_usage(path).percent)/100
            return disk_usage
        elif key == "available_storage":
            def available_storage(path):
                return psutil.disk_usage(path).free
            return available_storage    
        elif key == "total_storage":
            def total_storage(path):
                return psutil.disk_usage(path).total
            return total_storage    
        else:
            raise KeyError()