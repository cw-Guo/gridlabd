"""GridLAB-D Model Editor
"""

import sys, os
import json
import pandas

# 
# FILE READ
#
def read(filename,filetype="json",*args,**kwargs):

    if filetype == "json":

        if filename.isatty():
            print("JSON",file=sys.stderr,flush=True,end='> ')
        return read_json(filename,*args,**kwargs)

    elif filetype == "csv":

        if filename.isatty():
            print("CSV",file=sys.stderr,flush=True,end='> ')
        return read_csv(filename,*args,**kwargs)

    else:
        raise ValueError(f"filetype '{filetype}' in invalid")

def read_csv(file,*args,**kwargs):
    return pandas.read_csv(file,*args,**kwargs)

def read_json(file,*args,**kwargs):
	return json.load(file,*args,**kwargs)

#
# FILE WRITE
#

def write(data,filename,filetype="json",*args,**kwargs):

    if filetype == "json":

        DATA = write_json(data,filename,*args,**kwargs)

    elif filetype == "csv":

        DATA = write_csv(data,filename,*args,**kwargs)

    else:
        raise ValueError(f"filetype '{filetype}' in invalid")

def write_csv(data,file,*args,**kwargs):
	data.to_csv(file,*args,**kwargs)

def write_json(data,file,*args,**kwargs):
	json.dump(data,file,*args,**kwargs)

#
# COMMANDS
#
VALID_COMMANDS = ["create"]
def command(*args,**kwargs):
	"""Run a model edit command

	ARGUMENTS

	- COMMAND
	- SUBCOMMAND
	- ARGUMENTS

	"""
	if len(args) < 3:

		raise ValueError("missing command arguments")

	if not "data" in kwargs.keys():

		raise ValueError("missing data")

	if not args[0] in VALID_COMMANDS:
		raise Exception(f"command '{args[0]}' in not valid")

	fname = f"{args[0]}_{args[1]}"
	fargs = args[2:]
	data = kwargs["data"]
	if fname in globals().keys() and type(globals()[fname]).__name__ == 'function':

		return globals()[fname](fargs,data=data)

	else:

		raise Exception(f"command({args},data={data}): {fname} is not a valid function name")

def create_object(args,data):
	"""Create object in model

	ARGUMENTS

	- CLASS
	- NAME
	- PROPERTIES ...
	- data=DATA

	RETURNS

	- DATA modified

	"""
	check_model(data)

	oclass = args[0]
	classes = get_classes(data)
	if oclass not in classes.keys():
		raise Exception(f"class '{oclass}' is not defined")
	
	oname = args[1]
	objects = get_objects(data)
	if oname in objects.keys():
		raise Exception(f"object '{oname}' already exists")

	obj = {"class":oclass,"id":len(objects.keys())}
	for prop in args[2:]:
		spec = prop.split("=")
		if len(spec) < 2:
			raise ValueError(f"property '{prop}' missing value(s)")
		key = spec[0]
		if len(spec) == 2:
			value = spec[1]
		else:
			value = '='.join(spec[1:])
		obj[key] = value

	missing = [key for key in get_required_keys(classes,oclass) if key not in obj.keys()]
	if missing:
		raise Exception(f"missing required properties: {', '.join(missing)}")

	objects[oname] = obj
	
	return data

#
# UTILITIES
#
def get_classes(data):
	"""Get classes in model"""
	if "classes" not in data.keys():
		raise ValueError("missing class data")
	return data["classes"]

def get_objects(data):
	"""Get objects in model"""
	if "objects" not in data.keys():
		raise ValueError("missing object data")
	return data["objects"]

def check_model(data,exception=None):
	"""Check whether model is valid"""
	if "application" not in data.keys():
		if exception:
			raise ValueError("not a gridlabd model") from exception
		return False
	return True

def get_required_keys(classes,oclass):
	required = []
	classdata = classes[oclass]
	for key,info in classdata.items():
		if type(info) is dict \
				and "flags" in info.keys() \
				and "REQUIRED" in set(info["flags"].split("|")):
			required.append(key)
	if "parent" in classdata.keys():
		required.extend(get_required_keys(classes,classdata["parent"]))
	return required

