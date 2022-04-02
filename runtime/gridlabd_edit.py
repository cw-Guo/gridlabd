"""GridLAB-D model editor

SYNTAX

	Shell:

		sh$ gridlabd edit [OPTIONS ...] [COMMAND ...] [ARGUMENTS ...]

	GLM:

		#edit [OPTIONS ...] [COMMAND ...] [ARGUMENTS ...]

	Python:

		>>> import gridlabd_edit as gld
		>>> gld.command(DATA,*COMMAND,**ARGUMENTS)

OPTIONS

  `-d|--debug`: enable debug output to /dev/stderr

  `-i|--inputfile=INPUTFILE`: file to read (default `/dev/stdin`)

  `-o|--outputfile=OUTPUTFILE`: file to write (default `/dev/stdout`)

  `-q|--quiet`: disable error output to /dev/stderr

  `-v|--verbose`: enable verbose operations output to /dev/stderr

  `-w|--warning`: enable warning output to /dev/stderr

  `--relax`: errors as warnings

  `--strict`: warnings as errors

COMMANDS

  `create`: Create a new model. ARGUMENTS are passed to the `gridlabd` command
  line to be used in creating the model.

  `delete {class,filter,global,module,object,schedule}`: Delete a component.

	`delete class name=NAME [--force]`: TODO

	`delete filter name=NAME [--force]`: TODO

	`delete global name=NAME [--force]`: TODO

	`delete module name=NAME [--force]`: TODO

	`delete object name=NAME [--force]`: TODO

	`delete schedule name=NAME [--force]`: TODO

  `insert {class,filter,global,module,object,schedule}`: Insert a component in the model.  

	`insert class name=NAME [PROPERTY=VALUE ...]`: TODO

	`insert filter name=NAME [PROPERTY=VALUE ...]`: TODO

	`insert global name=NAME [PROPERTY=VALUE ...]`: TODO

	`insert module name=NAME [PROPERTY=VALUE ...]`: TODO

	`insert object class=CLASS name=NAME [PROPERTY=VALUE ...]`: Insert an object
	into the model.  The class must be specified. If name is not specified the
	name is automatically generated as CLASS:ID, where ID is the next id number
	available.

	`insert schedule name=NAME [PROPERTY=VALUE ...]`: TODO

  `search {class,filter,global,module,object,schedule}`: Find a component in the model.

  `update {class,filter,global,module,object,schedule}`: Update a component in the model.

	`update class name=NAME [PROPERTY=VALUE ...]`: TODO

	`update filter name=NAME [PROPERTY=VALUE ...]`: TODO

	`update global name=NAME [PROPERTY=VALUE ...]`: TODO

	`update module name=NAME [PROPERTY=VALUE ...]`: TODO

	`update object name=NAME [PROPERTY=VALUE ...]`: TODO

	`update schedule name=NAME [PROPERTY=VALUE ...]`: TODO

  `script`:


DESCRIPTION

"""

import sys, os, subprocess
from warnings import warn as warning
import json

E_OK = 0 # no error
E_INVALID = 1 # invalid arguments
E_FAILED = 2 # gridlabd error
E_ACCESS = 3 # file access error
E_SYNTAX = 9 # syntax error
E_EXCEPTION = 99 # exception caught

VERBOSE = False
DEBUG = False
QUIET = False
WARNING = True
WARNINGMODE = "NORMAL" # "RELAX": errors as warnings, "STRICT": warnings as errors

VALID_COMMANDS = {
	"create" : {"input":0,"args":1,"kwargs":1}, # create [...]
	"delete" : {"input":1,"args":2,"kwargs":1}, # delete COMPONENT ...
	"insert" : {"input":1,"args":2,"kwargs":1}, # insert COMPONENT ...
	"search" : {"input":1,"args":2,"kwargs":1}, # search COMPONENT ...
	"script" : {"input":1,"args":1,"kwargs":1}, # script ...
	"update" : {"input":1,"args":2,"kwargs":1}, # update COMPONENT ...
}

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

