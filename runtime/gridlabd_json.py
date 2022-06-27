"""GridLAB-D JSON API

Options:

- debug (boolean): control debug output
- warning (boolean): control warning output
- quiet (boolean): control error output
- verbose (boolean): control verbose output
- exit_on_error ()

"""

import os
import sys
import json
import subprocess
import random

APPNAME = os.path.splitext(os.path.basename(sys.argv[0]))[0]
OPTIONS = {
    'debug' : False,
    'warning' : True,
    'quiet' : False,
    'verbose' : False,
    'exit_on_error' : False,
}
APPLICATION = "gridlabd"
VERSION = None
NEWMODEL = None

def enable(option):
    """Enable module option"""
    set_option(option,True)

def disable(option):
    """Disable module option"""
    set_option(option,False)

def set_option(option,value):
    """Set module option"""
    old_value = get_option(option)
    if type(old_value) != type(value):
        raise GldException(f"option '{option}' type mismatch")
    OPTIONS[option] = value
    return old_value

def get_option(option):
    """Get module option"""
    if option not in OPTIONS.keys():
        raise GldException(f"option '{option}' is invalid")
    return OPTIONS[option]

def debug(msg):
    """Output debug message"""
    if OPTIONS['debug']:
        print(f"DEBUG [{APPNAME}]: {msg}",file=sys.stderr)

def warning(msg):
    """Output warning message"""
    if OPTIONS['warning']:
        print(f"WARNING [{APPNAME}]: {msg}",file=sys.stderr)

def verbose(msg):
    """Output warning message"""
    if OPTIONS['verbose']:
        print(f"VERBOSE [{APPNAME}]: {msg}",file=sys.stderr)

def error(msg,code=None):
    """Output error message"""
    if OPTIONS['debug']:
        if type(code) is int:
            msg += f" (code {code})"
        raise GldException(msg)
    if not OPTIONS['quiet']:
        print(f"ERROR [{APPNAME}]: {msg}",file=sys.stderr)
    if type(code) is int and OPTIONS['exit_on_error']:
        exit(code)

def temporary_name(extension=""):
    """Get a temporary filename"""
    TMP = os.getenv("TMP")
    if not TMP:
        TMP = "/tmp"
    TMP += "/gridlabd_json"
    os.makedirs(TMP,exist_ok=True)
    return TMP+"/"+hex(random.randrange(1,2**64-1))+extension

def cleanup_tempfile(tmpname):
    """Delete a temporary filename"""
    if os.path.exists(tmpname):
        os.remove(tmpname)

class GldException(Exception):
    """GridLAB-D JSON API Exception"""
    pass

class GldRunner:
    """GridLAB-D runner"""
    command = "gridlabd"
    silent = False

    def __init__(self,args=[]):
        """Run GridLAB-D"""
        tmpname = temporary_name(".json")
        if type(args) is str:
            args = args.split(" ")
        if type(args) is list:
            if not args or args[0] != self.command:
                args.insert(0,self.command)
        else:
            raise GldException("invalid argument type")
        args.extend(["-o",tmpname])
        verbose(f"Running '{' '.join(args)}'")
        self.result = subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if self.result.returncode and not self.silent:
            error(f"exit code {self.result.returncode}")
        if self.result.stdout.decode() and not self.silent:
            debug(self.result.stdout.decode())
        if self.result.stderr.decode() and not self.silent:
            error(self.result.stderr.decode())
        if self.result.returncode == 0:
            with open(tmpname,"r") as fh:
                self.model = json.load(fh)
                global APPLICATION
                assert(self.model["application"]==APPLICATION)
                global VERSION
                if VERSION:
                    assert(self.model["version"]==VERSION)
                else:
                    VERSION = self.model["version"]
                cleanup_tempfile(tmpname)
        else:
            raise GldException(f"gridlabd run {args} failed (code {self.result.returncode}): {self.result.stderr.decode()}")
        debug(f"model = {self.model}")

    def get_exitcode(self):
        """Get exit code"""
        return self.result.returncode

    def get_model(self):
        """Get model data"""
        return self.model

    def get_output(self):
        """Get output"""
        return self.result.stdout.decode().strip().split("\n|\r\n")

    def get_errors(self):
        """Get errors"""
        return self.result.stderr.decode().strip().split("\n|\r\n")

