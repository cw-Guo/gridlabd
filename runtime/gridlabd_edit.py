"""GridLAB-D Model Editor
"""

import sys, os, subprocess
import json
import pandas

class GridlabdError(Exception):
	"""Raised when a GridLAB-D error occurs"""
	pass

class GridlabdModelError(GridlabdError):
	"""Raised when the model data is invalid"""
	pass

class GridlabdMissingValue(GridlabdError):
	"""Raised when a needed value is missing"""
	pass

class GridlabdInvalidValue(GridlabdError):
	"""Raise when a value is invalid"""
	pass

class GridlabdNoEntity(GridlabdError):
	"""Raised when the requested entity is not found in the model"""
	pass

class GridlabdInvalidCommand(GridlabdError):
	"""Raised when an invalid command is used"""
	pass

class GridlabdRuntimeError(GridlabdError):
	"""Raised when a runtime error occurs with GridLAB-D"""
	pass

class GridlabdEntityInUse(GridlabdError):
	"""Raised when an entity is busy or in used"""
	pass

class GridlabdEntityExists(GridlabdError):
	"""Raised when an entity already exists"""
	pass

# 
# FILE READ
#
def read(file,*args,**kwargs):
	return json.load(file,*args,**kwargs)

#
# FILE WRITE
#

def write(data,file,*args,**kwargs):
	json.dump(data,file,*args,**kwargs)

#
# COMMANDS
#
VALID_COMMANDS = {
	"create" : 0, # no additional arguments required
	"delete" : 1, # one argument required
	"insert" : -1, # one argument required with keywords
	"update" : -1, # one argument required with keywords
}
def command(data,*args,**kwargs):
	"""Run a model edit command

	ARGUMENTS

	- COMMAND
	- SUBCOMMAND
	- ARGUMENTS

	"""
	if len(args) == 1:

		raise GridlabdInvalidCommand("missing command")

	if not args[0] in VALID_COMMANDS.keys():

		raise GridlabdInvalidCommand(f"command '{args[0]}' in not valid")

	if len(args) <= abs(VALID_COMMANDS[args[0]]):

		raise GridlabdInvalidCommand(f"'{args[0]}': missing command {abs(VALID_COMMANDS[args[0]])-len(args)} argument(s)")

	elif VALID_COMMANDS[args[0]] != 0:

		fname = f"{args[0]}_{args[1]}"
		nargs = 2

	else:

		fname = args[0]
		nargs = 1

	if VALID_COMMANDS[args[0]] < 0 and kwargs == {}:

		raise GridlabdInvalidCommand(f"'{args[0]}' missing keyword argumenets")

	if fname in globals().keys() and type(globals()[fname]).__name__ == 'function':

		return globals()[fname](data,*args[nargs:],**kwargs)

	else:

		raise GridlabdInvalidCommand(f"'{args[0]}': '{fname}' is not a valid function name")

def create(data,*args,**kwargs):
	"""Create new model

	ARGUMENTS

		data (dict) - ignored

		*args (list) - [1] name of model (optional)

		**kwargs (dict) - gridlabd command options
	"""
	if len(args) == 0:

		name = "untitled.glm"

	else:

		name = args[0]
		if not args[0].endswith(".glm"):
			name += ".glm"

	with open(name,"w") as fh:
		fh.write("")

	command = ["gridlabd","-C",name,"-o",name.replace(".glm",".json")]
	for key,value in kwargs.items():
		if value == None:
			command.append(key)
		else:
			command.append(f"{key}={value}")
	result = subprocess.run(command,capture_output=True)
	if result.returncode:
		raise GridlabdRuntimeError(f"gridlabd command failed: {' '.join(command)}\n{result.stderr.decode()}")

	with open(name.replace(".glm",".json")) as fh:
		return json.load(fh)

	raise GridlabdRuntimeError("json load failed")

def insert_class(data,*args,**kwargs):

	raise NotImplementedError("insert_class")

def insert_filter(data,*args,**kwargs):

	raise NotImplementedError("insert_filter")

def insert_global(data,*args,**kwargs):

	if not "name" in kwargs.keys():
		raise GridlabdMissingValue("missing global name")
	name = kwargs["name"]

	if not "type" in kwargs.keys():
		raise GridlabdMissingValue("missing global type")
	gtype = kwargs["type"]
	if gtype not in data["types"].keys():
		raise GridlabdInvalidValue(f"global type '{gtype}' is invalid")

	if not "access" in kwargs.keys():
		access = "PUBLIC" # default is public
	else:
		access = kwargs["access"]
	if access not in ["REFERENCE","PUBLIC","PRIVATE","PROTECTED","HIDDEN"]:
		raise GridlabdInvalidValue(f"global access '{access}' is invalid")

	if not "values" in kwargs.keys():
		value = "" # default is null value
	else:
		value = kwargs["value"]

	globalvars = get_globals(data)
	if name in globalvars.keys():
		raise GridlabdEntityExists(f"global name '{name}' already exists")

	globalvars[name] = {
		"type" : gtype,
		"access" : access,
		"value" : value
	}
	if gtype in ["set","enumeration"]: # special for keywords
		if not "keywords" in kwargs.keys():
			raise GridlabdMissingValue(f"missing {gtype} keywords")
		keywords = {}
		for item in kwargs["keywords"].split(","):
			spec = item.split(":")
			keywords[spec[0]] = spec[1]
		globalvars[name]["keywords"] = keywords

	return data