class GridlabdModel:

	INPUTFILE = sys.stdin
	OUTPUTFILE = sys.stdout
	SCRIPTFILE = None
	COMMANDS = []
	KEYWORDS = {}
	DATA = None

	def __init__(self,args=None,file=None,name=None):

		if args:
			self.parse(args)
			if self.INPUTFILE and self.INPUTFILE.isatty():
				error("input is a tty",gld.E_INVALID)

		elif type(file) is str:
			self.INPUTFILE = open(file,"r")
		elif filename != None:
			self.INPUTFILE = file

		if self.INPUTFILE:
			self.read(INPUTFILE)
		else:
			self.create(name=name)

	def parse(self,args):
		"""Parse input command arguments

		ARGUMENTS

			args (list): command arguments

		RETURNS

			boolean: True if command needs processing, False if no processing required

		EXCEPTIONS

			GridlabdInvalidCommand: error parsing command arguments
		"""
		for arg in args:

			# extract arg specs
			spec = arg.split("=")
			tag = spec[0]
			if len(spec) == 1:
				value = None
			elif len(spec) == 2:
				value = spec[1]
			else:
				value = spec[1:]

			if tag in ['-d','--debug']:
				global DEBUG
				DEBUG = True
			elif tag in ['-h','--help','help']:
				print(__doc__,file=self.OUTPUTFILE)
				return False
			elif tag in ['-i','--inputfile']:
				if value == "/dev/stdin":
					self.INPUTFILE = sys.stdin
				elif value:
					self.INPUTFILE = open(value,"r")
				else:
					self.INPUTFILE = None
			elif tag in ['-o','--outputfile']:
				if value == "/dev/stdout":
					self.OUTPUTFILE = sys.stdout
				elif value:
					self.OUTPUTFILE = open(value,"w")
				else:
					self.OUTPUTFILE = None
			elif tag in ['-q','--quiet']:
				global QUIET
				QUIET = True
			elif tag == '--relax':
				global WARNINGMODE
				if WARNINGMODE == "STRICT":
					raise GridlabdInvalidCommand("--relax conflicts with --strict",E_INVALID)
				WARNINGMODE = "RELAX"
			elif tag == '--strict':
				if WARNINGMODE == "RELAX":
					raise GridlabdInvalidCommand("--strict conflicts with --relax",E_INVALID)
				WARNINGMODE = "STRICT"
			elif tag in ['-v','--verbose']:
				global VERBOSE
				VERBOSE = True
			elif tag in ['-w','--warning']:
				global WARNING
				WARNING = False
			elif value != None:
				if tag in self.KEYWORDS.keys():
					raise GridlabdInvalidCommand(f"{arg}: key '{tag}' already specified")
				else:
					self.KEYWORDS[tag] = value
			elif not tag.startswith('-') and ( len(self.COMMANDS) == 0 or len(self.COMMANDS) < VALID_COMMANDS[self.COMMANDS[0]]["args"] ):
				self.COMMANDS.append(arg)
			elif VALID_COMMANDS[self.COMMANDS[0]]["kwargs"] > 0 and len(self.COMMANDS) == VALID_COMMANDS[self.COMMANDS[0]]["args"]:
				self.KEYWORDS[tag] = value
			else:
				raise GridlabdInvalidCommand(f"'{arg}' is invalid",E_INVALID)

		if VALID_COMMANDS[self.COMMANDS[0]]["input"] == 0:
			if self.INPUTFILE != sys.stdin:
				warning(f"command '{self.COMMANDS[0]}' ignores input data")
			self.INPUTFILE = None

		return True

	# 
	# FILE READ
	#
	def read(self,file,*args,**kwargs):
		self.DATA = json.load(file,*args,**kwargs)
		self.check_model()
		return self.DATA

	#
	# FILE WRITE
	#

	def write(self,file=None,*args,**kwargs):
		if file == None:
			file = self.OUTPUTFILE
		json.dump(self.DATA,file,*args,**kwargs)

	#
	# COMMANDS
	#
	def command(self,*args,**kwargs):
		"""Run a model edit command

		ARGUMENTS

		- COMMAND
		- SUBCOMMAND
		- ARGUMENTS

		"""
		if len(args) == 0:
			raise GridlabdInvalidCommand("missing command")

		cmd = args[0]
		if not cmd in VALID_COMMANDS.keys():
			raise GridlabdInvalidCommand(f"command '{args[0]}' in not valid")

		nargs = VALID_COMMANDS[cmd]["args"]
		if len(args) < nargs:
			raise GridlabdInvalidCommand(f"'{args[0]}': missing {nargs-len(args)} argument(s)")

		fname = "_".join(args[0:nargs])

		nkwds = VALID_COMMANDS[cmd]["kwargs"]
		if len(kwargs) < nkwds:
			raise GridlabdInvalidCommand(f"'{args[0]}' missing {nkwds-len(kwargs)} keyword(s)")

		call = getattr(self,fname)
		if not fname in dir(self) or type(call).__name__ not in ["method"]:
			raise GridlabdInvalidCommand(f"'{args[0]}': '{fname}' is not a method in class {self.__name__}")

		if self.DATA != None and VALID_COMMANDS[cmd]["input"] == 0:
			raise GridlabdInvalidCommand(f"unexpected input data")

		if self.DATA == None and VALID_COMMANDS[cmd]["input"] == 1:
			raise GridlabdInvalidCommand(f"expected input data")

		return call(self,*args[nargs:],**kwargs)

	def create(self,*args,**kwargs):
		"""Create new model

		ARGUMENTS

			*args (list) - none required

			**kwargs (dict) - options

			- `name` : specify the model name (default is "untitled")
		"""
		if "name" not in kwargs.keys():
			raise GridlabdMissingValue(f"create: 'name' not specified")
		name = kwargs["name"]
		del kwargs["name"]

		if name == None or isempty(name):
			name = "untitled"
			n = 0
			while os.path.exists(f"{name}.glm") or os.path.exists(f"{name}.json"):
				name = f"untitled_{n}"
				n += 1

		if os.path.exists(f"{name}.glm"):
			warning(f"{name}.glm exists")

		if os.path.exists(f"{name}.json"):
			warning(f"{name}.json exists")

		with open(f"{name}.glm","w") as fh:
			fh.write("")

		command = ["gridlabd","-C",name+".glm","-o",name+".json"]
		for key,value in kwargs.items():
			if value == None:
				command.append(key)
			else:
				command.append(f"{key}={value}")
		result = subprocess.run(command,capture_output=True)
		if result.returncode:
			raise GridlabdRuntimeError(f"gridlabd command failed: {' '.join(command)}\n{result.stderr.decode()}")

		with open(name+".json") as fh:
			self.DATA = json.load(fh)
		if not self.DATA:
			raise GridlabdRuntimeError("json load failed")

		self.check_model()

	def delete_class(self,*args,**kwargs):

		if "name" not in kwargs.keys():
			raise GridlabdInvalidCommand(f"class name not specified")
		name = kwargs["name"]

		classes = self.get_classes()
		if name not in classes.keys():
			raise GridlabdNoEntity(f"class '{name}' does not exist")

		if self.get_class_reference_count(name,limit=1) > 0:
			raise GridlabdEntityInUse(f"class '{name}' is referenced at least once")

		del classes[name]

	def delete_filter(self,*args,**kwargs):

		raise NotImplementedError("delete_filter")
		
	def delete_global(self,*args,**kwargs):

		raise NotImplementedError("delete_global")

	def delete_module(self,*args,**kwargs):

		raise NotImplementedError("delete_module")
		
	def delete_object(self,*args,**kwargs):

		objects = self.get_objects()

		if "name" not in kwargs.keys():
			raise GridlabdInvalidCommand(f"class name not specified")
		name = kwargs["name"]

		refcount = self.get_object_reference_count(name,limit=1)
		if refcount > 0:
			raise GridlabdEntityInUse(f"object '{name}' is referenced at least once")
		elif not name in objects.keys():
			raise GridlabdNoEntity(f"object '{name}' not found")

		del objects[name]

	def delete_schedule(self,*args,**kwargs):

		raise NotImplementedError("delete_schedule")

	def insert_class(self,*args,**kwargs):

		raise NotImplementedError("insert_class")

	def insert_filter(self,*args,**kwargs):

		raise NotImplementedError("insert_filter")

	def insert_global(self,*args,**kwargs):

		if not "name" in kwargs.keys():
			raise GridlabdMissingValue("missing global name")
		name = kwargs["name"]

		if not "type" in kwargs.keys():
			gtype = "char1024"
		else:
			gtype = kwargs["type"]
		if gtype not in self.get_types().keys():
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

		globalvars = self.get_globals()
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

	def insert_module(self,*args,**kwargs):
		"""Insert a module

		ARGUMENTS

		- `args` (list): none

		- `kwargs` (dict): module `name` must be specified

		"""
		result = subprocess.run(["gridlabd","--modhelp=json",kwargs["name"]],capture_output=True)
		if result.returncode:
			raise GridlabdRuntimeError(f"gridlabd command failed: {' '.join(command)}\n{result.stderr.decode()}")
		module = json.loads(result.stdout.decode())

		self.get_modules().update(module["modules"])
		self.get_classes().update(module["classes"])

	def insert_object(self,*args,**kwargs):
		"""Create object in model

		ARGUMENTS

		- `args` (list): none

		- `kwargs` (dict): Object Properties (must include `class` as well as all 
		  required properties for class)

		RETURNS

		- Data (dict): modified model

		"""
		classes = self.get_classes()
		objects = self.get_objects()

		if "class" not in kwargs.keys():
			raise GridlabdModelError(f"class is not specified")
		oclass = kwargs["class"]
		if oclass not in classes.keys():
			raise GridlabdMissingValue(f"class '{oclass}' is not defined")
		
		if "id" in kwargs.keys():
			warning(f"object cannot specify its id (this is automatically assigned)")
		kwargs["id"] = len(objects)

		if "name" in kwargs.keys():
			oname = kwargs["name"]
			del kwargs["name"]
		else:
			oname = f"{oclass}:{kwargs['id']}"
		if oname in objects.keys():
			raise GridlabdEntityExists(f"object '{oname}' already exists")

		missing = [key for key in get_required_properties(classes,oclass) if key not in kwargs.keys()]
		if missing:
			raise GridlabdMissingValue(f"missing required properties: {', '.join(missing)}")

		objects[oname] = kwargs
		
	def insert_schedule(self,*args,**kwargs):

		raise NotImplementedError("insert_schedule")

	def script(self,*args,**kwargs):

		if "name" not in kwargs.keys():
			raise GridlabdMissingValue(f"missing script name")
		name = kwargs["name"]
		with open(name,"r") as fh:
			for lineno, line in enumerate(fh.readlines()):
				try:
					global DATA
					global COMMANDS
					global KEYWORDS
					parse(line.strip().split(" "))
					DATA = command(DATA,*COMMANDS,**KEYWORDS)
				except Exception as err:
					etype,evalue,etrace = sys.exc_info()
					raise etype(f"script '{name}' error at line {lineno+1} - {evalue}") from err
		return DATA


	def update_class(self,*args,**kwargs):

		raise NotImplementedError("update_class")

	def update_filter(self,*args,**kwargs):

		raise NotImplementedError("update_filter")

	def update_module(self,*args,**kwargs):

		raise NotImplementedError("update_module")

	def update_object(self,*args,**kwargs):

		raise NotImplementedError("update_object")

	def update_schedule(self,*args,**kwargs):

		raise NotImplementedError("update_schedule")

	#
	# UTILITIES
	#

	def get_classes(self):
		"""Get classes in model"""
		return self.DATA["classes"]

	def get_headers(self):
		return self.DATA["header"]

	def get_property_type(self,classname,propname):
		if propname in self.get_headers().keys():
			return self.get_headers()[propname]["type"]
		classes = self.get_classes()
		if classname not in classes.keys():
			raise GridlabdMissingValue(f"class '{classname}' not found")
		classdata = classes[classname]
		if propname not in classdata.keys():
			if "parent" in classdata.keys():
				return self.get_property_type(classdata["parent"],propname)
			raise GridlabdMissingValue(f"property '{propname}' not found in class '{classname}'")
		propdata = classdata[propname]
		if not type(propdata) is dict or "type" not in propdata.keys():
			raise GridlabdModelError(f"property '{propname}' is not a valid")

		return propdata["type"]

	def get_filters(self):
		"""Get filters in model"""
		if "filters" not in self.DATA.keys():
			return {}
		return self.DATA["filters"]

	def get_globals(self):
		"""Get globals in model"""
		if "globals" not in self.DATA.keys():
			raise GridlabdModelError("missing global data")
		return self.DATA["globals"]

	def get_modules(self):
		"""Get modules in models"""
		if "modules" not in self.DATA.keys():
			raise GridlabdModelError("missing module data")
		return self.DATA["modules"]

	def get_objects(self):
		"""Get objects in model"""
		if "objects" not in self.DATA.keys():
			raise GridlabdModelError("missing object data")
		return self.DATA["objects"]

	def get_schedules(self):
		"""Get schedules in model"""
		if "schedules" not in self.DATA.keys():
			return {}
		return self.DATA["schedules"]

	def check_model(self,quick=True,exception=True):
		"""Check whether model is valid"""
		for required in ["application","version","classes","header","types","modules","globals","objects"]:
			if required not in self.DATA.keys():
				if exception:
					raise GridlabdModelError("not a gridlabd model") from exception
				return False
		if quick:
			return True
		# TODO: more thorough checks
		return True

	def get_version(self):
		return self.DATA["version"]

	def get_required_properties(self,oclass):
		"""Get list of required properties in class"""
		required = []
		classdata = self.get_classes()[oclass]
		for key,info in classdata.items():
			if type(info) is dict \
					and "flags" in info.keys() \
					and "REQUIRED" in set(info["flags"].split("|")):
				required.append(key)
		if "parent" in classdata.keys():
			required.extend(get_required_properties(classes,classdata["parent"]))
		return required

	def get_object_reference_count(self,name,limit=1):
		"""Get a count of references to object"""
		refcount = 0
		for key,values in self.get_objects().items():
			classname = values["class"]
			for propname,propvalue in values.items():
				if self.get_property_type(classname,propname) == "object" and propvalue == name:
					refcount += 1
					if limit and refcount >= limit:
						return refcount
		return refcount

	def get_class_reference_count(self,name,limit=1):
		"""Get a count of references to class"""
		refcount = 0
		for key,values in self.get_classes().items():
			if "parent" in values.keys() and values["parent"] == name:
				refcount += 1
				if limit and refcount >= limit:
					return refcount
		for key,values in self.get_objects().items():
			if "class" in values.keys() and values["class"] == name:
				refcount += 1
				if limit and refcount >= limit:
					return refcount
		return refcount

	def get_types(self):
		return self.DATA["types"]