class GldModule:
    """GridLAB-D Module Data"""
    def __init__(self,modules,name):
        self.name = name
        self.data = modules[name]
    def get_name(self):
        return self.name
    def get_version(self):
        return ".".join([self.data["major"],self.data["minor"]])

class GldModules:
    """GridLAB-D Module List"""
    def __init__(self,model):
        self.data = model.data["modules"]
    def get_names(self):
        return list(self.data.keys())
    def __getitem__(self,name):
        return GldModule(self.data,name)
    def load(self,name,model=None):
        """Load a module, optionally into a model"""
        result = GldRunner(["--modhelp",name])
        if not name in result.model["modules"].keys():
            error(f"module '{name}' load failed")
        if model:
            model["modules"].update(result.model["modules"])
            model["classes"].update(result.model["classes"])
            return model
        else:
            return result.model

class GldProperties:
    def __init__(self,properties):
        self.data = properties

class GldProperty:
    def __init__(self,data):
        self.data = data

class GldClass:
    def __init__(self,classes,name):
        self.name = name
        self.data = classes[name]
    def get_name(self):
        return self.name
    def __getitem__(self,item):
        value = self.data[item]
        if type(value) is str:
            return value
        else:
            return GldProperty(value)
    def get_properties(self):
        return GldProperties(self.data)

class GldClasses:
    def __init__(self,model,module=None):
        self.data = model.data["classes"]
    def get_names(self):
        return list(self.data.keys())
    def __getitem__(self,name):
        return GldClass(self.data,name)
    def define(self,name,properties):
        pass

class GldModel:
    """GridLAB-D Model Data"""
    def __init__(self,**kwargs):
        """Create GridLAB-D model"""
        global NEWMODEL
        if not NEWMODEL:
            NEWMODEL = GldRunner().get_model()
        self.data = NEWMODEL

    def load(self,**kwargs):
        """Load GridLAB-D model"""
        with open(kwargs['filename'],'r') as fh:
            self.data = json.load(fh)

    def save(self,**kwargs):
        """Save GridLAB-D model"""
        with open(kwargs['filename'],'w') as fh:
            json.dump(self.data,fh)

    def get_application(self):
        return self.data["application"]

    def get_version(self):
        return self.data["version"].split(".")

    def get_modules(self):
        return GldModules(self)

    def get_module(self,name):
        return GldModules(self)[name]

    def get_classes(self,module=None):
        if module:
            result = {}
            for key,data in self.data["classes"].items():
                if data["module"] == module:
                    result[key] = data
            return result
        else:
            return self.data["classes"]

    def get_class(self,name,module=None):
        return GldClass(self.get_classes(module),name)

    def get_objects(self):
        return self.data["objects"]

    def get_types(self):
        return self.data["types"]

    def get_header(self):
        return self.data["header"]

    def get_globals(self):
        return self.data["globals"]

    def get_schedules(self):
        return self.data["schedules"]

    def get_filters(self):
        if "filters" in self.data.keys():
            return self.data["filters"]
        else:
            return {}

    def add_module(self,name):
        self.get_modules().load(name,self.data)

if __name__ == "__main__":

    import unittest

    class TestModule(unittest.TestCase):

        def test1_runner(self):
            model = GldModel()
            result = GldRunner("--version=number")
            self.assertEqual(result.get_output()[0].split("."),model.get_version())

        def test2_new_model(self):
            model = GldModel()
            self.assertEqual(model.get_application(),"gridlabd")
            self.assertEqual(model.get_modules().get_names(),[])
            self.assertEqual(model.get_classes(),{})
            self.assertEqual(model.get_objects(),{})

        def test3_load_module_bad(self):
            GldRunner.silent = True
            model = GldModel()
            try:
                model.add_module("non_existent")
                self.assertFalse("non_existent module load succeeded unexpectedly")
            except GldException as err:
                pass # failure is expected
            except:
                self.assertFalse("non_existent module load failed in an unexpected way")

        def test3_load_module(self):
            GldRunner.silent = True
            model = GldModel()
            model.add_module("powerflow")
            module = model.get_module("powerflow")
            self.assertTrue(VERSION.startswith(module.get_version()))
            nodeclass = model.get_class("node","powerflow")
            self.assertTrue(nodeclass["parent"]=="powerflow_object")

    unittest.main()
