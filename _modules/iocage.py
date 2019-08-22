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
        raise CommandExecutionError('iocage error: ' . content['message'])
    else:
        print(content['message'])
    

def _iocage(**kwargs):
    kwargs['callback'] = '_iocage_error'
    kwargs['silent'] = True
    
    return ioc.IOCage(**kwargs)


def filter_properties(properties):
    '''
    Returns a rendered properties string used by iocage command line properties
    argument
    '''
    filtered = {}
    defaults = list(_defaults())

    # Append pkglist, which is valid for create.
    #defaults.append('pkglist')
    #defaults.append('state')
    #defaults.append('release')

    for prop in properties.keys():
        if not prop.startswith('__'):
            if prop in defaults:
                filtered[prop] = properties[prop]
        
    return filtered


def _manage_state(state, jail_name, **kwargs):
    '''
    Start / Stop / Reboot / Destroy a jail `jail_name`
    '''
    if get(jail_name) is None:
        raise SaltInvocationError('jail does not exist: %s' % (jail_name,))

    manager = _iocage(jail=jail_name)

    running = (get_property('state', jail_name) is 'up')

    if (state == 'start'):
        if running:
            raise SaltInvocationError('jail %s is already started' % (jail_name,))
        manager.start()

    elif (state == 'stop'):
        if not running:
            raise SaltInvocationError('jail %s is not running' % (jail_name,))
        manager.stop()

    elif (state == 'restart'):
        manager.restart()


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


def _format_property(name, value):
    '''
    iocage expects properties as 'k=v' strings:
    Return a list of strings appropriate for set_properties and create functions.
    '''
    return name + '=' + str(value)


def set_properties(jail_name, **kwargs):
    '''
    Set property value for a given jail

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.set_properties <jail_name> [<property=value>]
    '''
    if jail_name == 'defaults':
        jail_name = 'default'

    exclusions = ['CONFIG_VERSION', 'last_started', 'mountpoint',
            'origin', 'used', 'available']

    iocage = _iocage(jail=jail_name)

    # "Before" state; current state of the jail.
    current = iocage.get('all')

    # Desired state is defaults + passed-in properties.
    desired = _iocage(jail='default').get('all')
    desired.update(kwargs)

    # Special case for state: you can't change this value.
    desired_state = (desired.pop('state', current['state']) == 'up')
    current_state = (current['state'] == 'up')

    result = True
    changes = {}
    for key, val in desired.items():
        if key in exclusions:
            continue

        prop = _format_property(key, val)
        orig = _format_property(key, current[key]) if key in current else ""

        if prop != orig:
            iocage.set(prop)
            changes[key] = {'new': val, 'old': current[key]}

            # Verify that the property has changed.
            result = result and (prop == _format_property(key, iocage.get(key)))

    if current_state != desired_state:
        action = 'start' if desired_state else 'stop'
        _manage_state(action, jail_name)

    return {'result': result, 'changes': changes }


def fetch(release, **kwargs):
    '''
    Download or update/patch release

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.fetch
        salt '*' iocage.fetch <release>
    '''
    kwargs['release'] = release

    return _iocage().fetch(**kwargs)


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


def create(jail_name, jail_type="full", template_id=None, properties={}, **kwargs):
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
            'clone':None
            # These are relatively new: https://github.com/iocage/iocage/pull/867
            #'skip_batch':False,
            #'thickconfig':False,
            #'clone_basejail':False
    }

    iocage = _iocage()
    defaults = _defaults()

    _jail_types = ['full', 'clone', 'base', 'empty', 'template-clone']

    if jail_type not in _jail_types:
        raise SaltInvocationError('Unknown option %s' % (jail_type,))
    else:
        if jail_type == 'full':
            args['thickjail'] = True
            template_id = release
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
    release = kwargs['release'] if ('release' in kwargs.keys()) else None

    # Get package list from arguments
    args['pkglist'] = kwargs['pkglist'] if ('pkglist' in kwargs.keys()) else None

    # State can not be passed in as a property but we want to know about it.
    desired_state = (properties.pop('state', None) == 'up')

    print(properties)
    property_list = []
    for k, v in properties.items():
        property_list.append(_format_property(k, v))
    #for k, v in filter_properties(properties).items():
        #property_list.append(_format_property(k, v))


    # TODO This may be an unpopular assumption.
    args['_uuid'] = jail_name

    # check template exists for cloned template
    if jail_type == 'template-clone':
        if template_id == None:
            raise SaltInvocationError('template_id not specified for cloned template')
        else:
            args['template'] = True
            release = template_id
            iocage.jail = template_id
    elif jail_type is 'clone':
        args['clone'] = template_id
        iocage.jail = template_id
    elif jail_type is 'empty' and release is None:
        raise SaltInvocationError('Must specify a release or a template_id')

    print(args)
    print(properties)
    print(iocage.jails.items())
    result = iocage.create(release, property_list, **args)
    result = result and (start(jail_name) if desired_state else True)

    return result


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
