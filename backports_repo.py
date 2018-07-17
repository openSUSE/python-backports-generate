#!/usr/bin/python3
import asyncio
import async_timeout
import aiohttp
import configparser
import logging
import os.path
import xml.etree.ElementTree as etree

logging.basicConfig(format='%(levelname)s:%(funcName)s:%(message)s',
                    level=logging.DEBUG)
log = logging.getLogger('asyncio')

project = "devel:languages:python:backports"

loop = asyncio.get_event_loop()
cfg = configparser.ConfigParser(os.path.expanduser('~/.config/osc/oscrc'))
OBS_cfg = cfg['https://api.opensuse.org']
auth = aiohttp.BasicAuth(login=OBS_cfg['user'], password=OBS_cfg['pass'])
client = aiohttp.ClientSession(loop=loop, auth=auth)

ls_URL = "https://api.opensuse.org/source/{}"

backports_python = None
factory_python = None

async def get_xml_list(url):
    with async_timeout.timeout(10):
        async with client.get(url) as response:
            assert response.status == 200
            for event, element in etree.iterparse(response):
                log.debug('event = %s, element = %s', event, element)
                if element.tag == 'entry':
                    yield element.attr('name')
            await response.release()

def do_work():
    global backports_python, factory_python
    backports_python = {x async for x in get_xml_list(ls_URL.format(project))}
    factory_python = {x async for x in get_xml_list(ls_URL.format('openSUSE:Factory'))}
    python_itself = {"python-base", "python3-base", "python", "python3",
                     "python-doc", "python3-doc"}

    # extra packages we want there
    additional_links = {"libcryptopp", "libsodium", "qpid-proton",
                        "openstack-macros"}

    factory_python = factory_python | additional_links

    # remove packages not in tumbleweed
    for i in backports_python - factory_python:
        msg = f"Package {i} not in whitelist or openSUSE:Factory"
        print(['osc', 'rdelete', i, '-m', msg])

    # add packages not in yet
    for i in factory_python - python_itself - backports_python:
        print(['osc', 'linkpac', 'openSUSE:Factory', i, project])

loop.run_until_complete(do_work())
