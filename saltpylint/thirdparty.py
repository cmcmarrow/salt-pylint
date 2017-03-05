# -*- coding: utf-8 -*-
'''
    :codeauthor: :email:`Pedro Algarvio (pedro@algarvio.me)`
    :copyright: © 2017 by the SaltStack Team, see AUTHORS for more details.
    :license: Apache 2.0, see LICENSE for more details.


    saltpylint.thirdparty
    ~~~~~~~~~~~~~~~~~~~~~

    Checks all imports against a list of known and allowed 3rd-party modules
    and raises a lint error if an import not in that known 3rd-party modules list
    is not gated.
'''

# Import python libs
from __future__ import absolute_import

# Import pylint libs
import astroid
import astroid.exceptions
from astroid.modutils import get_module_part, is_standard_module
from pylint.interfaces import IAstroidChecker
from pylint.checkers import BaseChecker
from pylint.checkers.utils import check_messages

MSGS = {
    'W8410': ('3rd-party module import is not gated: %s',
              '3rd-party-module-not-gated',
              '3rd-party module imported without being gated.'),
    }


def get_import_package(node, modname):
    '''
    Return the import package.

    Given modname is 'salt.utils', returns 'salt'
    '''
    return get_module_part(modname, node.root().file).split('.')[0]


class ThirdPartyImportsChecker(BaseChecker):

    __implements__ = IAstroidChecker

    name = '3rd-party-imports'
    msgs = MSGS
    priority = -2

    options = (
        ('allowed-3rd-party-modules', {
            'default': (),
            'type': 'csv',
            'metavar': '<3rd-party-modules>',
            'help': 'Known 3rd-party modules which don\' require being gated, separated by a comma'}),
    )

    def __init__(self, linter=None):
        BaseChecker.__init__(self, linter)
        self._inside_try_except = False
        self._allowed_3rd_party_modules = set(
                ('salt', ) + tuple(self.config.allowed_3rd_party_modules))  # pylint: disable=no-member

    @check_messages('3rd-party-imports')
    def visit_tryexcept(self, node):
        self._inside_try_except = True

    @check_messages('3rd-party-imports')
    def leave_tryexcept(self, node):
        self._inside_try_except = False

    @check_messages('3rd-party-imports')
    def visit_import(self, node):
        names = [name for name, _ in node.names]
        for name in names:
            self._check_third_party_import(node, name)

    @check_messages('3rd-party-imports')
    def visit_importfrom(self, node):
        self._check_third_party_import(node, node.modname)

    def _check_third_party_import(self, node, modname):
        if modname and modname in ('__future__',):
            # Don't even care about these
            return
        module_file = node.root().file
        try:
            imported_module = node.do_import_module(modname)
            importedmodname = get_module_part(imported_module.name, module_file)
            if not is_standard_module(importedmodname):
                if self._inside_try_except is False:
                    if get_import_package(node, modname) in self._allowed_3rd_party_modules:
                        return
                    self.add_message('3rd-party-module-not-gated', node=node, args=modname)
        except astroid.exceptions.InferenceError:
            # Failed to import
            if self._inside_try_except is False:
                if get_import_package(node, modname) in self._allowed_3rd_party_modules:
                    return
                self.add_message('3rd-party-module-not-gated', node=node, args=modname)
                return
        except ImportError:
            # Definitly not a standard library import
            if self._inside_try_except is False:
                if get_import_package(node, modname) in self._allowed_3rd_party_modules:
                    return
                self.add_message('3rd-party-module-not-gated', node=node, args=modname)


def register(linter):
    '''required method to auto register this checker '''
    linter.register_checker(ThirdPartyImportsChecker(linter))