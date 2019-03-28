"""
Utility functions to create openapi spec from resource schema
"""
import copy
# [E0611(no-name-in-module), ]
# [E0401(import-error), ]
import distutils.dir_util  # pylint: disable=E0611,E0401
import json
import logging
import os
import sys

# pylint:W0611 Unused import jsonschema
import yaml
import jsonschema  # pylint: disable=W0611
from jsonschema import Draft4Validator

FAMILY_FILE = 'etc/family'
_LOG = logging.getLogger(__name__)


def add_rpcresponses():
    """
    Add generic responses to components/responses section
    of openapi spec for rpc only
    """
    resp_comp = dict()
    resp_comp["Accepted"] = {"description": "Accepted"}
    resp_comp["Processing"] = {"description": "Processing"}
    resp_comp["NoContent"] = {"description": "No Content"}
    resp_comp["SeeOther"] = {"description": "See other"}
    resp_comp["BadRequest"] = {"description": "Bad Reqeust"}
    resp_comp["UnAuthorized"] = {"description": "Unauthorized"}
    resp_comp["NotFound"] = {"description": "Not Found"}
    resp_comp["MethodNotAllowed"] = {"description": "Method Not Allowed"}
    resp_comp["NotAcceptable"] = {"description": "Not Acceptable"}
    resp_comp["Conflict"] = {"description": "Conflict"}
    resp_comp["TooManyRequest"] = {"description": "Too Many Requests"}
    resp_comp["InternalServerError"] = {
        "description": "Internal Server Error"
    }
    resp_comp["ServiceUnavailable"] = {
        "description": "Service Unavailable"
    }
    return resp_comp


def check_jsonschema(schemadoc, filename):
    """
    Check schema against jsonschema Draft4
    """
    error_flag = 0
    try:
        Draft4Validator.check_schema(schemadoc)
    except jsonschema.exceptions.SchemaError as err:
        _LOG.error('Schema error in %s\n%s', filename, err)
        error_flag = 1
    return error_flag


def dump_file_to_openapidir(basedir, openapidir, infile=None):
    """
    Copy common schema files to openapi directory
    """
    outfiledir = os.path.join(openapidir, 'common')
    if infile:
        infildir = os.path.join(os.path.dirname(infile), 'common')
    else:
        infiledir = os.path.join(basedir, 'apischemas', 'rschemas', 'common')
    if os.path.isdir(infiledir):
        if not os.path.isdir(outfiledir):
            os.makedirs(outfiledir)
        distutils.dir_util.copy_tree(infiledir, outfiledir)
        for root, _, files in os.walk(outfiledir):
            for name in files:
                filename = os.path.join(root, name)
                with open(filename) as inputfile:
                    try:
                        value = yaml.load(inputfile)
                    except yaml.YAMLError as err:
                        sys.exit(
                            "Yaml Error in {0}: {1}".format(filename, err)
                        )
                with open(filename, 'w') as outfile:
                    _str = json.dumps(value,
                                      indent=4,
                                      sort_keys=True,
                                      ensure_ascii=False)
                    outfile.write(_str)


# pylint: R1710(inconsistent-return-statements)
def yaml_handler(path):  # pylint: disable=R1710
    """
    Loading yaml reference files
    """
    if path.startswith('file://'):
        with open(path[len('file://'):]) as f:
            return yaml.load(f)


def validate_schema(openapi_doc, filename):
    """
    Check schema is correct
    """
    error_flag = 0
    for _, value in openapi_doc['components']['schemas'].items():
        if check_jsonschema(value, filename):
            error_flag = 1
    return error_flag


def validate_object_field(propname, propval, filename):
    """
    Validate object entry in schema file
    """
    error_flag = 0
    if 'properties' not in propval:
        msg = "%s -- missing field properties in schema file %s"
        _LOG.error(msg, propname, filename)
        error_flag = 1
    return error_flag


def validate_array_field(resolver, propname, propval, filename):
    """
    Validate array entry in schema file
    """
    error_flag = 0
    if 'items' not in propval:
        msg = (
            "%s -- items field missing for array in schema file %s"
        )
        _LOG.error(msg, propname, filename)
        error_flag = 1
        return error_flag
    allowed_types = [
        'integer',
        'number',
        'string',
        'boolean',
        'enum',
        'object',
        'array']
    itemvalue = resolve_reference(resolver,
                                  propname,
                                  propval['items'],
                                  filename)
    if itemvalue == 1:
        error_flag = 1
        return error_flag
    if 'type' in itemvalue:
        itemtype = itemvalue['type']
    elif 'enum' in itemvalue:
        itemtype = itemvalue['enum']
    else:
        itemtype = None
    if itemtype not in allowed_types:
        msg = (
            "%s -- Only basic types allowed for items in array type. "
            "%s not allowed in array type in schema file %s"
        )
        _LOG.error(msg, propname, itemvalue['type'], filename)
        error_flag = 1
    return error_flag


