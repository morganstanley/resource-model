"""
create openapi spec from resource schema
for Openapi 3.0 version
"""
# pylint:C0302 Too many lines in module (1306/1000)
# pylint: disable=C0302
import copy
import json
import logging

import yaml
# pylint:W0611 Unused import jsonschema
import jsonschema  # pylint: disable=W0611
from jsonschema import RefResolver

from . import utils
_LOG = logging.getLogger(__name__)


class VersionV3():
    """
    Version V3 - Openapi spec 3.0 with jsonschema validation
    """
    def __init__(self, openapi, specfile,
                 schema, outfmt, mimetype, version,
                 schemafile, openapidir):
        """
        Initialize v3 object
        """
        self.openapi = openapi
        self.specfile = specfile
        self.schemafile = schemafile
        self.version = version
        self.resourcedef = schema
        self.yaml_content = 'application/{0}+yaml'.format(mimetype)
        self.json_content = 'application/{0}+json'.format(mimetype)
        self.mimetype = mimetype
        self.outfmt = outfmt
        self.inresponses = dict()
        self.delresponses = dict()
        base = "file://{0}/".format(openapidir)
        handlers = {'file': utils.yaml_handler}
        self.resolver = RefResolver(base_uri=base,
                                    referrer=schema,
                                    handlers=handlers)
        self.error = 0
        self.hasbody = 'type' in schema
        self.bodyreq = 'required' in schema

    def create_spec(self):
        """
        Create v3 openapi 3.0 spec
        """
        self.add_definitions()
        if 'rpconly' in self.resourcedef and self.resourcedef['rpconly']:
            resp_comp = utils.add_rpcresponses()
            self.openapi['components']["responses"] = resp_comp
            self.add_rpcverbs()
        else:
            self.add_responses()
            self.inresponses = copy.deepcopy(
                utils.generate_default_response())
            self.inresponses["200"] = {
                "$ref": (
                    "#/components/responses/Ok"
                )
            }
            self.inresponses.update(
                copy.deepcopy(utils.generate_create_response()))
            self.delresponses = copy.deepcopy(
                utils.generate_default_response())
            self.delresponses["204"] = {
                "$ref": (
                    "#/components/responses/NoContent"
                )
            }
            err = self.add_parameters()
            if not err:
                self.add_basepath()
                self.add_pkpath()
                if self.hasbody:
                    self.add_extrapaths()
            self.add_rpcverbs()

    def add_definitions(self):
        """
        Copy definitions section to components section
        in openapi spec V3
        """
        error_flag = 0
        if 'definitions' in self.resourcedef:
            defval = utils.jsonschema_compat(self.resourcedef['definitions'])
            definitionsobj = {'definitions': defval}
            if utils.check_jsonschema(definitionsobj, self.schemafile):
                error_flag = 1
                self.error = 1
                return error_flag
            for key, value in definitionsobj['definitions'].items():
                self.openapi['components']['schemas'][
                    'definitions-' + key] = value
        return error_flag

    def add_responses(self):
        """
        Add generic responses to components/responses section
        of openapi spec for v3
        """
        resp_comp = dict()
        resp_comp["Ok_all"] = {
            "description": "OK",
            "content": {
                self.yaml_content: {
                    'schema': {
                        'type': "object",
                        "properties": {
                            "_elem": {
                                'type': "array",
                                'items': {
                                    "$ref": (
                                        "#/components/schemas/primary_key"
                                    )
                                }
                            },
                            "_links": {
                                "type": "object",
                                "properties": {
                                    "_self": {
                                        "type": "object",
                                        "properties": {
                                            "href": {
                                                "type": "string"
                                            }
                                        }
                                    },
                                    "_prev": {
                                        "type": "object",
                                        "properties": {
                                            "href": {
                                                "type": "string"
                                            }
                                        }
                                    },
                                    "_next": {
                                        "type": "object",
                                        "properties": {
                                            "href": {
                                                "type": "string"
                                            }
                                        }
                                    }
                                },
                                "required": ["_self"]
                            }
                        },
                        "additionalProperties": True
                    }
                },
                self.json_content: {
                    'schema': {
                        'type': "object",
                        "properties": {
                            "_elem": {
                                'type': "array",
                                'items': {
                                    "$ref": (
                                        "#/components/schemas/primary_key"
                                    )
                                }
                            },
                            "_links": {
                                "type": "object",
                                "properties": {
                                    "_self": {
                                        "type": "object",
                                        "properties": {
                                            "href": {
                                                "type": "string"
                                            }
                                        }
                                    },
                                    "_prev": {
                                        "type": "object",
                                        "properties": {
                                            "href": {
                                                "type": "string"
                                            }
                                        }
                                    },
                                    "_next": {
                                        "type": "object",
                                        "properties": {
                                            "href": {
                                                "type": "string"
                                            }
                                        }
                                    },
                                },
                                "required": ["_self"]
                            }
                        },
                        "additionalProperties": True
                    }
                }
            }
        }
        resp_comp["Ok"] = {
            "description": "OK",
            "content": {
                self.json_content: {
                    'schema': {
                        "$ref": (
                            "#/components/schemas/" +
                            self.resourcedef['name']
                        )
                    }
                },
                self.yaml_content: {
                    'schema': {
                        "$ref": (
                            "#/components/schemas/" +
                            self.resourcedef['name']
                        )
                    }
                }
            }
        }
        resp_comp["Created"] = {
            "description": "Created",
            "content": {
                self.json_content: {
                    'schema': {
                        "$ref": (
                            "#/components/schemas/" +
                            self.resourcedef['name']
                        )
                    }
                },
                self.yaml_content: {
                    'schema': {
                        "$ref": (
                            "#/components/schemas/" +
                            self.resourcedef['name']
                        )
                    }
                }
            }
        }
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
        self.openapi['components']["responses"] = resp_comp

    def add_parameters(self):
        """
        Add parameters to components/parameters section of openapi spec v3
        """
        error_flag = 0
        para_comp = dict()
        para_comp["PrimaryKeyParm"] = {
            "name": "primary_key",
            "in": "path",
            "required": True,
            "schema": {
                "$ref": "#/components/schemas/primary_key"
            }
        }
        para_comp["Pagination_limit"] = {
            "name": "_limit",
            "required": False,
            "in": "query",
            "style": "form",
            "explode": False,
            "schema": {
                "type": "integer",
                "minimum": 1,
                "maximum": 30,
                "default": 20
            }
        }
        para_comp["Pagination_cursor"] = {
            "name": "_cursor",
            "required": False,
            "in": "query",
            "style": "form",
            "explode": False,
            "schema": {
                "type": "string"
            }
        }
        if 'search' in self.resourcedef:
            if not isinstance(self.resourcedef['search'], list):
                msg = 'search field should be a list in schema %s'
                _LOG.error(msg, self.schemafile)
                self.error = 1
                error_flag = 1
                return error_flag
            for search_by in self.resourcedef['search']:
                if 'name' not in search_by:
                    msg = (
                        'search -- name field missing in search schema file%s'
                    )
                    _LOG.error(msg, self.schemafile)
                    self.error = 1
                    error_flag = 1
                    return error_flag
                if search_by['name'] in ['pk', 'body']:
                    msg = '%s -- reserved keyword in search schema file %s'
                    _LOG.error(msg, search_by['name'], self.schemafile)
                    self.error = 1
                    error_flag = 1
                    return error_flag
                if 'schema' not in search_by:
                    msg = '%s -- schema field missing in search schema file %s'
                    _LOG.error(msg, search_by['name'], self.schemafile)
                    self.error = 1
                    error_flag = 1
                    return error_flag
                if utils.check_jsonschema(
                        search_by['schema'], self.schemafile
                ):
                    self.error = 1
                    error_flag = 1
                    return error_flag
                search_by['style'] = 'form'
                search_by['explode'] = False
                search_by['in'] = 'query'
                para_comp[search_by['name']] = search_by
        self.openapi['components']["parameters"] = para_comp
        return error_flag

    def add_basepath(self):
        """
        Add base path to openapi spec v3
        """
        resource = copy.deepcopy(self.resourcedef)
        resource.pop('name', None)
        self.openapi['components']['schemas'][
            self.resourcedef['name']] = utils.jsonschema_compat(resource)
        self.openapi['paths']['/' + self.resourcedef['name']] = dict()
        operationid = self.resourcedef['name'] + "_get_all_" + self.version
        parameters = [
            {
                "name": "_limit",
                "required": False,
                "in": "query",
                "style": "form",
                "explode": False,
                "schema": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 30,
                    "default": 20
                }
            },
            {
                "name": "_cursor",
                "required": False,
                "in": "query",
                "style": "form",
                "explode": False,
                "schema": {
                    "type": "string"
                }
            }
        ]

        if 'search' in self.resourcedef:
            for search_by in self.resourcedef['search']:
                parameters.append(self.openapi['components'][
                    'parameters'][search_by['name']])
        base_responses = copy.deepcopy(
            utils.generate_default_response())
        base_responses['200'] = {
            "$ref": "#/components/responses/Ok_all"
        }
        opengapigetall = {
            'get': {
                'tags': [self.resourcedef['name']],
                'description': "Get all the resources",
                'operationId': operationid,
                'parameters': parameters,
                'responses': base_responses
            }
        }
        self.openapi['paths']['/' + self.resourcedef['name']][
            'get'] = opengapigetall['get']
        operationid = self.resourcedef['name'] + '_post_' + self.version
        desc = 'create a {0}'.format(self.resourcedef['name'])
        reqbody = {
            "description": desc,
            "required": self.bodyreq,
            "content": {
                self.yaml_content: {
                    "schema": {
                        "$ref": (
                            "#/components/schemas/" +
                            self.resourcedef['name']
                        )
                    }
                },
                self.json_content: {
                    "schema": {
                        "$ref": (
                            "#/components/schemas/" +
                            self.resourcedef['name']
                        )
                    }
                }
            }
        }
        openapicreate = {
            'post': {
                'tags': [self.resourcedef['name']],
                'description': desc,
                'operationId': operationid,
                'parameters': [],
                'responses': self.inresponses
            }
        }
        if self.hasbody:
            openapicreate['post']['requestBody'] = reqbody
        self.openapi['paths']['/' + self.resourcedef['name']][
            'post'] = openapicreate['post']

    def add_pkpath(self):
        """
        Add primary key path to openapi spec v3
        """
        self.openapi['components']['schemas'][
            'primary_key'] = self.resourcedef['key']
        self.openapi['paths'][
            '/' + self.resourcedef['name'] + '/{primary_key}'] = dict()
        operationid = self.resourcedef['name'] + '_pk_delete_' + self.version
        parameters = [{
            "name": "primary_key",
            "in": "path",
            "required": True,
            "schema": {
                "$ref": "#/components/schemas/primary_key"
            }
        }]
        desc = 'delete a {0}'.format(self.resourcedef['name'])
        openapidelete = {
            'delete': {
                'tags': [self.resourcedef['name']],
                'description': desc,
                'operationId': operationid,
                'parameters': parameters,
                'responses': self.delresponses
            }
        }
        self.openapi['paths'][
            '/' + self.resourcedef['name'] + '/{primary_key}'][
                'delete'] = openapidelete['delete']
        operationid = self.resourcedef['name'] + '_pk_get_' + self.version
        responses = copy.deepcopy(utils.generate_default_response())
        responses["200"] = {
            "$ref": "#/components/responses/Ok"
        }
        desc = 'get a {0}'.format(self.resourcedef['name'])
        openapiget = {
            'get': {
                'tags': [self.resourcedef['name']],
                'description': desc,
                'operationId': operationid,
                'parameters': parameters,
                'responses': responses
            }
        }
        self.openapi['paths'][
            '/' + self.resourcedef['name'] + '/{primary_key}'][
                'get'] = openapiget['get']
        operationid = self.resourcedef['name'] + "_pk_put_" + self.version
        reqbody = {
            "required": self.bodyreq,
            "content": {
                self.yaml_content: {
                    "schema": {
                        "$ref": (
                            "#/components/schemas/" +
                            self.resourcedef['name']
                        )
                    }
                },
                self.json_content: {
                    "schema": {
                        "$ref": (
                            "#/components/schemas/" +
                            self.resourcedef['name']
                        )
                    }
                }
            }
        }
        desc = 'create a {0}'.format(self.resourcedef['name'])
        openapicreate = {
            'put': {
                'tags': [self.resourcedef['name']],
                'description': desc,
                'operationId': operationid,
                'parameters': parameters,
                'responses': self.inresponses
            }
        }
        if self.hasbody:
            openapicreate['put']['requestBody'] = reqbody
        self.openapi['paths'][
            '/' + self.resourcedef['name'] + '/{primary_key}'][
                'put'] = openapicreate['put']

    def add_extrapaths(self):
        """
        Add extended paths v3
        """
        basepath = '/' + self.resourcedef['name'] + '/{primary_key}'
        parameters = [{
            "name": "primary_key",
            "in": "path",
            "required": True,
            "schema": {
                "$ref": "#/components/schemas/primary_key"
            }
        }]
        operationid = self.resourcedef['name'] + '_pk'
        if 'properties' in self.resourcedef:
            requirelist = list()
            if 'required' in self.resourcedef:
                requirelist = self.resourcedef['required']
            self.findallpaths(self.resourcedef['properties'],
                              basepath,
                              operationid,
                              self.resourcedef['name'],
                              parameters,
                              requirelist)

    def findallpaths_in_mhash(self,
                              propname,
                              propval,
                              parametername,
                              operationid,
                              parameters,
                              newpath,
                              basepath,
                              tagname,
                              opid,
                              propbodyreq):
        """
        Add all paths for mutable hash v3
        """
        propkeys = list(propval['properties'].keys())
        self.openapi['components']['schemas'][
            propname + "_keys"] = {"type": "string", "enum": propkeys}
        newschema = {
            "$ref": "#/components/schemas/" + propname
        }
        removeschema = {
            "$ref": (
                "#/components/schemas/" +
                propname + "_keys"
            )
        }
        if parametername not in (
                self.openapi['components'][
                    'parameters']
        ):
            self.openapi['components']["parameters"][parametername] = {
                "in": "path",
                "name": parametername,
                "required": True,
                "schema": removeschema
            }
        openapimutablehash = dict()
        # insert
        for key in propkeys:
            keypath = basepath + '/' + propname + '/' + key
            self.openapi['paths'][keypath] = dict()
            newschema = {
                "$ref": "#/components/schemas/" + key
            }
            reqbody = {
                "required": True,
                "content": {
                    self.yaml_content: {
                        "schema": newschema
                    },
                    self.json_content: {
                        "schema": newschema
                    }
                }
            }
            desc = 'insert {0} to a {1}'.format(propname,
                                                self.resourcedef['name'])
            openapimutablehash = {
                'tags': [tagname],
                "description": desc,
                "operationId": (
                    opid +
                    '_' +
                    propname +
                    '_' +
                    key +
                    '_put_' +
                    self.version
                ),
                'parameters': parameters,
                'requestBody': reqbody,
                "responses": self.inresponses
            }
            self.openapi['paths'][keypath][
                'put'] = copy.deepcopy(openapimutablehash)

        # remove
        desc = 'delete {0} from a {1}'.format(propname,
                                              self.resourcedef['name'])
        removeparameters = [{
            "in": "path",
            "name": parametername,
            "required": True,
            "schema": removeschema
        }]
        openapimutablehash[
            'parameters'] = removeparameters + parameters
        openapimutablehash.pop('requestBody', None)
        openapimutablehash['operationId'] = (
            operationid +
            '_delete_' +
            self.version
        )
        openapimutablehash['description'] = desc
        openapimutablehash['responses'] = self.delresponses
        self.openapi['paths'][newpath][
            'delete'] = copy.deepcopy(openapimutablehash)
        # replace
        replacepath = basepath + '/' + propname
        self.openapi['paths'][replacepath] = dict()
        openapimutablehash['operationId'] = (
            operationid +
            '_put' +
            self.version
        )
        desc = 'replace {0} in a {1}'.format(propname,
                                             self.resourcedef['name'])
        openapimutablehash['description'] = desc
        openapimutablehash['parameters'] = parameters
        replaceschema = {
            "$ref": (
                "#/components/schemas/" +
                propname
            )
        }
        reqbody = {
            "required": propbodyreq,
            "content": {
                self.yaml_content: {
                    "schema": replaceschema
                },
                self.json_content: {
                    "schema": replaceschema
                }
            }
        }
        openapimutablehash['requestBody'] = reqbody
        openapimutablehash['responses'] = self.inresponses
        self.openapi['paths'][replacepath][
            'put'] = copy.deepcopy(openapimutablehash)
        # patch
        openapimutablehash['description'] = (
            "bulk insert/remove part of resource")
        openapimutablehash['operationId'] = operationid + '_patch'
        oplist = ["insert", "remove"]
        jsonpatchdoc = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "op": {
                        "type": "string",
                        "enum": oplist
                    },
                    "value": replaceschema
                }
            }
        }
        reqbody = {
            "required": True,
            "content": {
                self.yaml_content: {
                    "schema": jsonpatchdoc
                },
                self.json_content: {
                    "schema": jsonpatchdoc
                }
            }
        }
        openapimutablehash['requestBody'] = reqbody
        # self.openapi['paths'][replacepath][
        #    'patch'] = copy.deepcopy(openapimutablehash)

    # R0915: Too many statements (51/50)
    # pylint: disable=R0915
    def findallpaths_in_proplist(self,
                                 propname,
                                 propval,
                                 parametername,
                                 operationid,
                                 parameters,
                                 newpath,
                                 basepath,
                                 tagname,
                                 propbodyreq):
        """
        Add all paths for property list v3
        """
        keys = propval['key']
        itemval = utils.resolve_reference(self.resolver,
                                          propname,
                                          propval['items'],
                                          self.schemafile)
        if itemval == 1:
            self.error = 1
            return
        value = utils.jsonschema_compat(itemval)
        value.pop('key', None)
        items = {"type": "object", "required": keys, "properties": {}}
        for k in keys:
            items["properties"][k] = {
                "$ref": "#/components/schemas/" + k
            }
            value['properties'].pop(k, None)
            if 'required' in value:
                try:
                    value['required'].remove(k)
                except ValueError:
                    pass
        self.openapi['components']['schemas'][
            propname + "_keys"] = items
        self.openapi['components']['schemas'][
            propname + "_value"] = value
        proplist_schema = {
            "$ref": (
                "#/components/schemas/" +
                propname + "_keys"
            )
        }
        newschema = {
            "$ref": "#/components/schemas/" + propname
        }
        # insert
        insertschema = {
            "$ref": (
                "#/components/schemas/" +
                propname + "_value"
            )
        }
        if parametername not in (
                self.openapi['components'][
                    'parameters']
        ):
            self.openapi['components']["parameters"][parametername] = {
                "in": "path",
                "name": parametername,
                "required": True,
                "style": "simple",
                "explode": True,
                "schema": proplist_schema
            }
        insertparameters = [{
            "in": "path",
            "name": parametername,
            "required": True,
            "style": "simple",
            "explode": True,
            "schema": proplist_schema
        }]
        reqbody = False
        if 'required' in value:
            reqbody = True
        insertreqbody = {
            "required": reqbody,
            "content": {
                self.yaml_content: {
                    "schema": insertschema
                },
                self.json_content: {
                    "schema": insertschema
                }
            }
        }
        desc = 'insert {0} to a {1}'.format(propname,
                                            self.resourcedef['name'])
        openapiproplist = {
            'tags': [tagname],
            'description': desc,
            'operationId': (
                operationid +
                '_' +
                propname[:3] +
                '_put_' +
                self.version
            ),
            'parameters': insertparameters + parameters,
            'requestBody': insertreqbody,
            'responses': self.inresponses
        }
        self.openapi['paths'][newpath] = dict()
        self.openapi['paths'][newpath][
            'put'] = copy.deepcopy(openapiproplist)
        # remove
        desc = 'delete {0} from a {1}'.format(propname,
                                              self.resourcedef['name'])
        openapiproplist.pop('requestBody', None)
        openapiproplist['description'] = desc
        openapiproplist['operationId'] = (
            operationid +
            '_' +
            propname[:3] +
            '_delete_' +
            self.version
        )
        openapiproplist['responses'] = self.delresponses
        self.openapi['paths'][newpath][
            'delete'] = copy.deepcopy(openapiproplist)
        # replace
        replaceschema = {
            "type": "array",
            "items": {
                "$ref": (
                    "#/components/schemas/" +
                    propname
                )
            }
        }
        reqbody = {
            "required": propbodyreq,
            "content": {
                self.yaml_content: {
                    "schema": replaceschema
                },
                self.json_content: {
                    "schema": replaceschema
                }
            }
        }
        desc = 'replace {0} in a {1}'.format(propname,
                                             self.resourcedef['name'])
        openapiproplist['description'] = desc
        openapiproplist['operationId'] = operationid + '_put_' + self.version
        replacepath = basepath + '/' + propname
        openapiproplist['requestBody'] = reqbody
        openapiproplist['parameters'] = parameters
        openapiproplist['responses'] = self.inresponses
        self.openapi['paths'][replacepath] = dict()
        self.openapi['paths'][replacepath][
            'put'] = copy.deepcopy(openapiproplist)
        # patch
        openapiproplist['description'] = "bulk insert/remove part of resource"
        openapiproplist['operationId'] = operationid + '_patch'
        oplist = ["insert", "remove"]
        jsonpatchdoc = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "op": {
                        "type": "string",
                        "enum": oplist
                    },
                    "value": newschema
                }
            }
        }
        reqbody = {
            "required": True,
            "content": {
                self.yaml_content: {
                    "schema": jsonpatchdoc
                },
                self.json_content: {
                    "schema": jsonpatchdoc
                }
            }
        }
        openapiproplist['requestBody'] = reqbody
        # self.openapi['paths'][replacepath][
        #     'patch'] = copy.deepcopy(openapiproplist)
        for k in keys:
            if k not in itemval['properties']:
                msg = '%s -- is not defined in the properties: %s and %r'
                _LOG.error(msg, k, propname, itemval['properties'])
                self.error = 1
                return
            self.openapi['components']['schemas'][k] = itemval[
                'properties'][k]
            itemval['properties'].pop(k, None)
        reqlist = list()
        if 'required' in itemval:
            reqlist = itemval['required']
        self.findallpaths(itemval['properties'],
                          newpath,
                          operationid,
                          tagname,
                          parameters + insertparameters,
                          reqlist)

    def findallpaths_in_array(self,
                              propname,
                              parametername,
                              operationid,
                              parameters,
                              newpath,
                              basepath,
                              tagname,
                              propbodyreq):
        """
        Add all paths for array v3
        """
        # insert
        newschema = {
            "$ref": "#/components/schemas/" + propname
        }
        reqbody = {
            "required": True,
            "content": {
                self.yaml_content: {
                    "schema": newschema
                },
                self.json_content: {
                    "schema": newschema
                }
            }
        }
        if parametername not in (
                self.openapi['components'][
                    'parameters']
        ):
            self.openapi['components']["parameters"][parametername] = {
                "in": "path",
                "name": parametername,
                "required": True,
                "schema": newschema
            }
        insertparameters = [{
            "in": "path",
            "name": parametername,
            "required": True,
            "schema": newschema
        }]
        desc = 'insert {0} to a {1}'.format(propname,
                                            self.resourcedef['name'])
        openapiarray = {
            'tags': [tagname],
            'description': desc,
            'operationId': (
                operationid +
                '_' +
                propname[:3] +
                '_put_' +
                self.version
            ),
            'parameters': parameters + insertparameters,
            'responses': self.inresponses
        }
        self.openapi['paths'][
            newpath]['put'] = copy.deepcopy(openapiarray)
        # delete
        openapiarray["responses"] = self.delresponses
        openapiarray['operationId'] = (
            operationid +
            '_' +
            propname[:3] +
            '_delete_' +
            self.version
        )
        desc = 'delete {0} from a {1}'.format(propname,
                                              self.resourcedef['name'])
        openapiarray['description'] = desc
        self.openapi['paths'][newpath][
            'delete'] = copy.deepcopy(openapiarray)

        # replace
        newschema = {
            "type": "array",
            "items": {
                "$ref": (
                    "#/components/schemas/" +
                    propname
                )
            }
        }
        reqbody = {
            "required": propbodyreq,
            "content": {
                self.yaml_content: {
                    "schema": newschema
                },
                self.json_content: {
                    "schema": newschema
                }
            }
        }
        desc = 'replace {0} in a {1}'.format(propname,
                                             self.resourcedef['name'])
        openapiarray['operationId'] = operationid + '_put_' + self.version
        replacepath = basepath + '/' + propname
        self.openapi['paths'][replacepath] = dict()
        openapiarray['description'] = desc
        openapiarray['parameters'] = parameters
        openapiarray['requestBody'] = reqbody
        openapiarray["responses"] = self.inresponses
        self.openapi['paths'][replacepath][
            'put'] = copy.deepcopy(openapiarray)

        # patch
        openapiarray['description'] = "bulk insert/remove part of resource"
        openapiarray['operationId'] = operationid + '_patch'
        oplist = ["insert", "remove"]
        patchschema = {
            "$ref": "#/components/schemas/" + propname
        }
        jsonpatchdoc = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "op": {
                        "type": "string",
                        "enum": oplist
                    },
                    "value": patchschema
                }
            }
        }
        reqbody = {
            "required": True,
            "content": {
                self.yaml_content: {
                    "schema": jsonpatchdoc
                },
                self.json_content: {
                    "schema": jsonpatchdoc
                }
            }
        }
        openapiarray['requestBody'] = reqbody
        # self.openapi['paths'][replacepath][
        #    'patch'] = copy.deepcopy(openapiarray)

    # R0912: Too many branches (14/12)
    # pylint: disable=R0912
    def findallpaths(self, propdict,
                     basepath, opid, tagname,
                     parameters, requirelist):
        """
        Add extended paths v3
        """
        for propname, propvalue in propdict.items():
            if utils.check_property_name(propname, self.schemafile):
                self.error = 1
                continue
            propval = utils.resolve_reference(self.resolver,
                                              propname,
                                              propvalue,
                                              self.schemafile)
            if propval == 1:
                self.error = 1
                continue
            if utils.check_property_types(propname, propval, self.schemafile):
                self.error = 1
                continue
            propbodyreq = bool(requirelist and propname in requirelist)
            newpath = ""
            _combine_keywords = ['anyOf', 'allOf', 'oneOf', 'not']
            if 'type' not in propval and (
                    any(t in propval for t in _combine_keywords)
            ):
                self.openapi['components']['schemas'][propname] = propval
                newpath = basepath + '/' + propname
                self.openapi['paths'][newpath] = dict()
                operationid = opid + '_' + propname
                newschema = {
                    "$ref": "#/components/schemas/" + propname
                }
                reqbody = {
                    "required": propbodyreq,
                    "content": {
                        self.yaml_content: {
                            "schema": newschema
                        },
                        self.json_content: {
                            "schema": newschema
                        }
                    }
                }
                desc = 'replace {0} in a {1}'.format(
                    propname,
                    self.resourcedef['name'])
                openapibasic = {
                    'tags': [tagname],
                    'description': desc,
                    'operationId': operationid + '_put_' + self.version,
                    'parameters': parameters,
                    'responses': self.inresponses,
                    'requestBody': reqbody
                }
                self.openapi['paths'][
                    newpath]['put'] = copy.deepcopy(openapibasic)
                continue
            if 'enum' in propval or (
                    propval['type'] in [
                        'string', 'boolean', 'number', 'integer'
                    ]
            ):
                self.openapi['components']['schemas'][propname] = propval
                newpath = basepath + '/' + propname
                self.openapi['paths'][newpath] = dict()
                operationid = opid + '_' + propname
                newschema = {
                    "$ref": "#/components/schemas/" + propname
                }
                reqbody = {
                    "required": propbodyreq,
                    "content": {
                        self.yaml_content: {
                            "schema": newschema
                        },
                        self.json_content: {
                            "schema": newschema
                        }
                    }
                }
                desc = 'replace {0} in a {1}'.format(
                    propname,
                    self.resourcedef['name'])
                openapibasic = {
                    'tags': [tagname],
                    'description': desc,
                    'operationId': operationid + '_put_' + self.version,
                    'parameters': parameters,
                    'responses': self.inresponses,
                    'requestBody': reqbody
                }
                self.openapi['paths'][
                    newpath]['put'] = copy.deepcopy(openapibasic)
                continue
            if propval['type'] in ['object', 'mutablehash']:
                if utils.validate_object_field(
                        propname, propval, self.schemafile
                ):
                    self.error = 1
                    continue
            if propval['type'] in ['array']:
                if utils.validate_array_field(self.resolver,
                                              propname,
                                              propval,
                                              self.schemafile):
                    self.error = 1
                    continue
            if propval['type'] in ["propertylist"]:
                if utils.validate_propertylist_field(self.resolver,
                                                     propname,
                                                     propval,
                                                     self.schemafile):
                    self.error = 1
                    continue
            if propval['type'] in ['object']:
                newpath = basepath + '/' + propname
                self.openapi['paths'][newpath] = dict()
                operationid = opid + '_' + propname
                propertyval = utils.jsonschema_compat(propval)
                self.openapi['components']['schemas'][propname] = propertyval
                newschema = {
                    "$ref": "#/components/schemas/" + propname
                }
                reqbody = {
                    "required": propbodyreq,
                    "content": {
                        self.yaml_content: {
                            "schema": newschema
                        },
                        self.json_content: {
                            "schema": newschema
                        }
                    }
                }
                desc = 'replace {0} in a {1}'.format(
                    propname,
                    self.resourcedef['name'])
                openapibasic = {
                    'tags': [tagname],
                    'description': desc,
                    'operationId': operationid + '_put_' + self.version,
                    'parameters': parameters,
                    'responses': self.inresponses,
                    'requestBody': reqbody
                }
                self.openapi['paths'][
                    newpath]['put'] = copy.deepcopy(openapibasic)
            if propval['type'] in ["mutablehash", "propertylist", "array"]:
                if propval['type'] in ["propertylist"]:
                    partialpath = '{' + propname + '_keys}'
                    parametername = propname + '_keys'
                else:
                    partialpath = '{' + propname + '}'
                    parametername = propname
                newpath = basepath + '/' + propname + '/' + partialpath
                self.openapi['paths'][newpath] = dict()
                operationid = opid + '_' + propname
                propertyval = utils.jsonschema_compat(propval)
                if propval['type'] in ["propertylist", "array"]:
                    self.openapi['components']['schemas'][
                        propname] = propertyval['items']
                else:
                    self.openapi['components']['schemas'][
                        propname] = propertyval
            if propval['type'] in ['array']:
                self.findallpaths_in_array(propname,
                                           parametername,
                                           operationid,
                                           parameters,
                                           newpath,
                                           basepath,
                                           tagname,
                                           propbodyreq)
                continue
            if propval['type'] in ["propertylist"]:
                self.findallpaths_in_proplist(propname,
                                              propval,
                                              parametername,
                                              operationid,
                                              parameters,
                                              newpath,
                                              basepath,
                                              tagname,
                                              propbodyreq)
            if propval['type'] in ["mutablehash"]:
                self.findallpaths_in_mhash(propname,
                                           propval,
                                           parametername,
                                           operationid,
                                           parameters,
                                           newpath,
                                           basepath,
                                           tagname,
                                           opid,
                                           propbodyreq)
            if propval['type'] in ["object", "mutablehash"]:
                newpath = basepath + '/' + propname
                operationid = opid + '_' + propname
                objreqlist = list()
                if 'required' in propval:
                    objreqlist = propval['required']
                self.findallpaths(propval['properties'],
                                  newpath,
                                  operationid,
                                  tagname,
                                  parameters,
                                  objreqlist)
        return

    def add_rpcverbs(self):
        """
        Add paths for rpc verbs v3
        """
        error_flag = 0
        if "rpc" in self.resourcedef:
            if not isinstance(self.resourcedef['rpc'], list):
                msg = 'rpc field should be a list in schema %s'
                _LOG.error(msg, self.schemafile)
                error_flag = 1
                self.error = 1
                return error_flag
            tags = [self.resourcedef['name']]
            basepath = '/' + self.resourcedef['name']
            for rpcdef in self.resourcedef['rpc']:
                self.addrpcdef(rpcdef, tags, basepath)
        return error_flag

    def addrpcdef(self, rpcdef, tags, basepath):
        """
        Add rpc definition for v3
        """
        for verb, val in rpcdef.items():
            if utils.check_rpc_definition(verb, val, self.schemafile):
                self.error = 1
                continue
            newpath = basepath + ':' + verb
            parameters = []
            self.openapi['paths'][newpath] = dict()
            operationid = 'rpc_' + verb + '_' + self.version
            desc = 'rpc operation: {0}'.format(verb)
            reqbody = None
            bodyreq = False
            if val['request']:
                rpcrequest = utils.jsonschema_compat(val['request'])
                if 'required' in rpcrequest:
                    bodyreq = True
                if utils.check_jsonschema(rpcrequest, self.schemafile):
                    self.error = 1
                    continue
                reqbody = {
                    "required": bodyreq,
                    "content": {
                        self.yaml_content: {
                            "schema": rpcrequest
                        },
                        self.json_content: {
                            "schema": rpcrequest
                        }
                    }
                }
            rpcresponse = utils.jsonschema_compat(val['response'])
            if utils.check_jsonschema(rpcresponse, self.schemafile):
                self.error = 1
                continue
            responses = copy.deepcopy(
                utils.generate_default_response())
            responses['200'] = {
                "description": "OK",
                "content": {
                    self.yaml_content: {
                        'schema': rpcresponse
                    },
                    self.json_content: {
                        'schema': rpcresponse
                    }
                }
            }
            responses.update(copy.deepcopy(
                utils.generate_create_response()))
            rpcpost = {
                'tags': tags,
                'description': desc,
                'operationId': operationid,
                'parameters': parameters,
                'responses': responses
            }
            if reqbody:
                rpcpost['requestBody'] = reqbody
            self.openapi['paths'][newpath] = {'post': rpcpost}

    def write(self):
        """
        Write openapi spec to output file v3
        """
        # W0603(global-statement
        # pylint: disable=W0603
        if self.error:
            return
        if utils.validate_schema(self.openapi, self.schemafile):
            self.error = 1
            return
        if self.outfmt == 'yaml':
            with open(self.specfile, 'w') as outfile:
                yaml.dump(self.openapi, outfile, default_flow_style=False)
        if self.outfmt == 'json':
            with open(self.specfile, 'w') as outfile:
                _str = json.dumps(self.openapi,
                                  indent=4,
                                  sort_keys=True,
                                  ensure_ascii=False)
                outfile.write(_str)
        _LOG.info('Successfully created openapi spec file %s', self.specfile)
