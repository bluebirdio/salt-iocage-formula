# -*- coding: utf-8 -*-
'''
Support for iocage (jails tools on FreeBSD)
'''
from __future__ import absolute_import

# Import python libs
# import os

import logging
# Import salt libs
import salt.utils
from salt.exceptions import CommandExecutionError, SaltInvocationError

import iocage_lib.iocage as ioc

log = logging.getLogger(__name__)

__virtualname__ = 'iocage'


def __virtual__():
    '''
    Module load only if iocage is installed
    '''
    if salt.utils.which('iocage'):
        return __virtualname__
    else:
        return False


def _iocage_error(content, exception):
    if content['level'] in ['EXCEPTION', 'ERROR', 'CRITICAL']:
        raise CommandExecutionError(content['message'])
    else:
        print(content['message'])
    

def _iocage(**kwargs):
    iocage = ioc.IOCage(**kwargs)
    iocage.callback = '_iocage_error'
    return iocage


def _option_exists(name, **kwargs):
    '''
    Check if a given property `name` is in the all properties list
    '''
    return name in properties(name, **kwargs)


def _filter_properties(jail, **kwargs):
    '''
    Returns a rendered properties string used by iocage command line properties
    argument
    '''
    props = []
    defaults = _defaults().keys()

    defaults.append('pkglist')

    for prop in kwargs.keys():
        if not prop.startswith('__'):
            if prop not in defaults:
                raise SaltInvocationError('Unknown property %s' % (prop,))
            else:
                props[prop] = kwargs[prop]
        
    return props


def _manage_state(state, jail_name, **kwargs):
    '''
    Start / Stop / Reboot / Destroy a jail `jail_name`
    '''
    if get(jail_name) is None:
        raise SaltInvocationError('jail does not exist: %s' % (jail_name,))
    else:
        manager = _iocage(jail=jail_name)

    running = (get_property('state', jail_name) is 'up')

    if (state == 'start'):
        if running:
            raise SaltInvocationError(
                'jail %s is already started' % (jail_name,))
            manger.start()
    elif (state == 'stop'):
        if not running:
            raise SaltInvocationError(
                'jail %s is not running' % (jail_name,))
            manger.stop()
    elif (state == 'restart'):
            manger.restart()


def list_jails(**kwargs):
    '''
    Get list of jails

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.list_jails
    '''
    return _iocage().list("all")


def list_templates(**kwargs):
    '''
    Get list of template jails

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.list_templates
    '''
    return _iocage().list("template")


def list_releases(**kwargs):
    '''
    Get list of downloaded releases

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.list_releases
    '''
    return _iocage().list("base")


def properties(jail_name, **kwargs):
    '''
    List all properies for a given jail or defaults value

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.properties <jail_name>
        salt '*' iocage.properties defaults
    '''
    # Return the same output with defaults or for a given jail
    if (jail_name == 'defaults'):
        return _defaults('all')
    else: 
        return get(jail_name)


def get_property(property_name, jail_name, **kwargs):
    '''
    Get property value for a given jail (or default value)

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.get_property <property> <jail_name>
        salt '*' iocage.get_property <property> defaults
    '''

    # Return the same output with defaults or for a given jail
    if (jail_name == 'defaults'):
        return _defaults(property_name)
    else: 
        return get(jail_name, property_name)


def set_property(jail_name, **kwargs):
    '''
    Set property value for a given jail

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.set_property <jail_name> [<property=value>]
    '''
    if jail_name == 'defaults':
        jail_name = 'default'

    for k, v in _filter_properties(jail_name, **kwargs):
        prop = k + '=' + v

        # Properties are expected as text: 'key=val'
        _iocage(jail=jail_name).set(prop)


def fetch(release=None, **kwargs):
    '''
    Download or update/patch release

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.fetch
        salt '*' iocage.fetch <release>
    '''
    args = []
    if release is not None:
        args['release'] = release

    args['release'] = release
    return _iocage().fetch(args)


def get(jail_name, property='all', **kwargs):
    '''
    Get all propeties for a jail

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.get <jail_name>
    '''
    try:
        jail = None
        iocage = _iocage(jail=jail_name)

        for j in iocage.jails.items():
            if j[0] == jail_name:
                jail = iocage.get(property)
                break
    except RuntimeError:
        return None

    return jail


def _defaults(property='all'):
    return _iocage(jail='default').get(property)


def create(jail_type="full", template_id=None, **kwargs):
    '''
    Create a new jail

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.create [<option>] [<property=value>]
    '''

    # These are the default inputs for iocage's create() call.
    release = ''
    args = {
            'count':0,
            'pkglist':None,
            'template':False,
            'short':False,
            '_uuid':None,
            'basejail':False,
            'thickjail':False,
            'empty':False,
            'clone':None,
            'skip_batch':False,
            'thickconfig':False,
            'clone_basejail':False
    }

    defaults = _defaults()

    _jail_types = ['full', 'clone', 'base', 'empty', 'template-clone']

    if jail_type not in _jail_types:
        raise SaltInvocationError('Unknown option %s' % (jail_type,))
    else:
        if jail_type == 'full':
            args['thickjail'] = True
        elif jail_type == 'base':
            args['basejail'] = True
        elif jail_type == 'empty':
            args['empty'] = True
        elif jail_type == 'clone':
            if 'clone' in kwargs.keys():
                args['clone'] = kwargs['clone']
            else:
                raise SaltInvocationError('Clone not specified for cloned jail')


    # Get release from arguments or from defaults.
    release = kwargs['release'] if ('release' in kwargs.keys()) else defaults['release']
    fetch(release)

    properties = _filter_properties(**kwargs)


    # check template exists for cloned template
    if jail_type == 'template-clone':
        if template_id == None:
            raise SaltInvocationError('template_id not specified for cloned template')

    return _iocage().create(release, properties, args)


def start(jail_name, **kwargs):
    '''
    Start a jail

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.start <jail_name>
    '''
    return _manage_state('start', jail_name, **kwargs)


def stop(jail_name, **kwargs):
    '''
    Stop a jail

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.stop <jail_name>
    '''
    return _manage_state('stop', jail_name, **kwargs)


def restart(jail_name, **kwargs):
    '''
    Restart a jail

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.restart <jail_name>
    '''
    return _manage_state('restart', jail_name, **kwargs)


def update(jail_name, pkgs=False, **kwargs):
    '''
    Updates a jail to the latest patchset.

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.update <jail_name> [pkgs=False]
    '''
    return _iocage(jail=jail_name).update(pkgs)


def destroy(jail_name, **kwargs):
    '''
    Destroy a jail

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.destroy <jail_name>
    '''
    # Function doc recommends skip_jails for performance.
    _iocage(jail=jail_name, skip_jails=True).destroy_jail()


if __name__ == "__main__":
    __salt__ = ''

    import sys
    sys.exit(0)
