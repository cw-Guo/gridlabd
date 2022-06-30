"""GridLAB-D JSON Model API

General API conventions/guidlines:

- The global CONFIG controls the behavior of the module.  This global is loaded
  from the file gridlabd_json.conf, which is also located in the runtime folder.
  If the file is absent or damaged, it is (re)created from the default values 
  specified in the module source code. Options can be enabled and disabled using
  the enable() and disable() methods.

- Most methods accept 'no_exception=True' to disable raising exception. In
  such cases, the return values is either None or False according to whether
  the function is expected to return something when successful.  When the
  call fails, the class set _lasterror to the value of the exception
  raised.

- When the module is run as a script, it executes a self-test sequence using
  the unittest python model.  The output of the unit test can be saved to a 
  file by enabling the CONFIG['save_unittest'] option.  Profiling can also
  be performed by enabling the CONFIG['profile_unittest'] option. The profile
  can be saved as well by enabling the CONFIG['save_profile'] option.

Example:

>>> import gridlabd_json as gld
>>> m = gld.GldModel()
>>> m.save("new.json")
>>> m.add_module("powerflow")

"""

__author__ = "David P. Chassin"
__copyright__ = "Copyright (C) 2022, Regents of the Leland Stanford Junior University"
__license__ = "BSD-3"
__version__ = "0.0"

import os
import sys
import json
import subprocess
import random
import re
from copy import deepcopy
import shutil

APPNAME = os.path.splitext(os.path.basename(sys.argv[0]))[0]
CONFIG = {
    'debug' : False,
    'exit_on_error' : False,
    'profile_unittest' : False,
    'quiet' : False,
    'save_unittest' : False,
    'save_profile' : False,
    'silent_runner' : True,
    'verbose' : False,
    'warning' : True,
}
CONFIGFILE = os.path.splitext(sys.argv[0])[0]+".conf"
UNITTESTFILE = "gridlabd_json.txt"
APPLICATION = "gridlabd"
VERSION = None
NEWMODEL = None

#
# CONFIG options
#

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
    CONFIG[option] = value
    return old_value

def get_option(option):
    """Get configuration option"""
    if option not in CONFIG.keys():
        raise GldException(f"option '{option}' is invalid")
    return CONFIG[option]

def save_options(file=CONFIGFILE):
    """Save configuration options"""
    with open(CONFIGFILE,"w") as fh:
        json.dump(CONFIG,fh,indent=4)

def load_options(file=CONFIGFILE):
    """Load configuration options"""
    with open(CONFIGFILE,"r") as fh:
        config = json.load(fh)
        CONFIG.update(config)

if os.path.exists(CONFIGFILE):
    try:
        load_options()
    except:
        print(f"WARNING [{APPNAME}]: defective '{CONFIGFILE}' fixed using default values",file=sys.stderr)
        os.remove(CONFIGFILE)
if not os.path.exists(CONFIGFILE):
    save_options()

#
# Output
#

def debug(msg):
    """Output debug message"""
    if CONFIG['debug']:
        print(f"DEBUG [{APPNAME}]: {msg}",file=sys.stderr)

def warning(msg):
    """Output warning message"""
    if CONFIG['warning']:
        print(f"WARNING [{APPNAME}]: {msg}",file=sys.stderr)

def verbose(msg):
    """Output warning message"""
    if CONFIG['verbose']:
        print(f"VERBOSE [{APPNAME}]: {msg}",file=sys.stderr)

def error(msg,code=None):
    """Output error message"""
    if CONFIG['debug']:
        if type(code) is int:
            msg += f" (code {code})"
        raise GldException(msg)
    if not CONFIG['quiet']:
        print(f"ERROR [{APPNAME}]: {msg}",file=sys.stderr)
    if type(code) is int and CONFIG['exit_on_error']:
        exit(code)

#
# Temporary file/folder management
#

class GldTemporaryFile:

    def __init__(self,extension="",root=None):
        """Get a temporary filename

        Constructor:

            extension   specify the file extension to use (default "")
                        use "/" to create a temporary folder
            root        specify the root folder to use

        Destructor:

            The file or folder is deleted when the object is deleted

        Members:

            name
        """
        if root == None:
            root = os.getenv("TMP")
            if not root:
                root = "/tmp"
            root += "/gridlabd_json"
        os.makedirs(os.path.dirname(root),exist_ok=True)
        self.name = root+"/"+hex(random.randrange(1,2**128-1))[2:]+extension

    def __del__(self):
        """Delete a temporary filename"""
        if hasattr(self,"name") and os.path.exists(self.name):
            if self.name.endswith("/"):
                shutil.rmtree(self.name)
            else:
                os.remove(self.name)

    def open(self,mode):
        """Open the temporary file"""
        return open(self.name,mode)

