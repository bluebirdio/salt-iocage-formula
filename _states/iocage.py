# -*- coding: utf-8 -*-
'''
Support for iocage (jails tools on FreeBSD)
'''
from __future__ import absolute_import
import logging
log = logging.getLogger(__name__)

def property(name, value, jail='default', **kwargs):
    ret = {'name': name,
           'changes': {},
           'comment': '',
           'result': False}

    print("HELLP")
    print(name)
    print(value)
    print(jail)
    try:
        old_value = __salt__['iocage.get_property'](name, jail, **kwargs)
        print(old_value)

    except:
        if __opts__['test']:
            ret['result'] = None
            if jail == 'default':
                ret['comment'] = 'default option %s doesn\'t exist' % ( name,)
            else:
                ret['comment'] = 'jail option %s seems to not exist' % (name,)
        else:
            ret['result'] = False
            if jail == 'default':
                ret['comment'] = 'default option %s does not exist' % (name,)
            else:
                ret['comment'] = 'jail option %s does not exist' % (name,)
    else:
        if value != old_value:
            if not __opts__['test']:
                ret.update(__salt__['iocage.set_properties'](jail, **{name: value}))
            else:
                ret['result'] = None
        else:
            if __opts__['test']:
                ret['result'] = None
            else:
                ret['result'] = True

    return ret


def managed(name, properties={}, jail_type="clone", template_id=None, **kwargs):
    ret = {'name': name,
           'changes': {},
           'comment': '',
           'result': False}

    # Get all properties for this jail
    jail = __salt__['iocage.get'](name)

    # The jail does not exist. Create it!
    if jail is None:
        if not __opts__['test']:
            #properties = __salt__['iocage.filter_properties'](properties)

            ret['comment'] = 'Creating iocage jail.'
            ret['result'] = __salt__['iocage.create'](jail_name=name, jail_type=jail_type, template_id=template_id, properties=properties, **kwargs)

    # Verify and update properties on existing jail.
    else:
        if not __opts__['test']:
            ret.update(__salt__['iocage.set_properties'](name, **properties))

        if len(ret['changes']):
            ret['comment'] = 'Updated %s\'s jail properties.' % ( name,)
        else:
            ret['comment'] = 'No changes required.'

    return ret

if __name__ == "__main__":
    __salt__ = ''
    __opts__ = ''

    import sys
    sys.exit(0)
