"""
Script to create openapi spec from resource schema
"""
import argparse
import logging

from . import openapiconverter

_LOG = logging.getLogger(__name__)


def convert_to_openapispec():
    """
    convert resource schema to
    openapi 3.0 specification
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--basedir', required=True,
                        help='basedir of family')
    parser.add_argument('-l', '--lones', required=True,
                        help='comma separated resource names')
    parser.add_argument('--outfmt', required=False,
                        default='json',
                        help='yaml or json')
    parser.add_argument('--outdir', required=False,
                        help='output directory')
    parser.add_argument('--infile', required=False,
                        help='full path of schema file')
    parser.add_argument('-m', '--module', required=False,
                        help='Module used for creating spec')
    args = parser.parse_args()
    log_format = '[%(filename)s:%(lineno)d]' \
                 '[%(levelname)s]: %(message)s'
    logging.basicConfig(format=log_format,
                        level=logging.INFO)
    openapiconverter.main(args)