#
# Exception class
#

class GldException(Exception):
    """GridLAB-D JSON API Exception"""
    pass

#
# GridLAB-D runner class
#

class GldRunner:
    """GridLAB-D runner"""
    command = "gridlabd"
    options = []
    silent = CONFIG['silent_runner']

    def __init__(self,args=[]):
        """Run GridLAB-D"""
        tmpdir = GldTemporaryFile("/")
        tmpfile = GldTemporaryFile(".json",tmpdir.name)
        if type(args) is str:
            args = args.split(" ")
        if type(args) is list:
            if not args or args[0] != self.command:
                args.insert(0,self.command)
                for option in self.options:
                    args.insert(1,option)
        else:
            raise GldException("invalid argument type")
        args.extend(["-o",tmpfile.name])
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
            with tmpfile.open("r") as fh:
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

#
# GridLAB-D module class
#

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

# 
# GridLAB-D property class
#

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
        self._lasterror = None

    def check_value(self,value,model,no_exception=False):
        try:
            # validate object references
            if model and pspec.type == "object" \
                    and not value in model.get_objects().keys():
                raise GldException(f"property '{self.name}' refers to undefined object '{value}'")
            # TODO validate other object types
            return True
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return False

#
# GridLAB-D class class
#

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
        self._lasterror = None

    def find_properties(self,pattern=".*"):
        result = []
        for key in self._elements:
            if re.match(pattern,key):
                value = getattr(self,key)
                if type(value) is dict:
                    result.append(key)
        return result

#
# GridLAB-D object class
#

class GldObject:
    """Object accessor"""
    def __init__(self,name,data):
        self.name = name
        for key,value in data.items():
            setattr(self,key,value)
        self._elements = list(data.keys())
        self._lasterror = None

#
# GridLAB-D schedule class
#

class GldSchedule:
    """TODO"""
    def __int__(self,name,data):
        self.name = name
        for key,value in data.items():
            setattr(self,key,value)
        self._elements = list(data.keys())
        self._lasterror = None

#
# GridLAB-D filter class
#

class GldFilter:
    """TODO"""
    def __init(self,name,data):
        self.name = name
        for key,value in data.items():
            setattr(self,key,value)
        self._elements = list(data.keys())
        self._lasterror = None
        
