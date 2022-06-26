"""GridLAB-D JSON API

Options:

- DEBUG (boolean): enable debug output

"""

import os
import sys
import json
import subprocess
import random

OPTIONS = {
    'debug' : False
}

def enable(option):
    """Enable module option"""
    if option not in OPTIONS.keys():
        raise GldException(f"option '{options}' is invalid")
    OPTIONS[option] = True

def disable(option):
    """Disable module option"""
    if option not in OPTIONS.keys():
        raise GldException(f"option '{options}' is invalid")
    OPTIONS[option] = False

def debug(msg):
    if OPTIONS['debug']:
        print(f"DEBUG [gridlabd_json]: {msg}",file=sys.stderr)

def temporary_name(extension=""):
    TMP = os.getenv("TMP")
    if not TMP:
        TMP = "/tmp"
    TMP += "/gridlabd_json"
    os.makedirs(TMP,exist_ok=True)
    return TMP+"/"+hex(random.randrange(1,2**64-1))+extension

def cleanup_tempfile(tmpname):
    os.remove(tmpname)

class GldException(Exception):
    """GridLAB-D JSON API Exception"""
    pass

class GldRunner:

    def __init__(self,args=[]):
        tmpname = temporary_name(".json")
        args.insert(0,"gridlabd")
        args.extend(["-o",tmpname])
        debug(f"Running {args}...")
        self.result = subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if self.result.returncode == 0:
            with open(tmpname,"r") as fh:
                self.model = json.load(fh)
                cleanup_tempfile(tmpname)
        else:
            raise GldException(f"gridlabd run {args} failed (code {self.result.returncode}): {self.result.stderr}")
        debug(f"model = {self.model}")

class GldModel:

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

if __name__ == "__main__":

    import unittest

    class TestGridlabdModel(unittest.TestCase):

        def test_new_model(self):
            model = GldModel()
            self.assertEqual(model.get_application(),"gridlabd")

    unittest.main()