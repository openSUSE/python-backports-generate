#!/usr/bin/python3
from subprocess import check_call, check_output

project = "devel:languages:python:backports"

backports_python = set(check_output(['osc', 'ls', project]).split())
factory_python_raw = check_output(['osc', 'ls', 'openSUSE:Factory']).split()
factory_python = {x for x in factory_python_raw if x.startswith('python')}

python_itself = {"python-base", "python3-base", "python", "python3",
                 "python-doc", "python3-doc"}

# extra packages we want there
additional_links = {"libcryptopp", "libsodium", "qpid-proton",
                    "openstack-macros"}

factory_python = factory_python | additional_links

# remove packages not in tumbleweed
for i in backports_python - factory_python:
    msg = f"Package {i} not in whitelist or openSUSE:Factory"
    check_call(['osc', 'rdelete', i, '-m', msg])

# add packages not in yet
for i in factory_python - python_itself - backports_python:
    check_call(['osc', 'linkpac', 'openSUSE:Factory', i, project])
