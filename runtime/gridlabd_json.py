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
    if type(code) is int and not OPTIONS['exit_on_error']:
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
        if self.result.returncode:
            error(f"exit code {self.result.returncode}")
        if self.result.stdout.decode():
            debug(self.result.stdout.decode())
        if self.result.stderr.decode():
            error(self.result.stderr.decode())
        if self.result.returncode == 0:
            with open(tmpname,"r") as fh:
                self.model = json.load(fh)
                cleanup_tempfile(tmpname)
        else:
            raise GldException(f"gridlabd run {args} failed (code {self.result.returncode}): {self.result.stderr}")
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

class GldModel:
    """GridLAB-D Model Data"""
    def __init__(self,**kwargs):
        """Create GridLAB-D model"""
        self.data = GldRunner().model

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
        return self.data["version"]

    def get_modules(self):
        return self.data["modules"]

    def get_classes(self):
        return self.data["classes"]

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

if __name__ == "__main__":

    import unittest

    class TestModule(unittest.TestCase):

        def test_new_model(self):
            model = GldModel()
            self.assertEqual(model.get_application(),"gridlabd")
            self.assertEqual(model.get_modules(),{})
            self.assertEqual(model.get_classes(),{})
            self.assertEqual(model.get_objects(),{})

        def test_runner(self):
            model = GldModel()
            result = GldRunner("--version=number")
            self.assertEqual(result.get_output()[0],model.get_version())

    unittest.main()