#
# GridLAB-D model class
#

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
        self._lasterror = None
            

    def get_elements(self):
        """Get list of model data elements"""
        return self.data.keys()

    def __getitem__(self,item):
        return self.data[item]

    def load(self,filename,no_exception=False):
        """Load GridLAB-D model"""
        try:
            with open(filename,'r') as fh:
                self.data = json.load(fh)
            return self.data
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None            

    def save(self,filename,no_exception=False):
        """Save GridLAB-D model"""
        try:
            with open(filename,'w') as fh:
                json.dump(self.data,fh,indent=4)
            return True
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return False

    def get_application(self,no_exception=False):
        """Get application name"""
        try:
            return str(self.data["application"])
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    def get_version(self,as_str=False,no_exception=False):
        """Get model version"""
        try:
            version = self.data["version"]
            if as_str:
                return str(version)
            else:
                return version.split(".")
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None


    def run(self,options=[],no_exception=False):
        """Run the simulation"""
        try:
            tmpdir = GldTemporaryFile("/")
            tmpfile = GldTemporaryFile(".json",tmpdir.name)
            self.save(tmpfile.name)
            arglist = [tmpfile.name]
            arglist.extend(options)
            return GldRunner(arglist).model
        except:
            if notno_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

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
        result = deepcopy(self.data["modules"])
        if pattern:
            for name in list(result.keys()):
                if not re.match(pattern,name):
                    del result[name]
        return result

    def get_module(self,name,no_exception=False):
        """Get a loaded GridLAB-D module"""
        try:
            return GldModule(name,self.data["modules"][name])
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    def add_module(self,name,no_exception=False):
        """Add a GridLAB-D module"""
        try:
            if not name in self.get_modules():
                result = GldRunner(["--modhelp",name])
                if not name in result.get_model().get_modules().keys():
                    error(f"module '{name}' not found")
                self.data["modules"].update(result.model["modules"])
                self.data["classes"].update(result.model["classes"])
            return GldModule(name,self.data["modules"][name])
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    def delete_module(self,name,found='fail',no_exception=False):
        """Delete a GridLAB-D module

            name             module name to delete

            found='delete'   delete element found using module
            found='fail'     raise exception if element found using module (default)
            found='ignore'   ignore elements found using module
        """
        try:
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
            return True
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return False
    
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
            result = deepcopy(self.data["classes"])
        if pattern:
            for name in list(result.keys()):
                if not re.match(pattern,name):
                    del result[name]
        return result

    def get_class(self,name,no_exception=False):
        """Get a class"""
        try:
            return GldClass(name,self.data["classes"][name])
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    def add_class(self,name,data,no_exception=False):
        """Add a class"""
        try:
            self.check_class(name,data)
            if name in self.data["classes"].keys():
                raise GldException(f"class '{name}' is already defined")
            self.data["classes"][name] = data
            return GldClass(name,self.data["classes"][name])
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    def check_class(self,name,data,no_exception=False):
        try:
            if "module" in data.keys() and not data["module"] in self.data["modules"].keys():
                raise GldException(f"class '{name}' refers to non-existent module '{data['module']}'")
            for key,value in data.items():
                if "type" not in value.keys():
                    raise GldException(f"class '{name}' is missing a type specification")
                if not value["type"] in self.data["types"].keys():
                    raise GldException(f"class '{name}' uses an invalid type '{value['type']}'")
                for spec in value.keys():
                    if not spec in ["type","access","keywords","flags","description"]:
                        raise GldException(f"class '{name}' includes an invalid specification for '{spec}'")
            return True
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return False

    def isa_class(self,name,kindof,no_exception=False):
        """Check whether a class is a kindof another class"""
        try:
            oclass = self.data["classes"][name]
            if not "parent" in oclass.keys():
                return name == kindof
            return self.isa_class(oclass["parent"],kindof)
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    def delete_class(self,name,found='fail',no_exception=False):
        """Delete a class

            name             class name to delete

            found='delete'   delete element found using class
            found='fail'     raise exception if element found using class (default)
            found='ignore'   ignore elements found using class
        """
        try:
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
            return True
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return False

    #
    # Types
    #

    def get_types(self,pattern=None):
        """Get GridLAB-D data type specifications"""
        result = deepcopy(self.data["types"])
        if pattern:
            for name in list(result.keys()):
                if not re.match(pattern,name):
                    del result[name]
        return result

    def get_type(self,name,no_exception=False):
        """Get a GridLAB-D data type specification"""
        try:
            return GldType(name,self.data["types"][name])
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    #
    # Headers
    #

    def get_headers(self,pattern=None):
        """Get all GridLAB-D object header data specifications"""
        result = deepcopy(self.data["header"])
        if pattern:
            for name in list(result.keys()):
                if not re.match(pattern,name):
                    del result[name]
        return result

    def get_header(self,name,no_exception=False):
        """Get a GridLAB-D object header data specification"""
        try:
            return GldHeader(name,self.data["header"][name])
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    #
    # Globals
    #

    def get_globals(self,pattern=None):
        """Get all global variables"""
        result = deepcopy(self.data["globals"])
        if pattern:
            for name in list(result.keys()):
                if not re.match(pattern,name):
                    del result[name]
        return result

    def get_global(self,name,no_exception=False):
        """Get a global variable"""
        try:
            return GldGlobal(name,self.data["globals"][name])
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    def set_global(self,name,data,no_exception=False):
        """Set a global variable"""
        try:
            self.check_global(name,data)
            self.data["globals"][name] = data
            return True
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return False

    def add_global(self,name,data,type="char1024",access="PUBLIC",no_exception=False):
        """Add a global variable"""
        try:
            if name in self.data["globals"].keys():
                raise GldException(f"global '{name}' is already defined")
            self.check_global(name,data)
            self.data["globals"][name] = data
            return self.data["globals"][name]
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    def check_global(self,name,data,no_exception=False):
        """Validate a global"""
        try:
            for item in data.keys():
                if not item in ["type","keywords","access","value"]:
                    raise GldException(f"global '{name}' data item '{item}' is invalid")
            if not data["type"] in self.data["types"].keys():
                raise GldException(f"global '{name}' type '{data['type']}' is invalid")
            return True
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return False

    def delete_global(self,name,no_exception=False):
        """Delete a global variables"""
        try:
            del self.data["globals"]
            return True
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return False

    #
    # Schedules
    #

    def get_schedules(self,pattern=None):
        """Get all GridLAB-D schedules"""
        result = deepcopy(self.data["schedules"])
        if pattern:
            for name in list(result.keys()):
                if not re.match(pattern,name):
                    del result[name]
        return result

    def get_schedule(self,name,no_exception=False):
        """Get a schedule"""
        try:
            return GldSchedule(name,self.data["schedules"][name])
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    def add_schedule(self,name,data,no_exception=False):
        """Add a schedule"""
        try:
            self.check_schedule(name,data)
            self.data["schedules"][name] = data
            return self.data["schedule"][name]
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None        

    def check_schedule(self,name,data,no_exception=False):
        try:
            if not type(data) is str:
                raise GldException("schedule '{name}' data is not a string")
            return True
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return False

    def delete_schedule(self,name,found='fail',no_exception=False):
        """Delete a schedule"""
        try:
            if not name in self.data["schedules"].keys():
                raise GldException(f"schedules '{name}' not found")
            root = f"{name}("
            for obj,data in self.data["objects"].items():
                for prop,value in data.items():
                    if value.beginswith(root):
                        if found == 'fail':
                            raise GldException(f"schedules '{name}' is in use by object '{obj}'")
                        elif found == 'delete':
                            delete_object(obj)
                        elif found != 'ignore':
                            raise Exception(f"option found='{found}' is invalid")
            del self.data["schedules"][name]
            return True
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return False

    #
    # Filters
    #

    def get_filters(self,pattern=None):
        """Get all GridLAB-D filters"""
        if "filters" in self.data.keys():
            result = deepcopy(self.data["filters"])
        else:
            result = {}
        if pattern:
            for name in list(result.keys()):
                if not re.match(pattern,name):
                    del result[name]
        return result

    def get_filter(self,name,no_exception=False):
        try:
            return GldFilter(name,self.data["filters"][name])
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    def add_filter(self,name,data,no_exception=False):
        try:
            if "filters" in self.data.keys() and name in self.data["filters"]:
                raise GldException(f"filter '{name}' is already defined")
            self.check_filter(name,data)
            self.data["filters"][name] = data
            return self.data["filters"][name]
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    def check_filter(self,name,data,no_exception=False):
        try:
            for key in ["domain","timestep","numerator","denominator"]:
                if not key in data.keys():
                    raise GldException(f"filter '{name}' missing {key} specification")
            for key in data.keys():
                if key not in ["domain","timestep","timeskew","resolution","minimum","maximum","numerator","denominator"]:
                    raise GldException(f"filter '{name}' key '{key}' is not recognized")
            return True
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return False

    def delete_filter(self,name,found='fail',no_exception=False):
        try:
            if not "filters" in self.data.keys() or not name in self.data["filters"].keys():
                raise GldException(f"filter '{name}' not found")
            root = f"{name}("
            for obj,data in self.data["objects"].items():
                for prop,value in data.items():
                    if value.beginswith(root):
                        if found == 'fail':
                            raise GldException(f"filter '{name}' is in use by object '{obj}'")
                        elif found == 'delete':
                            delete_object(obj)
                        elif found != 'ignore':
                            raise Exception(f"option found='{found}' is invalid")
            del self.data["filters"][name]
            return True
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return False

    #
    # Objects
    #

    def get_objects(self,classes=None,pattern=None):
        if type(classes) is str:
            classes = [classes]
        if classes:
            result = {}
            for key,data in self.data["objects"].items():
                if data["class"] in classes:
                    result[key] = data
        else:
            result = deepcopy(self.data["objects"])
        if pattern:
            for name in list(result.keys()):
                if not re.match(pattern,name):
                    del result[name]
        return result

    def get_object(self,name,no_exception=False):
        try:
            return GldObject(name,self.data["objects"][name])
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    def add_object(self,name,data,no_check=False,no_exception=False):
        try:
            if name in self.get_objects().keys():
                raise GldException(f"object '{name}' exists already")
            if not no_check:
                self.check_object(name,data)
            self.data["objects"][name] = data
            return GldObject(name,self.data["objects"][name])
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    def delete_object(self,name,found='fail',no_exception=False):
        """Delete object

            name    object name
            found   dependent object disposition
                    'fail' - delete fails
                    'delete' - delete dependent object
                    'ignore' - ignore dependent object
        """
        try:
            if type(name) is list:
                ok = True
                for item in name:
                    if not delete_object(item,found,no_exception):
                        ok = False
                return ok
            data = self.data["objects"]["name"]
            for prop,spec in self.get_class(data["class"]).items():
                if self.get_property(prop,spec).type == "object" \
                        and data[prop] in self.get_objects().keys():
                    if found == 'fail':
                        raise GldException(f"object '{name}' refers to object '{data[prop]}'")
                    elif found == 'delete':
                        delete_object(data[prop])
                    elif found != 'ignore':
                        raise Exception(f"option '{fail}' is invalid'")
                del self.data["objects"][name]
            return True
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return False

    def check_object(self,name,data,no_exception=False):
        """Validate object specifications"""
        try:
            if "class" not in data.keys():
                raise GldException(f"object '{name}' does not specify a class")
            if not data["class"] in self.get_classes().keys():
                raise GldException(f"object '{name}' class '{data['class']}' undefined")
            oclass = self.get_class(data["class"])
            for prop,value in data.items():
                pspec = oclass.get_property(prop)
                pspec.check_value(value)
            return True
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return False

    def get_double(self,obj,prop,no_exception=False):
        """Return an object property value as a double"""
        try:
            data = self.data["objects"][obj]
            if prop in data.keys():
                value = data[prop]
            else:
                oclass = data["class"]
                if not prop in self.data["classes"][oclass].keys():
                    raise GldException(f"object '{obj}' property '{prop}' is invalid")
                value = self.data["classes"][oclass][prop]["default"]
            return float(value.split()[0])
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    def get_complex(self,no_exception=False):
        """Return an object property value as a double"""
        try:
            data = self.data["objects"][obj]
            if prop in data.keys():
                value = data[prop]
            else:
                oclass = data["class"]
                if not prop in self.data["classes"][oclass].keys():
                    raise GldException(f"object '{obj}' property '{prop}' is invalid")
                value = self.data["classes"][oclass][prop]["default"]
            return complex(value.split()[0])
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    def get_unit(self,no_exception=False):
        """Return an object property unit, if any"""
        try:
            oclass = self.data["objects"][obj]["class"]
            if not prop in self.data["classes"][oclass].keys():
                raise GldException(f"object '{obj}' property '{prop}' is invalid")
            return self.data["classes"][oclass][prop]["unit"]
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    def get_integer(self,no_exception=False):
        """Return an object property as an integer"""
        try:
            data = self.data["objects"][obj]
            if prop in data.keys():
                value = data[prop]
            else:
                oclass = data["class"]
                if not prop in self.data["classes"][oclass].keys():
                    raise GldException(f"object '{obj}' property '{prop}' is invalid")
                value = self.data["classes"][oclass][prop]["default"]
            return int(value)
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    def get_string(self,no_exception=False):
        """Return an object property as a string"""
        try:
            data = self.data["objects"][obj]
            if prop in data.keys():
                value = data[prop]
            else:
                oclass = data["class"]
                if not prop in self.data["classes"][oclass].keys():
                    raise GldException(f"object '{obj}' property '{prop}' is invalid")
                value = self.data["classes"][oclass][prop]["default"]
            return str(value)
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

    def get_object(self,no_exception=False):
        """Return an object property as object data"""
        try:
            value = self.data["objects"][obj][prop]
            return self.data["objects"][value]
        except:
            if not no_exception:
                raise
            self._lasterror = sys.exc_info()
        return None

