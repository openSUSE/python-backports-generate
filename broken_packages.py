#!/usr/bin/python3
import configparser
import logging
import os.path
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as etree

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
build_URL = "%s/build/{}" % OBS_API


def project_list(url):
    with opener.open(url, timeout=10) as response:
        assert response.status == 200
        for _, element in etree.iterparse(response):
            if element.tag == 'entry':
                yield element.attrib['name']


def list_broken_packages(proj):
    url = build_URL.format("%s/_result" % proj)
    with opener.open(url, timeout=10) as response:
        assert response.status == 200
        for _, element in etree.iterparse(response):
            if element.tag == 'status':
                if element.attrib['code'] == 'broken':
                    details = ''.join(element.itertext())
                    details = details.split(':')[-1].strip()
                    yield element.attrib['package'], details


def rdelete(pkg, proj):
    msg = "Package {} not in allowlist or {}".format(pkg, factory_name)
    ret = subprocess.call(['osc', 'rdelete', '-m', msg, proj, pkg])
    time.sleep(1)
    return ret


def linkpac(pkg, proj_source):
    ret = subprocess.call(['osc', 'linkpac', factory_name, pkg, proj_source])
    time.sleep(1)
    return ret


broken_packages = list_broken_packages(project)
for elem in broken_packages:
    print(elem)
