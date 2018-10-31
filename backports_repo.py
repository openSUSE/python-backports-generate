#!/usr/bin/python3
import concurrent.futures
import configparser
import io
import json
import logging
import os.path
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as etree

import appdirs

logging.basicConfig(format='%(levelname)s:%(funcName)s:%(message)s',
                    level=logging.DEBUG)
log = logging.getLogger('backports_repo')

project = "devel:languages:python:backports"
factory_name = "openSUSE:Factory"

cfg = configparser.ConfigParser()
cfg.read(os.path.expanduser('~/.config/osc/oscrc'))
OBS_API = 'https://api.opensuse.org'
OBS_cfg = cfg[OBS_API]
MAX_PROCS = 5

# available in python >= 3.5
pwd_mgr = urllib.request.HTTPPasswordMgrWithPriorAuth()
pwd_mgr.add_password(realm=None, uri=OBS_API,
                     user=OBS_cfg['user'],
                     passwd=OBS_cfg['pass'])
https_handler = urllib.request.HTTPSHandler(debuglevel=0)
auth_handler = urllib.request.HTTPBasicAuthHandler(pwd_mgr)
opener = urllib.request.build_opener(https_handler, auth_handler)

src_URL = "%s/source/{}" % OBS_API


def project_list(url):
    with opener.open(url, timeout=10) as response:
        assert response.status == 200
        for _, element in etree.iterparse(response):
            if element.tag == 'entry':
                yield element.attrib['name']


def rdelete(pkg, proj):
    msg = "Package {} not in whitelist or {}".format(pkg, factory_name)
    log.info("osc rdelete %(msg)s %(proj)s %(pkg)s" % {
        'msg': msg, 'proj': proj, 'pkg': pkg})
    ret = subprocess.call(['osc', 'rdelete', '-m', msg, proj, pkg])
    time.sleep(1)
    return ret


def linkpac(pkg, proj_source):
    log.info("osc linkpac %(factory_name)s %(pkg)s %(proj_source)s" % {
        'factory_name': factory_name, 'pkg': pkg, 'proj_source': proj_source})
    ret = subprocess.call(['osc', 'linkpac', factory_name, pkg, proj_source])
    time.sleep(1)
    return ret


backports_python = {x for x in project_list(src_URL.format(project))}
factory_python = {x for x in project_list(src_URL.format(factory_name))
                  if x.startswith('python')}
python_itself = {"python-base", "python3-base", "python", "python3",
                 "python-doc", "python3-doc"}

additional_conf_file = os.path.join(appdirs.user_config_dir(),
                                    'osc', 'backports_repo.json')

# Fall back to in-tree copy
if not os.path.exists(additional_conf_file):
    additional_conf_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'backports_repo.json')

# extra packages we want there
additional_links = set()
if os.path.exists(additional_conf_file):
    with io.open(additional_conf_file) as conf_f:
        obj = json.load(conf_f)
        if 'additional_links' not in obj:
            raise KeyError(
                '"additional_links" not found in configuration file %s' %
                additional_conf_file)
        additional_links = set(obj['additional_links'])

factory_python = factory_python | additional_links
factory_python -= {
    'python-Django',  # prefer python-Django1
}


futures = []
with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PROCS) as executor:
    # remove packages not in tumbleweed
    for package in backports_python - factory_python:
        futures.append(executor.submit(rdelete, package, project))

    # add packages not in yet
    for package in factory_python - python_itself - backports_python:
        futures.append(executor.submit(linkpac, package, project))

results = []
for f in concurrent.futures.as_completed(futures):
    results.append(f.result())

results = [x for x in results if x != 0]

sys.exit(len(results))
