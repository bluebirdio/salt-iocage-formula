# -*- coding: utf-8 -*-
'''
Support for iocage (jails tools on FreeBSD)
'''
from __future__ import absolute_import
import logging
log = logging.getLogger(__name__)

def _property(name, value, jail, **kwargs):
    ret = {'name': name,
           'changes': {},
           'comment': '',
           'result': False}

    try:
        old_value = __salt__['iocage.get_property'](name, jail, **kwargs)

        if jail == 'defaults':
            jail = 'default'
    except:
        if __opts__['test']:
            ret['result'] = None
            if jail == 'default':
                ret['comment'] = 'default option %s seems do not exist' % (
                    name,)
            else:
                ret['comment'] = 'jail option %s seems do not exist' % (name,)
        else:
            ret['result'] = False
            if jail == 'default':
                ret['comment'] = 'default option %s does not exist' % (name,)
            else:
                ret['comment'] = 'jail option %s does not exist' % (name,)
    else:
        if value != old_value:
            ret['changes'] = {'new': value, 'old': old_value}

            if not __opts__['test']:
                try:
                    __salt__['iocage.set_property'](jail, **{name: value})
                except:
                    ret['result'] = False
                else:
                    ret['result'] = True
            else:
                ret['result'] = None
        else:
            if __opts__['test']:
                ret['result'] = None
            else:
                ret['result'] = True

    return ret


def property(name, value, jail=None, **kwargs):
    if jail is None:
        return _property(name, value, 'defaults', **kwargs)
    else:
        return _property(name, value, jail, **kwargs)


def managed(name, properties={}, jail_type="full", template_id=None, **kwargs):
    ret = {'name': name,
           'changes': {},
           'comment': '',
           'result': False}

    print(__salt__['environ.items']())
    #if len(kwargs.keys()) > 0 :
        #properties.update(**kwargs)

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
