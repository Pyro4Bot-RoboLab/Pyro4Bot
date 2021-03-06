#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ____________developed by paco andres____________________
# _________collaboration with cristian vazquez____________
"""
This library inspect packages and get a module where it defining a classes
his goal is import just classes for  pyro4bot.
"""

import sys
import os
import inspect
import pkgutil
import importlib


def explore_package(module_name):
    """
    Get a list of modules and submodules for a given package
    this function use a recursive algorithm.
    """
    modules = []
    loader = pkgutil.get_loader(module_name)
    loader.filename = loader.path.replace('/__init__.py', '')
    for a, sub_module_name, b in pkgutil.walk_packages([loader.filename]):
        qname = module_name + "." + sub_module_name
        modules.append(qname)
        if b:
            modules.extend(explore_package(qname))
    return modules


def get_classes(m):
    """
    Return a list of classes for a given module
    Warning: if module has non installed package return a empty list
    """
    list_class = []
    error_class = None
    try:
        mod = importlib.import_module(m)
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            list_class.append(name)
    except Exception as e:
        error_class = e
    return list_class, error_class


def get_packages_not_found(m):
    """
    Return a set of packages for a given module
    Warning: if module has non installed any package return a empty list
    """
    list_packages = None
    try:
        mod = importlib.import_module(m)
    except Exception as e:
        return "Module " + m + ": " + str(e)

    return None


def get_modules(pkgs):
    """
    Return all modules and submodules for given packages (pkgs).
    """
    if type(pkgs) not in (list, tuple):
        pkgs = (pkgs,)
    return [x for pk in pkgs for x in explore_package(pk)]


def module_class(cls, modules):
    """
    Find a module or modules for a cls class
    if has more than one module return first found
    """
    modules = [m for m in modules if cls in get_classes(m)]
    return modules[0].lstrip(".node") if len(modules) > 0 else None


def get_all_classes(modules):
    clases = {}
    errors = {}
    for m in modules:
        cls, error = get_classes(m)
        if error is not None:
            if m not in errors:
                errors[m] = []
            errors[m] = error
        for cl in cls:
            if cl not in clases:
                clases[cl] = []
            clases[cl].append(m.lstrip(".node"))
    return clases, errors


def import_module(module):
    """ Import specified module """
    importlib.import_module(module)


def module_packages_not_found(modules):
    """
    Returns all modules imported in modules that is no found
    """
    # return [m for m in modules if pkg in get_packages_not_found(m)]
    x = set()
    for m in modules:
        x.update(get_packages_not_found(m))
    return x


def not_found_modules(modules_error):
    """" Returns the modules what were not found """
    imports = [x[1].message.split("No module named ")[1] for x
               in modules_error.items() if type(x[1]) is ImportError]

    return list(set(imports))


def show_warnings(modules_errors):
    """ It prints the errors (warning) about the modules """
    if modules_errors:
        for k, v in modules_errors.items():
            print("warning: error in {} --> {}".format(k, v))


def show_module_resume(pkg, cls, errors):
    """ It prints a resume about the inspection of the different modules of the robot """
    print("INSPECTING MODULES {} ".format(pkg))
    for k, v in cls.items():
        print("   Class {} in Module {}".format(k, v))
    for k, v in errors.items():
        print("   ERROR {} in {}".format(v, k))
    print("____________________________")
    print("")


def inspecting_modules(*dirs, show=True):
    """ It runs the different methods to inspect the modules of the robot, to import them and show the related info """
    if type(dirs) not in (list, tuple):
        dirs = (dirs,)
    _modules = []
    _classes = {}
    _modules_errors = {}
    for pk in dirs:
        _module = get_modules(pk)
        _class, _module_errors = get_all_classes(_module)
        if show:
            show_module_resume(pk, _class, _module_errors)
        _modules.extend(_module)
        _classes.update(_class)
        _modules_errors.update(_module_errors)
    return _classes, _modules_errors


# _modules is a list of all components and services in pyro4bot
_modules = []
_classes = {}
_modules_errors = {}

# it is a list of all modules in system pyro4bot
_modules_libs = []
_classes_libs = {}
_modules_libs_errors = {}

if __name__ == "__main__":
    pass