def validate_propertylist_field(resolver,
                                propname,
                                propval,
                                filename):
    """
    Validate propertylist entry in schema file
    """
    error_flag = 0
    if 'key' not in propval:
        msg = (
            "%s -- missing key field in propertylist in schema file %s"
        )
        _LOG.error(msg, propname, filename)
        error_flag = 1
    if 'items' not in propval:
        msg = (
            "%s -- missing items field in schema file %s"
        )
        _LOG.error(msg, propname, filename)
        error_flag = 1
        return error_flag
    itemvalue = resolve_reference(resolver,
                                  propname,
                                  propval['items'],
                                  filename)
    if itemvalue == 1:
        error_flag = 1
        return error_flag
    if itemvalue['type'] != 'object':
        msg = (
            "%s -- Only object type allowed for items in propertylist "
            "in schema file %s"
        )
        _LOG.error(msg, propname, filename)
        error_flag = 1
        return error_flag
    err = validate_object_field(propname, itemvalue, filename)
    return error_flag or err


def _check_valid_ref_file(refname):
    """
    refname should not start with / (ie absoulte path)
    or ..
    """
    if refname.startswith('/'):
        return False
    if refname.startswith('..'):
        return False
    return True


def resolve_reference(resolver, propkey, propval, filename):
    """
    Resolving recursive reference
    """
    error_flag = 0
    val = None
    reference = propval
    stop_iterators = ['enum', 'allOf', 'anyOf', 'oneOf', 'not', 'type']
    while True:
        if any(t in reference for t in stop_iterators):
            val = reference
            break
        elif '$ref' in reference:
            refname = reference['$ref']
            if _check_valid_ref_file(refname):
                reference1 = resolver.resolve(reference['$ref'])
                reference = reference1[1]
            else:
                msg = (
                    "Invalid refname %s "
                    "in schema file %s"
                )
                _LOG.error(msg, refname, filename)
                error_flag = 1
                return error_flag
        else:
            msg = (
                "Invalid definition for parameter: %s "
                "in schema file %s"
            )
            _LOG.error(msg, propkey, filename)
            error_flag = 1
            return error_flag
    if val is None:
        msg = 'Invalid definition for parameter: %s in schema file %s'
        _LOG.error(msg, propkey, filename)
        error_flag = 1
        return error_flag
    else:
        return copy.deepcopy(val)


def check_rpconlybasic_fields(resourcedef, filename):
    """
    Check mandatory basic fields:
    name
    description
    version
    """
    for k in [
            'name',
            'description',
            'version',
    ]:
        if k not in resourcedef:
            sys.exit(
                'Mandatory field missing: {0} in schema file {1}'.format(
                    k, filename))


def check_basic_fields(resourcedef, filename):
    """
    Check mandatory basic fields:
    name
    description
    version
    key
    if 'type' is present, it should be object
    """
    for k in [
            'name',
            'description',
            'version',
            'key'
    ]:
        if k not in resourcedef:
            sys.exit(
                'Mandatory field missing: {0} in schema file {1}'.format(
                    k, filename))
    if 'type' in resourcedef:
        if resourcedef['type'] != 'object':
            sys.exit(
                'Base type should be object in schema file{0}'.format(
                    filename))
        if 'properties' not in resourcedef:
            sys.exit(
                'Missing field: Properties in schema file {0}'.format(
                    filename))


def create_mime_type(resourcedef, family):
    """
    Create mime-type is of format
    vnd.ms.{meta}_{proj}.{lone}.v{version}
    vnd.ms.cookbook.todo.v3.4.1
    """
    mime_format = 'vnd.ms.{0}.{1}.v{2}'.format(family,
                                               resourcedef['name'],
                                               resourcedef['version'])
    return mime_format


def check_property_name(propname, filename):
    """
    Reserved names:  pk, body, key, version, name
    rpc, search, definitions, type,
    on, off, yes, no, true, false
    Hyphen not allowed
    """
    error_flag = 0
    warning_name = ['name', 'type']
    reserved_name = [
        'key', 'version',
        'rpc', 'search',
        'definitions', 'pk', 'body',
        'on', 'off', 'true',
        'false', 'yes', 'no'
    ]
    yaml_bool = [
        'on', 'off', 'true', 'false',
        'yes', 'no'
    ]
    if propname is True or propname is False:
        msg = 'Do not name a property with any of %s in schema file %s'
        _LOG.error(msg, yaml_bool, filename)
        error_flag = 1
        return error_flag
    if propname.lower() in warning_name:
        msg = (
            "%s -- use explicit property names to avoid "
            "ambiguity in schema file %s"
        )
        _LOG.warning(msg, propname, filename)
    if propname.lower() in reserved_name:
        msg = '%s -- reserved keyword used in schema file %s'
        _LOG.error(msg, propname, filename)
        error_flag = 1
    if '-' in propname:
        msg = '%s -- hyphen not allowed in schema file %s'
        _LOG.error(msg, propname, filename)
        error_flag = 1
    return error_flag


