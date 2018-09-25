#!/usr/bin/python3
import argparse
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

FACTORY_NAME = "openSUSE:Factory"

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
# https://build.opensuse.org/apidocs/index
opener = urllib.request.build_opener(https_handler, auth_handler)

src_URL = "%s/source/{}" % OBS_API

failed = queue.Queue()

def project_list(url):
    with opener.open(url, timeout=10) as response:
        assert response.status == 200
        for event, element in etree.iterparse(response):
            if element.tag == 'entry':
                yield element.attrib['name']


def get_spec_file(proj_name, pname):
    get_URL = src_URL.format('{}/{}/{}.spec').format(proj_name, pname, pname)
    log.debug('get_URL = %s', get_URL)
    print(pname[0], file=sys.stderr, end='', flush=True)
    try:
        with opener.open(get_URL) as response:
            with open('{}.spec'.format(pname), 'wb') as outf:
                while True:
                    buf = response.read(1024*8)
                    if not buf:
                        break
                    outf.write(buf)
            return True, pname, 200
    except urllib.error.URLError:
        return False, pname, response.status


arg_p = argparse.ArgumentParser(description='Collect all SPEC files for a project.')
arg_p.add_argument('project_name', nargs='?', default=FACTORY_NAME)
args = arg_p.parse_args()
proj = args.project_name

packages = (x for x in project_list(src_URL.format(proj)))

futures = []
with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PROCS) as executor:
    for id_proj in packages:
        futures.append(executor.submit(get_spec_file, proj, id_proj))

failed_tasks = []
for f in concurrent.futures.as_completed(futures):
    task = f.result()
    if not task[0]:
        failed_tasks.append(task)

log.debug('failed_tasks = %s', failed_tasks)

print(file=sys.stderr)
log.info('Downloaded %d files.', len(packages) - len(failed_tasks))

for task in failed_tasks:
    log.error('Downloading of %s failed with status %d', task[1], task[2])

sys.exit(0 if len(failed_tasks) == 0 else 1)