#
# Only run when loaded as a script
#

if __name__ == "__main__":

    import unittest

    #
    # Runner
    #

    class TestRunner(unittest.TestCase):

        def test_gldrunner(self):
            result = GldRunner("--version=number")
            self.assertEqual(result.exitcode,0)

    #
    # Models
    #

    class TestModel(unittest.TestCase):

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

    class TestModule(unittest.TestCase):
    
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

        def test_gldmodel_modulepattern(self):
            model = GldModel()
            model.add_module("powerflow")
            model.add_module("residential")
            modules = model.get_modules("r")
            self.assertTrue("residential" in modules.keys())
            self.assertFalse("powerflow" in modules.keys())

    #
    # Classes
    #

    class TestClass(unittest.TestCase):
    
        def test_gldmodel_getclass(self):
            model = GldModel()
            model.add_module("powerflow")
            oclass = model.get_class("node")
            self.assertTrue("module" in oclass._elements)
            self.assertTrue(oclass.module=="powerflow")

        def test_gldmodel_getclass_pattern(self):
            model = GldModel()
            model.add_module("powerflow")
            classes = model.get_classes("powerflow","triplex_")
            self.assertTrue("triplex_meter" in classes.keys())
            self.assertFalse("node" in classes.keys())

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
    # Model run
    #

    class TestRun(unittest.TestCase):
    
        def test_gldmodel_run(self):
            model = GldModel()
            result = model.run()
            self.assertEqual(model,result)

    #
    # Unittest and profiler
    #

    if CONFIG['save_unittest']:
        sys.stdout = open(UNITTESTFILE,"w")
        if CONFIG['save_profile']:
            sys.stderr = sys.stdout
    elif CONFIG['save_profile']:
        sys.stdout = open(UNITTESTFILE,"w")
    if CONFIG['profile_unittest']:
        import cProfile
        runner = cProfile.run
    else:
        runner = eval
    runner('unittest.main()')
