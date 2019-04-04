"""
create openapi spec from resource schema
"""
import copy
import errno
import imp
import logging
import os
import re
import sys

import yaml
from . import openapiv3
from . import utils

_LOG = logging.getLogger(__name__)
_EXIT_STATUS = 0


def load_class_from_module(modulefile, major_version):
    """
    Load module file
    """
    openapispec_class = None
    modulebasepath = os.path.dirname(modulefile)
    sys.path.append(modulebasepath)
    inputmodule = os.path.splitext(modulefile)[0]
    modulename = os.path.basename(inputmodule)
    regex = re.compile(r'^openapi(v[0-9]+)$')
    result = regex.match(modulename)
    module_version = result.groups()[0]
    if major_version == module_version:
        modulespec = imp.find_module(modulename)
        module = imp.load_module(modulename, *modulespec)
        classname = 'Version' + module_version.upper()
        openapispec_class = getattr(module, classname)
    return openapispec_class


def main(args):
    """
    Main function
    """
    openapiglobal = dict()
    family = utils.get_family(args.basedir)
    openapiglobal['servers'] = [
        {"url": "/" + family, "description": family}]
    openapiglobal['openapi'] = '3.0.0'
    openapiglobal['tags'] = list()
    openapiglobal['paths'] = dict()
    openapiglobal['components'] = dict()
    openapiglobal['components']['schemas'] = dict()
    info = dict()
    openapiglobal['info'] = info
    if args.infile and not args.outdir:
        sys.exit('Enter infile and outdir')
    if args.outdir:
        openapidir = args.outdir
    else:
        openapidir = os.path.join(args.basedir, 'apischemas', 'openapi')
        try:
            os.makedirs(openapidir)
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise
    utils.dump_file_to_openapidir(args.basedir, openapidir, args.infile)
    if args.infile:
        openapi = dict()
        openapi = copy.deepcopy(openapiglobal)
        create_openapi_spec(openapi,
                            args.infile,
                            openapidir,
                            family,
                            args.outfmt,
                            args.module)
        return
    schemadir = os.path.join(args.basedir, 'apischemas', 'rschemas')
    lones_list = args.lones.split(',')
    for lone in lones_list:
        schemafile = os.path.join(schemadir, lone)
        if os.path.isfile(schemafile):
            openapi = dict()
            openapi = copy.deepcopy(openapiglobal)
            create_openapi_spec(openapi,
                                schemafile,
                                openapidir,
                                family,
                                args.outfmt,
                                args.module)
        else:
            _LOG.error('%s -- Resource does not exist', lone)
            # W0603(global-statement
            # pylint: disable=W0603
            global _EXIT_STATUS
            _EXIT_STATUS = 1
    sys.exit(_EXIT_STATUS)


def create_openapi_spec(openapi, schemafile, openapidir,
                        family, outfmt, inputmodule=None):
    """
    Create openapi spec for each lone
    """
    schema = open(schemafile).read()
    try:
        value = yaml.load(schema)
    except yaml.YAMLError as err:
        sys.exit("Yaml Error in {0}: {1}".format(schemafile, err))
    if 'rpconly' in value and value['rpconly']:
        utils.check_rpconlybasic_fields(value, schemafile)
    else:
        utils.check_basic_fields(value, schemafile)
    extfamily = '_'.join(family.split('/'))
    mimetype = utils.create_mime_type(value, extfamily)
    version = '_'.join(mimetype.split('.')[-3::])
    major_version = mimetype.split('.')[-3]

    # get tag
    openapi['tags'].append(
        {
            'name': value['name'],
            'description': value['description']
        }
    )
    openapi['info'] = {
        'version': value['version'],
        'title': value['name'],
        'description': 'openapi spec for this resource'
    }
    specfile = os.path.join(openapidir, mimetype)
    # W0603(global-statement
    # pylint: disable=W0603
    global _EXIT_STATUS
    if major_version == 'v3':
        v3specobj = openapiv3.VersionV3(openapi,
                                        specfile,
                                        value,
                                        outfmt,
                                        mimetype,
                                        version,
                                        schemafile,
                                        openapidir)
        v3specobj.create_spec()
        v3specobj.write()
        if v3specobj.error:
            _EXIT_STATUS = 1
    elif inputmodule:
        specclass = load_class_from_module(inputmodule, major_version)
        if specclass:
            specobj = specclass(openapi,
                                specfile,
                                value,
                                outfmt,
                                mimetype,
                                version,
                                schemafile,
                                openapidir)
            specobj.create_spec()
            specobj.write()
            if specobj.error:
                _EXIT_STATUS = 1
    else:
        msg = '{0} is not supported'.format(major_version)
        sys.exit(msg)
