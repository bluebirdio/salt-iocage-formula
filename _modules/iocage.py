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

def _iocage(**kwargs):
    return ioc.IOCage(**kwargs)


def _option_exists(name, **kwargs):
    '''
    Check if a given property `name` is in the all properties list
    '''
    return name in list_properties(name, **kwargs)


def _exec(cmd, output='stdout'):
    '''
    Execute commad `cmd` and returns output `output` (by default returns the
    stdout)
    '''
    cmd_ret = __salt__['cmd.run_all'](cmd)
    if cmd_ret['retcode'] == 0:
        return cmd_ret[output]
    else:
        raise CommandExecutionError(
            'Error in command "%s" : %s' % (cmd, str(cmd_ret)))


def _parse_properties(**kwargs):
    '''
    Returns a rendered properties string used by iocage command line properties
    argument
    '''
    default_properties = _get_default()

    default_properties.append('pkglist')

    for prop in kwargs.keys():
        if not prop.startswith('__') and prop not in default_properties:
            raise SaltInvocationError('Unknown property %s' % (prop,))

    return ' '.join(
        ['%s="%s"' % (k, v) for k, v in kwargs.items() if not k.startswith('__')])


def _manage_state(state, jail_name, **kwargs):
    '''
    Start / Stop / Reboot / Destroy a jail `jail_name`
    '''
    jail = get(jail_name)

    if jail is None:
        raise SaltInvocationError('jail does not exist:' % (jail_name))
    else
        manager = _iocage(jail=jail_name)

    running = (get_property('jid', jail_name) is not None)

    if (state == 'start'):
        if running:
            raise SaltInvocationError(
                'jail %s is already started' % (jail_name,))
            manger.start()
    elif (state == 'stop'):
        if !running:
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
    return _iocage(jail=jail_name, skip_jails=True).list("all")


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


def list_properties(jail_name, **kwargs):
    '''
    List all properies for a given jail or defaults value

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.list_properties <jail_name>
        salt '*' iocage.list_properties defaults
    '''
    # Return the same output with defaults or for a given jail
    if (jail_name == 'defaults'):
        return _get_default('all')
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
        return _get_default(property_name)
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


    return _iocage(jail=jail_name).set(prop)
    return _exec('iocage set %s %s' % (_parse_properties(**kwargs), jail_name))


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


def _get_default(property='all'):
    return _iocage(jail='default').get(property)


def create(jail_type="full", template_id=None, **kwargs):
    '''
    Create a new jail

    CLI Example:

    .. code-block:: bash

        salt '*' iocage.create [<option>] [<property=value>]

            def create(self,
               release,
               props,
               count=0,
               pkglist=None,
               template=False,
               short=False,
               _uuid=None,
               basejail=False,
               thickjail=False,
               empty=False,
               clone=None,
               skip_batch=False,
               thickconfig=False,
               clone_basejail=False):
    '''
    _options = ['full', 'clone', 'base', 'empty', 'template-clone']
    defaults = _get_default()

    if jail_type not in _options:
        raise SaltInvocationError('Unknown option %s' % (jail_type,))

    # Get release from arguments or from defaults.
    if 'release' in kwargs.keys():
        release = kwargs['release']
    else:
        release = defaults['release']
    fetch(release)

    properties = []
    args = []

    return _iocage().create(release, properties, args)

    # check template exists for cloned template
    if jail_type == 'template-clone':
        if template_id == None:
            raise SaltInvocationError('template_id not specified for cloned template')
        templates = __salt__['iocage.list_templates']().split('\n')
        tmpl_exists = False
        for tmpl in templates:
            tmpl_datas = {t.split('=')[0]: '='.join(t.split('=')[1:])
                          for t in tmpl.split(',')}
            if tmpl_datas['TAG'] == template_id or tmpl_datas['UUID'] == template_id:
                tmpl_exists = True
                break
        if tmpl_exists == False:
            raise SaltInvocationError('Template id %s does not exist' % (template_id,))


    # stringify the kwargs dict into iocage create properties format
    properties = _parse_properties(**kwargs)

    # if we would like to specify a tag value for the jail
    # check if another jail have not the same tag
    if 'tag' in kwargs.keys():
        if kwargs['tag'] in [k['TAG'] for k in list_jails()]:
            raise SaltInvocationError(
                'Tag %s already exists' % (kwargs['tag'],))

    pre_cmd = 'iocage create'
    if jail_type == 'clone':
        pre_cmd = 'iocage create -c'
    if jail_type == 'base':
        pre_cmd = 'iocage create -b'
    if jail_type == 'empty':
        pre_cmd = 'iocage create -e'
    if jail_type == 'template-clone':
        pre_cmd = 'iocage clone %s' % (template_id)

    # fetch a release if it's the first install
    existing_release = list_releases()
    if len(existing_release) == 0:
        fetch()


    if len(properties) > 0:
        cmd = '%s %s' % (pre_cmd, properties)
    else:
        cmd = 'iocage create %s' % (properties,)
    return _exec(cmd)



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
