#!/usr/bin/python3
import argparse
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

logging.basicConfig(format='%(levelname)s:%(funcName)s:%(message)s',
                    level=logging.INFO)
log = logging.getLogger('backports_repo')


def _get_osc_config(config_file, config_section):
    """
    Get the osc (OpenBuildService command line client) config
    for the the given config_section
    """
    if not os.path.exists(config_file):
        raise Exception('Config file {} does not exist'.format(config_file))
    cfg = configparser.ConfigParser()
    cfg.read(os.path.expanduser('~/.config/osc/oscrc'))
    return cfg[config_section]


def _get_opener(obs_api, obs_user, obs_password):
    # available in python >= 3.5
    pwd_mgr = urllib.request.HTTPPasswordMgrWithPriorAuth()
    pwd_mgr.add_password(realm=None, uri=obs_api,
                         user=obs_user,
                         passwd=obs_password)
    https_handler = urllib.request.HTTPSHandler(debuglevel=0)
    auth_handler = urllib.request.HTTPBasicAuthHandler(pwd_mgr)
    opener = urllib.request.build_opener(https_handler, auth_handler)
    return opener


def project_list(opener, url):
    with opener.open(url, timeout=10) as response:
        assert response.status == 200
        for _, element in etree.iterparse(response):
            if element.tag == 'entry':
                yield element.attrib['name']


def rdelete(factory_project, pkg, proj):
    msg = "Package {} not in whitelist or {}".format(pkg, factory_project)
    log.info("osc rdelete %(msg)s %(proj)s %(pkg)s" % {
        'msg': msg, 'proj': proj, 'pkg': pkg})
    ret = subprocess.call(['osc', 'rdelete', '-m', msg, proj, pkg])
    time.sleep(1)
    return ret


def linkpac(factory_project, pkg, proj_source):
    log.info("osc linkpac %(factory_project)s %(pkg)s %(proj_source)s" % {
             'factory_project': factory_project,
             'pkg': pkg,
             'proj_source': proj_source})
    ret = subprocess.call(['osc', 'linkpac',
                          factory_project, pkg, proj_source])
    time.sleep(1)
    return ret


def _get_from_config():
    conf_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'backports_repo.json')
    with io.open(conf_file) as conf_f:
        obj = json.load(conf_f)
        if 'additional_links' not in obj:
            raise KeyError(
                '"additional_links" not found in configuration file %s' %
                conf_file)
    return obj


def main(args):
    osc_cfg = _get_osc_config(os.path.expanduser('~/.config/osc/oscrc'),
                              args.obs_api)
    opener = _get_opener(args.obs_api, osc_cfg['user'], osc_cfg['pass'])
    # packages already in the backports project
    backports_python = {x for x in project_list(opener, '{}/source/{}'.format(
        args.obs_api, args.backports_project))}
    # packages already in the factory project
    factory_python = {x for x in project_list(opener, '{}/source/{}'.format(
        args.obs_api, args.factory_project)) if x.startswith('python')}
    python_itself = {"python-base", "python3-base", "python", "python3",
                     "python-doc", "python3-doc"}
    # additional link we want to link from Factory to Backports
    # also, list of all packages which are not Pyhon in the full meaning
    # of the word
    config_json = _get_from_config()
    additional_links = set(config_json['additional_links'])
    ignore_list_factory = set(config_json['ignore_list_factory'])
    ignore_list_backports = set(config_json['ignore_list_backports'])

    log.debug('additional_links = %s' % additional_links)
    log.debug('ignore_list_factory = %s' % ignore_list_factory)
    log.debug('ignore_list_backports = %s' % ignore_list_backports)

    backports_python -= ignore_list_backports

    factory_python = factory_python | additional_links
    factory_python -= ignore_list_factory
    log.debug('factory_python = %s' % factory_python)

    futures = []
    with concurrent.futures.ThreadPoolExecutor(
            max_workers=args.max_workers) as executor:
        # remove packages not in tumbleweed
        for package in backports_python - factory_python:
            futures.append(executor.submit(rdelete, args.factory_project,
                                           package, args.backports_project))

        # add packages not in yet
        for package in factory_python - python_itself - backports_python:
            futures.append(executor.submit(linkpac, args.factory_project,
                                           package, args.backports_project))

        results = []
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

        results = [x for x in results if x != 0]

        return(len(results))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Update the backports repo '
                                     'with packages from openSUSE:Factory')
    parser.add_argument('--obs-api', default='https://api.opensuse.org',
                        help='The OpenBuildService API to use. Defaults to '
                        '%(default)s')
    parser.add_argument('--backports-project',
                        default='devel:languages:python:backports',
                        help='The OpenBuildService backportsproject. Defaults '
                        'to %(default)s')
    parser.add_argument('--factory-project',
                        default='openSUSE:Factory',
                        help='The OpenBuildService Factory project. Defaults '
                        'to %(default)s')
    parser.add_argument('--max-workers', type=int,
                        default=5, help='Number of workers. Defaults '
                        'to %(default)s')

    args = parser.parse_args()
    sys.exit(main(args))
