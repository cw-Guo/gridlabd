"""GridLAB-D JSON API

Configuration options

- debug            control debug output
- exit_on_error    control whether errors cause exit
- quiet            control error output
- silent_running   silence output from GridLAB-D runner
- verbose          control verbose output
- warning          control warning output
"""

import os
import sys
import json
import subprocess
import random
import re
from copy import deepcopy
import shutil

APPNAME = os.path.splitext(os.path.basename(sys.argv[0]))[0]
OPTIONS = {
    'debug' : False,
    'warning' : True,
    'quiet' : False,
    'verbose' : False,
    'exit_on_error' : False,
    'silent_runner' : True
}
CONFIGFILE = os.path.splitext(sys.argv[0])[0]+".conf"
APPLICATION = "gridlabd"
VERSION = None
NEWMODEL = None

def enable(option):
    """Enable configuration option"""
    set_option(option,True)

def disable(option):
    """Disable configuration option"""
    set_option(option,False)

def set_option(option,value):
    """Set configuration option"""
    old_value = get_option(option)
    if type(old_value) != type(value):
        raise GldException(f"option '{option}' type mismatch")
    OPTIONS[option] = value
    return old_value

def get_option(option):
    """Get configuration option"""
    if option not in OPTIONS.keys():
        raise GldException(f"option '{option}' is invalid")
    return OPTIONS[option]

def save_options(file=CONFIGFILE):
    """Save configuration options"""
    with open(CONFIGFILE,"w") as fh:
        json.dump(OPTIONS,fh,indent=4)

def load_options(file=CONFIGFILE):
    """Load configuration options"""
    with open(CONFIGFILE,"r") as fh:
        config = json.load(fh)
        OPTIONS.update(config)

if os.path.exists(CONFIGFILE):
    try:
        load_options()
    except:
        print(f"WARNING [{APPNAME}]: defective '{CONFIGFILE}' fixed using default values",file=sys.stderr)
        os.remove(CONFIGFILE)
if not os.path.exists(CONFIGFILE):
    save_options()

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

class GldTemporaryFile:

    def __init__(self,extension="",root=None):
        """Get a temporary filename"""
        if root == None:
            root = os.getenv("TMP")
            if not root:
                root = "/tmp"
            root += "/gridlabd_json"
        os.makedirs(os.path.dirname(root),exist_ok=True)
        self.tmpname = root+"/"+hex(random.randrange(1,2**128-1))[2:]+extension

    def __del__(self):
        """Delete a temporary filename"""
        if hasattr(self,"tmpname") and os.path.exists(self.tmpname):
            if self.tmpname.endswith("/"):
                shutil.rmtree(self.tmpname)
            else:
                os.remove(self.tmpname)

    def __str__(self):
        return self.tmpname

    def __repr__(self):
        return self.tmpname

class GldException(Exception):
    """GridLAB-D JSON API Exception"""
    pass

class NotImplemented(Exception):
    pass

class GldRunner:
    """GridLAB-D runner"""
    command = "gridlabd"
    options = []
    silent = OPTIONS['silent_runner']

    def __init__(self,args=[]):
        """Run GridLAB-D"""
        tmpdir = GldTemporaryFile("/")
        tmpname = GldTemporaryFile(".json",str(tmpdir))
        if type(args) is str:
            args = args.split(" ")
        if type(args) is list:
            if not args or args[0] != self.command:
                args.insert(0,self.command)
                for option in self.options:
                    args.insert(1,option)
        else:
            raise GldException("invalid argument type")
        args.extend(["-o",str(tmpname)])
        verbose(f"Running '{' '.join(args)}'")
        self.result = subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if self.result.returncode and not self.silent:
            error(f"exit code {self.result.returncode}")
        self.exitcode = self.get_exitcode()
        if self.result.stdout.decode() and not self.silent:
            debug(self.result.stdout.decode())
        self.output = self.get_output()
        if self.result.stderr.decode() and not self.silent:
            error(self.result.stderr.decode())
        self.errors = self.get_errors()
        if self.result.returncode == 0:
            with open(str(tmpname),"r") as fh:
                self.data = json.load(fh)
                global APPLICATION
                assert(self.data["application"]==APPLICATION)
                global VERSION
                if VERSION:
                    assert(self.data["version"]==VERSION)
                else:
                    VERSION = self.data["version"]
                self.model = self.get_model()
        else:
            raise GldException(f"gridlabd run {args} failed (code {self.result.returncode}): {self.result.stderr.decode()}")
        debug(f"data = {self.data}")

    def get_exitcode(self):
        """Get exit code"""
        return self.result.returncode

    def get_model(self):
        """Get model data"""
        return GldModel(self.data)

    def get_output(self,split="\n|\r\n",strip=True):
        """Get output"""
        result = self.result.stdout.decode()
        if strip:
            result = result.strip()
        if split:
            result = result.split(split)
        return result

    def get_errors(self,split="\n|\r\n",strip=True):
        """Get errors"""
        result = self.result.stderr.decode()
        if strip:
            result = result.strip()
        if split:
            result = result.split(split)
        return result

