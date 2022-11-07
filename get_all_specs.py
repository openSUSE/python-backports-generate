#!/usr/bin/python3
import argparse
import configparser
import getpass
import logging
import os.path
import re
import queue
import sys
import urllib.error
import urllib.parse
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
IBS_API = 'https://api.suse.de'
END_NUM_RE = re.compile(r'\.\d+$')

MAX_PROCS = 20

failed = queue.Queue()
src_URL = None
opener = None


def get_opener(use_IBS=True):
    # available in python >= 3.5
    if use_IBS:
        api = IBS_API
    else:
        api = OBS_API

    OBS_cfg = cfg[api]
    pwd_mgr = urllib.request.HTTPPasswordMgrWithPriorAuth()
    OBS_user = OBS_cfg['user'] if 'user' in OBS_cfg else input('Login: ')
    OBS_pass = OBS_cfg['pass'] if 'pass' in OBS_cfg else getpass.getpass()
    pwd_mgr.add_password(realm=None, uri=api,
                         user=OBS_user,
                         passwd=OBS_pass)
    https_handler = urllib.request.HTTPSHandler(debuglevel=0)
    auth_handler = urllib.request.HTTPBasicAuthHandler(pwd_mgr)
    # https://build.opensuse.org/apidocs/index
    out = urllib.request.build_opener(https_handler, auth_handler)
    return out, "%s/source/{}?expand=1" % api


def project_list(url):
    log.debug('url = %s', url)
    with opener.open(url, timeout=10) as response:
        assert response.status == 200
        for event, element in etree.iterparse(response):
            if element.tag == 'entry':
                yield element.attrib['name']


def get_file(proj_name, pname, filename_extension):
    response = None
    get_URL = src_URL.format('{}/{}/{}.' + filename_extension).format(
        urllib.parse.quote(proj_name), pname, pname)
    print(pname[0], file=sys.stderr, end='', flush=True)
    try:
        log.debug('get_URL = %s', get_URL)
        with opener.open(get_URL) as response:
            with open(('{}.'+filename_extension).format(pname), 'wb') as outf:
                while True:
                    buf = response.read(1024*8)
                    if not buf:
                        break
                    outf.write(buf)
            return True, pname, 200, ''
    except (urllib.error.URLError, urllib.error.HTTPError) as ex:
        return False, pname, ex.code, ex.reason


arg_p = argparse.ArgumentParser(
    description='Collect all SPEC files for a project.')
arg_p.add_argument('project_name', nargs='?', default=FACTORY_NAME,
                   help='project name in OBS (e.g., {})'.format(FACTORY_NAME))
arg_p.add_argument('-I', '--IBS', action='store_true',
                   help='prefer internal OBS over the public one')
arg_p.add_argument('--include-changelog', action='store_true',
                   help='also fetch changelogs ')
args = arg_p.parse_args()
log.debug('args = %s', args)
proj = args.project_name

opener, src_URL = get_opener(args.IBS)
log.debug('src_URL = %s', src_URL.format(proj))

packages = (x for x in project_list(src_URL.format(proj))
            if END_NUM_RE.search(x) is None)

futures = []
file_counter = 0
with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_PROCS) as executor:
    for id_proj in packages:
        file_counter += 1
        futures.append(executor.submit(get_file, proj, id_proj, 'spec'))
        if args.include_changelog:
            file_counter += 1
            futures.append(executor.submit(get_file, proj, id_proj, 'changes'))

failed_tasks = []
for f in concurrent.futures.as_completed(futures):
    task = f.result()
    if not task[0]:
        failed_tasks.append(task)

log.debug('failed_tasks = %s', failed_tasks)

print(file=sys.stderr)
log.info('Downloaded %d files.', file_counter - len(failed_tasks))

for task in failed_tasks:
    log.error('Downloading of %s failed with status %d:\n%s',
              task[1], task[2], task[3])

sys.exit(0 if len(failed_tasks) == 0 else 1)