def insert_module(data,*args,**kwargs):
	"""Insert a module

	ARGUMENTS

	- `data` (dict): original model

	- `args` (list): none

	- `kwargs` (dict): module `name` must be specified

	"""
	result = subprocess.run(["gridlabd","--modhelp=json",kwargs["name"]],capture_output=True)
	if result.returncode:
		raise GridlabdRuntimeError(f"gridlabd command failed: {' '.join(command)}\n{result.stderr.decode()}")
	module = json.loads(result.stdout.decode())

	data["modules"].update(module["modules"])
	data["classes"].update(module["classes"])

	return data

def insert_object(data,*args,**kwargs):
	"""Create object in model

	ARGUMENTS

	- `data` (dict): original model

	- `args` (list): none

	- `kwargs` (dict): Object Properties (must include `class` as well as all 
	  required properties for class)

	RETURNS

	- Data (dict): modified model

	"""
	check_model(data)

	classes = get_classes(data)
	if "class" not in kwargs.keys():
		raise GridlabdModelError(f"class is not specified")
	oclass = kwargs["class"]
	if oclass not in classes.keys():
		raise GridlabdMissingValue(f"class '{oclass}' is not defined")
	
	objects = get_objects(data)
	if "name" in kwargs.keys():
		oname = kwargs["name"]
		del kwargs["name"]
	else:
		oname = f"{oclass}:{len(objects.keys())}"
	if oname in objects.keys():
		raise GridlabdEntityExists(f"object '{oname}' already exists")

	missing = [key for key in get_required_properties(classes,oclass) if key not in kwargs.keys()]
	if missing:
		raise GridlabdMissingValue(f"missing required properties: {', '.join(missing)}")

	objects[oname] = kwargs
	
	return data

def insert_schedule(data,*args,**kwargs):

	raise NotImplementedError("insert_schedule")

def delete_class(data,*args,**kwargs):

	raise NotImplementedError("delete_class")

def delete_filter(data,*args,**kwargs):

	raise NotImplementedError("delete_filter")
	
def delete_global(data,*args,**kwargs):

	raise NotImplementedError("delete_global")

def delete_module(data,*args,**kwargs):

	raise NotImplementedError("delete_module")
	
def delete_object(data,*args,**kwargs):
	check_model(data)
	objects = get_objects(data)
	for name in args:
		refcount = get_object_reference_count(data,name,limit=1)
		if refcount > 0:
			raise GridlabdEntityInUse(f"object '{name}' is referenced at least once")
		elif not name in objects.keys():
			raise GridlabdNoEntity(f"object '{name}' not found")
		del objects[name]
	return data

def delete_schedule(data,*args,**kwargs):

	raise NotImplementedError("delete_schedule")

def update_class(data,*args,**kwargs):

	raise NotImplementedError("update_class")

def update_filter(data,*args,**kwargs):

	raise NotImplementedError("update_filter")

def update_module(data,*args,**kwargs):

	raise NotImplementedError("update_module")

def update_object(data,*args,**kwargs):

	raise NotImplementedError("update_object")

def update_schedule(data,*args,**kwargs):

	raise NotImplementedError("update_schedule")

#
# UTILITIES
#

def get_classes(data):
	"""Get classes in model"""
	if "classes" not in data.keys():
		raise GridlabdModelError("missing class data")
	return data["classes"]

def get_property_type(data,classname,propname):
	if propname in data["header"].keys():
		return data["header"][propname]["type"]
	classes = get_classes(data)
	if classname not in classes.keys():
		raise GridlabdMissingValue(f"class '{classname}' not found")
	classdata = classes[classname]
	if propname not in classdata.keys():
		if "parent" in classdata.keys():
			return get_property_type(data,classdata["parent"],propname)
		raise GridlabdMissingValue(f"property '{propname}' not found in class '{classname}'")
	propdata = classdata[propname]
	if not type(propdata) is dict or "type" not in propdata.keys():
		raise GridlabdModelError(f"property '{propname}' is not a valid")

	return propdata["type"]

def get_filters(data):
	"""Get filters in model"""
	if "filters" not in data.keys():
		return {}
	return data["filters"]

def get_globals(data):
	"""Get globals in model"""
	if "globals" not in data.keys():
		raise GridlabdModelError("missing global data")
	return data["globals"]

def get_modules(data):
	"""Get modules in models"""
	if "modules" not in data.keys():
		raise GridlabdModelError("missing module data")
	return data["modules"]

def get_objects(data):
	"""Get objects in model"""
	if "objects" not in data.keys():
		raise GridlabdModelError("missing object data")
	return data["objects"]

def get_schedules(data):
	"""Get schedules in model"""
	if "schedules" not in data.keys():
		return {}
	return data["schedules"]

def check_model(data,exception=None):
	"""Check whether model is valid"""
	if "application" not in data.keys():
		if exception:
			raise GridlabdModelError("not a gridlabd model") from exception
		return False
	return True

def get_required_properties(classes,oclass):
	"""Get list of required properties in class"""
	required = []
	classdata = classes[oclass]
	for key,info in classdata.items():
		if type(info) is dict \
				and "flags" in info.keys() \
				and "REQUIRED" in set(info["flags"].split("|")):
			required.append(key)
	if "parent" in classdata.keys():
		required.extend(get_required_properties(classes,classdata["parent"]))
	return required

def get_object_reference_count(data,name,limit=1):
	"""Get a count of references to object"""
	refcount = 0
	for key,values in data["objects"].items():
		classname = values["class"]
		for propname,propvalue in values.items():
			if get_property_type(data,classname,propname) == "object" and propvalue == name:
				refcount += 1
				if limit and refcount >= limit:
					return refcount
	return refcount
