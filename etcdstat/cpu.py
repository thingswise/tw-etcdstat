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
import time

class Cpu(module.BaseModule):

    def __init__(self):
        self.cpu = None        

    def keys(self):
        return ["cpu"]

    def get(self, key):
        if key == "cpu":
            curtime = time.time()
            if self.cpu is None or curtime - self.last_query > 10:
                self.cpu = psutil.cpu_percent(interval=None)
                self.last_query = curtime 
            return float(self.cpu) / 100
        else:
            raise KeyError()