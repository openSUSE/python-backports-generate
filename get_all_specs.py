#!/usr/bin/python3
import configparser
import logging
import os.path
import queue
import time
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as etree
import concurrent.futures

logging.basicConfig(format='%(levelname)s:%(funcName)s:%(message)s',
                    level=logging.INFO)
log = logging.getLogger('get_all_specs')

project = "devel:languages:python:backports"
factory_name = "openSUSE:Factory"

cfg = configparser.ConfigParser()
cfg.read(os.path.expanduser('~/.config/osc/oscrc'))
OBS_API = 'https://api.opensuse.org'
OBS_cfg = cfg[OBS_API]
MAX_PROCS = 100

# available in python >= 3.5
pwd_mgr = urllib.request.HTTPPasswordMgrWithPriorAuth()
pwd_mgr.add_password(realm=None, uri=OBS_API,
                     user=OBS_cfg['user'],
                     passwd=OBS_cfg['pass'])
https_handler = urllib.request.HTTPSHandler(debuglevel=0)
auth_handler = urllib.request.HTTPBasicAuthHandler(pwd_mgr)
opener = urllib.request.build_opener(https_handler, auth_handler)

src_URL = "%s/source/{}" % OBS_API

failed = queue.Queue()

def project_list(url):
    with opener.open(url, timeout=10) as response:
        assert response.status == 200
        for event, element in etree.iterparse(response):
            if element.tag == 'entry':
                yield element.attrib['name']


def get_spec_file(pname):
    get_URL = src_URL.format('openSUSE:Factory/{}/{}.spec')
    print(pname[0], file=sys.stderr, end='', flush=True)
    try:
        with opener.open(get_URL.format(pname, pname)) as response:
            with open('{}.spec'.format(pname), 'wb') as outf:
                while True:
                    buf = response.read(1024*8)
                    if not buf:
                        break
                    outf.write(buf)
            return True, pname, 200
    except urllib.error.URLError:
        return False, pname, response.status

packages = (x for x in project_list(src_URL.format('openSUSE:Factory')))

futures = []
with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PROCS) as executor:
    futures = executor.map(get_spec_file, packages)

failed_tasks = []
for f in concurrent.futures.as_completed(futures):
    task = f.result()
    if not task[0]:
        failed_tasks.append(task)

print(file=sys.stderr)
log.info('Downloaded %d files.', len(packages) - len(failed_tasks))

for task in failed_tasks:
    log.error('Downloading of %s failed with status %d', task[1], task[2])

sys.exit(0 if len(failed_tasks) == 0 else 1)
