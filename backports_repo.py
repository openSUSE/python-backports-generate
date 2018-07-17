#!/usr/bin/python3
import base64
import concurrent.futures
import configparser
import logging
import os.path
import urllib.parse
import urllib.request
import xml.etree.ElementTree as etree

logging.basicConfig(format='%(levelname)s:%(funcName)s:%(message)s',
                    level=logging.DEBUG)
log = logging.getLogger('backports_repo')

project = "devel:languages:python:backports"

cfg = configparser.ConfigParser()
cfg.read(os.path.expanduser('~/.config/osc/oscrc'))
OBS_API = 'https://api.opensuse.org'
OBS_cfg = cfg[OBS_API]

pwd_mgr = urllib.request.HTTPPasswordMgrWithPriorAuth()
pwd_mgr.add_password(realm=None, uri=OBS_API,
                     user=OBS_cfg['user'],
                     passwd=OBS_cfg['pass'])
https_handler = urllib.request.HTTPSHandler(debuglevel=0)
auth_handler = urllib.request.HTTPBasicAuthHandler(pwd_mgr)
opener = urllib.request.build_opener(https_handler, auth_handler)

src_URL = "%s/source/{}" % OBS_API

backports_python = None
factory_python = None

def get_xml_list(url):
    with opener.open(url, timeout=10) as response:
        assert response.status == 200
        for event, element in etree.iterparse(response):
            if element.tag == 'entry':
                yield element.attrib['name']

def rdelete(pkg, proj, comment):
    # GET https://api.opensuse.org/search/request?match=%28state%2F%40name%3D%27new%27+or+state%2F%40name%3D%27review%27+or+state%2F%40name%3D%27declined%27%29+and+%28action%2Ftarget%2F%40project%3D%27devel%3Alanguages%3Apython%3Abackports%27+or+submit%2Ftarget%2F%40project%3D%27devel%3Alanguages%3Apython%3Abackports%27+or+action%2Fsource%2F%40project%3D%27devel%3Alanguages%3Apython%3Abackports%27+or+submit%2Fsource%2F%40project%3D%27devel%3Alanguages%3Apython%3Abackports%27%29+and+%28action%2Ftarget%2F%40package%3D%27python-pycrypto%27+or+submit%2Ftarget%2F%40package%3D%27python-pycrypto%27+or+action%2Fsource%2F%40package%3D%27python-pycrypto%27+or+submit%2Fsource%2F%40package%3D%27python-pycrypto%27%29
    # DELETE https://api.opensuse.org/source/devel:languages:python:backports/python-pycrypto?comment=Package+python-pycrypto+not+in+whitelist+or+openSUSE%3AFactory
    #
    # match=(state/@name='new'+or+state/@name='review'+or+state/@name='declined')+and+(action/target/@project='devel:languages:python:backports'+or+submit/target/@project='devel:languages:python:backports'+or+action/source/@project='devel:languages:python:backports'+or+submit/source/@project='devel:languages:python:backports')+and+(action/target/@package='python-pycrypto'+or+submit/target/@package='python-pycrypto'+or+action/source/@package='python-pycrypto'+or+submit/source/@package='python-pycrypto')
    #
    # match=(state/@name='new' or state/@name='review' or state/@name='declined')
    #       and
    # (action/target/@project='devel:languages:python:backports' or
    #        submit/target/@project='devel:languages:python:backports' or
    #        action/source/@project='devel:languages:python:backports' or
    #        submit/source/@project='devel:languages:python:backports')
    #       and
    # (action/target/@package='python-pycrypto' or
    #        submit/target/@package='python-pycrypto' or
    #        action/source/@package='python-pycrypto' or
    #        submit/source/@package='python-pycrypto')
    comment = urllib.parse.quote_plus(comment)
    rdelete_URL = src_URL.format(f'{proj}/{pkg}?comment={comment}')
    headers = {}
    print('url:\n%s' % rdelete_URL)

def linkpac(pkg, proj_source):
    # GET https://api.opensuse.org/source/devel%3Alanguages%3Apython%3Abackports/python-atom/_meta
    # GET https://api.opensuse.org/source/openSUSE:Factory/python-atom/_meta
    # Sending meta data...
    # PUT https://api.opensuse.org/source/devel:languages:python:backports/python-atom/_meta
    # Done.
    # GET https://api.opensuse.org/source/devel:languages:python:backports/python-atom?rev=latest
    # PUT https://api.opensuse.org/source/devel:languages:python:backports/python-atom/_link
    proj_target = 'openSUSE:Factory'
    print(['osc', 'linkpac', proj_target, pkg, proj_source])

backports_python = {x for x in get_xml_list(src_URL.format(project))}
factory_python = {x for x in get_xml_list(src_URL.format('openSUSE:Factory'))
                  if x.startswith('python')}
python_itself = {"python-base", "python3-base", "python", "python3",
                 "python-doc", "python3-doc"}

# extra packages we want there
additional_links = {"libcryptopp", "libsodium", "qpid-proton",
                    "openstack-macros"}

factory_python = factory_python | additional_links

# remove packages not in tumbleweed
for i in backports_python - factory_python:
    msg = f"Package {i} not in whitelist or openSUSE:Factory"
    log.debug('rdelete i = %s', i)
    rdelete(i, project, msg)

# add packages not in yet
for i in factory_python - python_itself - backports_python:
    log.debug('linkpac i = %s', i)
    linkpac(i, project)