class GldModule:
    """Module accessor

    Constructor:

        name        module name
        data        module data from model

    Members:

        name        name of module
        _elements   list of elements in module data
        _version    module version as a string
    """
    def __init__(self,name,data):
        """Create module accessor from module data"""
        self.name = name
        for key,value in data.items():
            setattr(self,key,value)
        self._elements = list(data.keys())
        self._version = '.'.join([self.major,self.minor])

class GldProperty:
    """Property accessor

    Constructor:

        name        property name
        data        property data

    Members:

        name        property name
        _elements   list of elements in property data
    """
    def __init__(self,name,data):
        """Create property accessor"""
        self.name = name
        for key,value in data.items():
            setattr(self,key,value)
        self._elements = list(data.keys())

class GldClass:
    """Class accessor

    Constructor:

        name        class name
        data        class data

    Members:

        name        class name
        _elements   list of elements in class data
    """
    def __init__(self,name,data):
        self.name = name
        for key,value in data.items():
            setattr(self,key,value)
        self._elements = list(data.keys())

    def find_properties(self,pattern=".*"):
        result = []
        for key in self._elements:
            if re.match(pattern,key):
                value = getattr(self,key)
                if type(value) is dict:
                    result.append(key)
        return result

class GldModel:
    """GridLAB-D Model Data"""

    def __init__(self,data=None):
        """Create GridLAB-D model"""
        self.data = data
        if self.data == None:
            global NEWMODEL
            if not NEWMODEL:
                NEWMODEL = GldRunner().get_model().data
            self.data = deepcopy(NEWMODEL)

    def get_elements(self):
        """Get list of model data elements"""
        return self.data.keys()

    def __getitem__(self,item):
        return self.data[item]

    def load(self,**kwargs):
        """Load GridLAB-D model"""
        with open(kwargs['filename'],'r') as fh:
            self.data = json.load(fh)

    def save(self,filename):
        """Save GridLAB-D model"""
        with open(filename,'w') as fh:
            json.dump(self.data,fh)

    def get_application(self):
        """Get application name"""
        return self.data["application"]

    def get_version(self,as_str=False):
        """Get model version"""
        version = self.data["version"]
        if as_str:
            return version
        else:
            return version.split(".")

    def run(self,options=[]):
        """Run the simulation"""
        tmpdir = GldTemporaryFile("/")
        tmpname = GldTemporaryFile(".json",str(tmpdir))
        self.save(str(tmpname))
        arglist = [str(tmpname)]
        arglist.extend(options)
        return GldRunner(arglist).model

    def __eq__(self,model):
        """Check if models are equal"""
        return self.get_objects() == model.get_objects()

    def __ne__(self,model):
        """Check if models are not equal"""
        return self.get_objects() != model.get_objects()

    #
    # Modules
    #

    def get_modules(self,pattern=None):
        """Get list of loaded GridLAB-D modules"""
        result = self.data["modules"]
        if pattern:
            raise NotImplemented("get_headers pattern")
        return result

    def get_module(self,name):
        """Get a loaded GridLAB-D module"""
        return GldModule(name,self.data["modules"][name])

    def add_module(self,name):
        """Add a GridLAB-D module"""
        if not name in self.get_modules():
            result = GldRunner(["--modhelp",name])
            if not name in result.get_model().get_modules().keys():
                error(f"module '{name}' not found")
            self.data["modules"].update(result.model["modules"])
            self.data["classes"].update(result.model["classes"])
        return self.data

    def delete_module(self,name,found='fail'):
        """Delete a GridLAB-D module

            name             module name to delete

            found='delete'   delete element found using module
            found='fail'     raise exception if element found using module (default)
            found='ignore'   ignore elements found using module
        """
        for key in list(self.get_classes().keys()):
            data = self.get_classes()[key]
            if data["module"] == name:
                if found == 'delete':
                    self.delete_class(key)
                elif found == 'fail':
                    raise GldException(f"module in use by class {key}")
                elif found != 'ignore':
                    raise GldException(f"found='{found}' is invalid")
        del self.data["modules"][name]

    #
    # Classes
    #

    def get_classes(self,module=None,pattern=None):
        """Get classes"""
        if module:
            result = {}
            for key,data in self.data["classes"].items():
                if data["module"] == module:
                    result[key] = data
        else:
            result = self.data["classes"]
        if pattern:
            raise NotImplemented("get_classes pattern")
        return result

    def get_class(self,name):
        """Get a class"""
        return GldClass(name,self.data["classes"][name])

    def add_class(self,name,data):
        """Add a class"""
        raise NotImplemented("add_class")

    def isa_class(self,name,kindof):
        """Check whether a class is a kindof another class"""
        oclass = self.data["classes"][name]
        if not "parent" in oclass.keys():
            return name == kindof
        return self.isa_class(oclass["parent"],kindof)

    def delete_class(self,name,found='fail'):
        """Delete a class

            name             class name to delete

            found='delete'   delete element found using class
            found='fail'     raise exception if element found using class (default)
            found='ignore'   ignore elements found using class
        """
        for key in list(self.get_objects()):
            data = self.get_objects()[key]
            if data["class"] == name:
                if found == 'delete':
                    self.delete_object(key)
                elif found == 'fail':
                    raise GldException(f"class in use by object {key}")
                elif found != 'ignore':
                    raise GldException(f"found='{found}' is invalid")
        del self.data["classes"][name]

    #
    # Types
    #

    def get_types(self,pattern=None):
        """Get GridLAB-D data type specifications"""
        result = self.data["types"]
        if pattern:
            raise NotImplemented("get_types pattern")
        return result

    def get_type(self,name):
        """Get a GridLAB-D data type specification"""
        return GldType(name,self.data["types"][name])

    #
    # Headers
    #

    def get_headers(self,pattern=None):
        """Get all GridLAB-D object header data specifications"""
        result = self.data["header"]
        if pattern:
            raise NotImplemented("get_headers pattern")
        return result

    def get_header(self,name):
        """Get a GridLAB-D object header data specification"""
        return GldHeader(name,self.data["header"][name])

    #
    # Globals
    #

    def get_globals(self,pattern=None):
        """Get all global variables"""
        result = self.data["globals"]
        if pattern:
            raise NotImplemented("get_globals pattern")
        return result

    def get_global(self,name):
        """Get a global variable"""
        return GldGlobal(name,self.data["globals"][name])

    def set_global(self,name,data):
        """Set a global variables"""
        raise NotImplemented("set_global")

    def delete_global(self,name):
        """Delete a global variables"""
        raise NotImplemented("delete_global")

    #
    # Schedules
    #

    def get_schedules(self,pattern=None):
        """Get all GridLAB-D schedules"""
        result = self.data["schedules"]
        if pattern:
            raise NotImplemented("get_schedules pattern")
        return result

    def get_schedule(self,name):
        """Get a schedule"""
        return GldSchedule(name,self.data["schedules"][name])

    def add_schedule(self,name,data):
        """Add a schedule"""
        raise NotImplemented("add_schedule")

    def delete_schedule(self,name,force=False,recurse=True):
        """Delete a schedule"""
        raise NotImplemented("delete_schedule")

    #
    # Filters
    #

    def get_filters(self,pattern=None):
        """Get all GridLAB-D filters"""
        if "filters" in self.data.keys():
            result = self.data["filters"]
        else:
            result = {}
        if pattern:
            raise NotImplemented("get_filters pattern")
        return result

    def get_filter(self,name):
        return GldFilter(name,self.data["filters"][name])

    def add_filter(self,name,data):
        raise NotImplemented("add_filter")

    def delete_filter(self,name,force=False,recurse=True):
        raise NotImplemented("delete_filter")

    #
    # Objects
    #

    def get_objects(self,classes=None,pattern=None):
        if type(classes) is str:
            classes = [classes]
        if classes:
            result = {}
            for key,data in self.data["objects"]:
                if data["class"] in classes:
                    result[key] = data
        else:
            result = self.data["objects"]
        if pattern:
            raise NotImplemented("get_objects pattern")
        return result

    def get_object(self,name):
        return GldObject(name,self.data["objects"][name])

    def add_object(self,name,data):
        raise NotImplemented("add_object")

    def delete_object(self,name,force=False,recurse=True):
        raise NotImplemented("delete_object")        

