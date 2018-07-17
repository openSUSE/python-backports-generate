#!/usr/bin/python3
import asyncio
import async_timeout
import aiohttp
import logging
import xml.etree.ElementTree as etree
from subprocess import check_call, check_output

logging.basicConfig(format='%(levelname)s:%(funcName)s:%(message)s',
                    level=logging.DEBUG)
log = logging.getLogger('asyncio')

project = "devel:languages:python:backports"

loop = asyncio.get_event_loop()
auth = aiohttp.BasicAuth(login='mcepl', password='7vR$7By@Lj')
client = aiohttp.ClientSession(loop=loop, auth=auth)

# curl -u '' https://api.opensuse.org/source/devel:languages:python:backports
ls_URL = "https://api.opensuse.org/source/{}"

async def get_xml_list(url):
    with async_timeout.timeout(10):
        async with client.get(url) as response:
            assert response.status == 200
            for event, element in etree.iterparse(response):
                log.debug('event = %s, element = %s', event, element)
                if element.tag == 'entry':
                    yield element.attr('name')

async def get_backports():
    raw_data = await get_xml_list(ls_URL.format(project))
    print(set(raw_data))

loop.run_until_complete(get_backports())

##
##
## backports_python =
## factory_python_raw = check_output(['osc', 'ls', 'openSUSE:Factory']).split()
## factory_python = {x for x in factory_python_raw if x.startswith('python')}
##
## python_itself = {"python-base", "python3-base", "python", "python3",
##                  "python-doc", "python3-doc"}
##
## # extra packages we want there
## additional_links = {"libcryptopp", "libsodium", "qpid-proton",
##                     "openstack-macros"}
##
## factory_python = factory_python | additional_links
##
## # remove packages not in tumbleweed
## for i in backports_python - factory_python:
##     msg = f"Package {i} not in whitelist or openSUSE:Factory"
##     check_call(['osc', 'rdelete', i, '-m', msg])
##
## # add packages not in yet
## for i in factory_python - python_itself - backports_python:
##     check_call(['osc', 'linkpac', 'openSUSE:Factory', i, project])
