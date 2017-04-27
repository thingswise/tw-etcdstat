# -*- coding: utf-8 -*-

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

 
 
import re
from setuptools import setup

 
version = re.search(
    '^__version__\s*=\s*"(.*)"',
    open('etcdstat/__init__.py').read(),
    re.M
    ).group(1)
 
 
with open("README.rst", "rb") as f:
    long_descr = f.read().decode("utf-8")
 
 
setup(
    name = "tw-etcdstat",
    packages = ["etcdstat"],
    entry_points = {
        "console_scripts": ['etcdstat = etcdstat.etcdstat:main']
    },
    version = version,
    description = "Python system and service monitoring service",
    long_description = long_descr,
    author = "Alexander Lukichev",
    author_email = "alexander.lukichev@thingswise.com",
    url = "https://github.com/thingswise/tw-etcdstat",
    install_requires = [
        "jinja2",
        "psutil",
        "cachetools"
    ],
    license="Apache2"
)