if __name__ == "__main__":

    import unittest

    class TestGridlabdJsonModule(unittest.TestCase):

        #
        # Runner
        #
        def test_gldrunner(self):
            result = GldRunner("--version=number")
            self.assertEqual(result.exitcode,0)

        #
        # Models
        #
        def test_gldmodel_version(self):
            result = GldRunner("--version=number")
            model = GldModel()
            self.assertEqual(result.get_output()[0],model.get_version(as_str=True))

        def test_gldmodel_new(self):
            model = GldModel()
            self.assertEqual(model.get_application(),"gridlabd")
            self.assertTrue(type(model.get_version()) is list)
            self.assertTrue(type(model.get_version(as_str=True)) is str)
            self.assertEqual(model.get_modules(),{})
            self.assertEqual(model.get_classes(),{})
            self.assertEqual(model.get_objects(),{})
            self.assertEqual(model.get_schedules(),{})
            self.assertEqual(model.get_filters(),{})
            self.assertTrue("id" in model.get_headers())
            self.assertTrue("version" in model.get_globals())

        #
        # Modules
        #
        def test_gldmodel_nomodule(self):
            model = GldModel()
            try:
                model.add_module("non_existent")
                self.assertFalse("non_existent module load succeeded unexpectedly")
            except GldException:
                pass # failure is expected
            except:
                e_type, e_value, e_trace = sys.exc_info()
                self.assertFalse(f"non_existent module load failed: {e_value} ({e_type.__name__})")

        def test_gldmodel_addmodule(self):
            model = GldModel()
            model.add_module("powerflow")
            self.assertTrue("powerflow" in model.get_modules())
            module = model.get_module("powerflow")
            self.assertTrue(VERSION.startswith(module._version))
            self.assertTrue("major" in module._elements)
            nodeclass = model.get_class("node")
            self.assertTrue(nodeclass.parent=="powerflow_object")

        def test_gldmodel_getmodule(self):
            model = GldModel()
            model.add_module("powerflow")
            module = model.get_module("powerflow")
            self.assertTrue("major" in module._elements)
            self.assertTrue(type(module.minor) is str)

        def test_gldmodel_delmodule_delete(self):
            model = GldModel()
            model.add_module("powerflow")
            self.assertTrue("powerflow" in model.get_modules())
            model.delete_module("powerflow",found='delete')
            self.assertFalse(model.get_modules())
            self.assertFalse(model.get_classes())

        def test_gldmodel_delmodule_ignore(self):
            model = GldModel()
            model.add_module("powerflow")
            self.assertTrue("powerflow" in model.get_modules())
            model.delete_module("powerflow",found='ignore')
            self.assertFalse(model.get_modules())
            self.assertTrue(model.get_classes())

        def test_gldmodel_delmodule_fail(self):
            model = GldModel()
            model.add_module("powerflow")
            self.assertTrue("powerflow" in model.get_modules())
            try:
                model.delete_module("powerflow",found='fail')
                self.assertFalse("delete_module did not fail as expected")
            except GldException:
                self.assertTrue(model.get_modules())
                self.assertTrue(model.get_classes())
            except:
                self.assertFalse("delete_module fail unexpectedly")

        #
        # Classes
        #
        def test_gldmodel_getclass(self):
            model = GldModel()
            model.add_module("powerflow")
            oclass = model.get_class("node")
            self.assertTrue("module" in oclass._elements)
            self.assertTrue(oclass.module=="powerflow")

        def test_gldmodel_isaclass(self):
            model = GldModel()
            model.add_module("powerflow")
            self.assertTrue(model.isa_class("node","powerflow_object"))
            self.assertFalse(model.isa_class("node","link"))


        def test_gldmodel_findproperties(self):
            model = GldModel()
            model.add_module("powerflow")
            oclass = model.get_class("node")
            properties = oclass.find_properties("voltage.*")
            self.assertGreater(len(properties),0)


        #
        # Run
        #
        def test_gldmodel_run(self):
            model = GldModel()
            result = model.run()
            self.assertEqual(model,result)

    unittest.main()