def check_property_types(propname, propval, filename):
    """
    Allowed property types
    string
    number
    integer
    mutablehash
    propertylist
    array
    object
    boolean
    enum
    """
    error_flag = 0
    if 'type' in propval:
        prop_type = propval['type']
    elif 'enum' in propval:
        prop_type = 'enum'
    elif 'oneOf' in propval:
        prop_type = 'oneOf'
    elif 'allOf' in propval:
        prop_type = 'allOf'
    elif 'anyOf' in propval:
        prop_type = 'anyOf'
    elif 'not' in propval:
        prop_type = 'not'
    else:
        msg = '%s -- missing type field in schema file %s'
        _LOG.error(msg, propname, filename)
        error_flag = 1
        return error_flag
    if prop_type not in [
            'number',
            'string',
            'integer',
            'boolean',
            'enum',
            'object',
            'array',
            'mutablehash',
            'propertylist',
            'oneOf',
            'allOf',
            'anyOf',
            'not'
    ]:
        msg = '%s -- Unsupported type for property %s in schema file %s'
        _LOG.error(msg, prop_type, propname, filename)
        error_flag = 1
    return error_flag


def check_rpc_definition(rpcverb, rpcval, filename):
    """
    Check RPC verb definition
    """
    error_flag = 0
    if 'response' not in rpcval or (not rpcval['response']):
        msg = '%s -- missing response field in rpc section in schema file %s'
        _LOG.error(msg, rpcverb, filename)
        error_flag = 1
    if 'request' not in rpcval or (not rpcval['request']):
        msg = (
            "%s -- missing request field in rpc section in schema file %s"
        )
        _LOG.error(msg, rpcverb, filename)
        error_flag = 1
    return error_flag


def generate_create_response():
    """
    Generate 1XX, 2XX http responses
    """
    default_responses = {
        "102": {
            "$ref": "#/components/responses/Processing"
        },
        "202": {
            "$ref": "#/components/responses/Accepted"
        }
    }
    return default_responses


def generate_default_response():
    """
    Generate default responses for http requests
    """
    default_responses = {
        "400": {
            "$ref": "#/components/responses/BadRequest"
        },
        "401": {
            "$ref": "#/components/responses/UnAuthorized"
        },
        "404": {
            "$ref": "#/components/responses/NotFound"
        },
        "405": {
            "$ref": "#/components/responses/MethodNotAllowed"
        },
        "406": {
            "$ref": "#/components/responses/NotAcceptable"
        },
        "429": {
            "$ref": "#/components/responses/TooManyRequest"
        },
        "500": {
            "$ref": "#/components/responses/InternalServerError"
        },
        "503": {
            "$ref": "#/components/responses/ServiceUnavailable"
        }
    }
    return default_responses


def generate_default_ok_responses():
    """
    Generate default ok responses for http requests
    """
    default_ok_responses = generate_default_response()
    default_ok_responses["200"] = {
        "$ref": "#/components/responses/Ok"
    }
    return default_ok_responses


def jsonschema_compat(propval):
    """
    Convert resource definition jsonschema compatible
    """
    stringpropval = json.dumps(propval)
    stringpropval = stringpropval.replace(
        "\"type\": \"propertylist\"", "\"type\": \"array\"")
    stringpropval = stringpropval.replace(
        "\"type\": \"mutablehash\"", "\"type\": \"object\"")
    stringpropval = stringpropval.replace(
        "\"$ref\": \"#/definitions/",
        "\"$ref\": \"#/components/schemas/definitions-")
    propdict = json.loads(stringpropval)
    delete_keys_from_dict(propdict)
    return propdict


def delete_keys_from_dict(dict_del):
    """
    Remove unncessary keys from resource definition
    """
    lst_keys = [
        'key', 'version',
        'rpc', 'search',
        'definitions'
    ]
    for k in lst_keys:
        if k in dict_del:
            del dict_del[k]
    for val in list(dict_del.values()):
        if isinstance(val, dict):
            delete_keys_from_dict(val)
    return dict_del


def get_family(basedir):
    """
    Get family name from the etc/family file in basedir
    or from environment
    """
    family = None
    familyfile = os.path.join(basedir, FAMILY_FILE)
    try:
        with open(familyfile) as fh:
            family = fh.read().rstrip()
    except FileNotFoundError as _:
        pass
    if 'family' in os.environ:
        family = os.environ['family']
    if family is None:
        sys.exit('set family name and re-run the command')
    return family
