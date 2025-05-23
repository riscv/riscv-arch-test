# See LICENSE.incore for details
"""Console script for riscv_isac."""

import os
import click
import shutil
from git import Repo

from riscv_isac.isac import isac
from riscv_isac.isac import preprocessing
from riscv_isac.__init__ import __version__
from riscv_isac.log import logger
import riscv_isac.utils as utils
from riscv_isac.cgf_normalize import *
import riscv_isac.coverage as cov
from riscv_isac.plugins.translator_cgf import Translate_cgf

@click.group()
@click.version_option(prog_name="RISC-V ISA Coverage Generator",version=__version__)
@click.option('--verbose', '-v', default='info', help='Set verbose level', type=click.Choice(['info','error','debug'],case_sensitive=False))
def cli(verbose):
    logger.level(verbose)
    logger.info('****** RISC-V ISA Coverage {0} *******'.format(__version__ ))
    logger.info('Copyright (c) 2020, InCore Semiconductors Pvt. Ltd.')
    logger.info('All Rights Reserved.')

@cli.command(help = "Run Coverage analysis on tracefile.")
@click.option('--elf', '-e' , type=click.Path(exists=True,resolve_path=True),help="ELF file")
@click.option(
        '--trace-file','-t',
        type=click.Path(resolve_path=True,readable=True,exists=True),
        help="Instruction trace file to be analyzed"
    )

@click.option(
        '--header-file','-h',
        type=click.Path(resolve_path=True,readable=True,exists=True),
        help="YAML macro file to include"
    )
@click.option(
        '--cgf-macro','-cm',
        metavar='CGF MACROS',
        type=str,
        multiple=True,
        help = "CGF macros to consider for this run."
)
@click.option(
        '--window-size',
        type= int,
        default = 32,
        help="Maximum length of instructions to be evaluated for checking hazards"
    )
@click.option(
        '--cgf-file','-c',multiple=True,
        type=click.Path(resolve_path=True,readable=True,exists=True),
        help="Coverage Group File(s). Multiple allowed.",required=True
    )
@click.option(
        '--detailed', '-d',
        is_flag=True,
        help='Select detailed mode of  coverage printing')

@click.option(
        '--parser-name',
        type = str,
        default = 'c_sail',
        metavar = 'NAME',
        help='Parser plugin name'
    )

@click.option(
        '--decoder-name',
        type = str,
        default = 'internaldecoder',
        metavar = 'NAME',
        help = 'Decoder plugin name'
    )

@click.option(
        '--parser-path',
        type=click.Path(resolve_path=True,readable=True,exists=True),
        help="Parser file path"
    )

@click.option(
        '--decoder-path',
        type=click.Path(resolve_path=True,readable=True,exists=True),
        help="Decoder file path"
    )

@click.option(
        '--output-file','-o',
        type=click.Path(writable=True,resolve_path=True),
        help="Coverage Group File",
        required=True
    )
@click.option(
        '--test-label',
        type=(str,str),
        multiple=True,
        metavar='LABEL_START LABEL_END',
        default=None,
        help='Pair of labels denoting start and end points of the test region(s). Multiple allowed.'
    )
@click.option(
        '--sig-label',
        type=(str,str),
        multiple=True,
        metavar='LABEL_START LABEL_END',
        default=None,
        help='Pair of labels denoting start and end points of the signature region(s). Multiple allowed.'
    )
@click.option(
        '--dump',
        type=click.Path(writable=True,resolve_path=True),
        help="Dump Normalized Coverage Group File"
    )
@click.option(
        '--cov-label','-l',
        metavar='COVERAGE LABEL',
        type=str,
        multiple=True,
        help = "Coverage labels to consider for this run."
)
@click.option('--xlen','-x',
        type=click.Choice(['32','64']),
        default='32',
        help="XLEN value for the ISA."
)
@click.option('--flen','-f',
        type=click.Choice(['32','64']),
        default='32',
        help="FLEN value for the ISA."
)
@click.option('--no-count',
        is_flag = True,
        help = "This option removes hit coverpoints during coverage computation"
)
@click.option('--procs', '-p',
        default = 1,
        help = 'Set number of processes to calculate coverage'
)
@click.option('--log-redundant',
        is_flag = True,
        help = "Log redundant coverpoints during normalization"
)
@click.option('--inxFlg', 'inxFlg',
        type=bool, 
        default = False, 
        help="Enable inxFlg if the extension is Z*inx"
)

def coverage(elf,trace_file, header_file, window_size, cgf_file, detailed,parser_name, decoder_name, parser_path, decoder_path,output_file, test_label,
        sig_label, dump,cov_label, cgf_macro, xlen, flen, no_count, procs, log_redundant, inxFlg):  
    isac(output_file,elf,trace_file, window_size, preprocessing(Translate_cgf(expand_cgf(cgf_file,int(xlen),int(flen),log_redundant)), header_file, cgf_macro), parser_name, decoder_name, parser_path, decoder_path, detailed, test_label,
            sig_label, dump, cov_label, int(xlen), int(flen), no_count, procs, inxFlg, logging=False)

@cli.command(help = "Merge given coverage files.")
@click.argument(
        'files',
        type=click.Path(resolve_path=True,readable=True,exists=True),
        nargs=-1
        )
@click.option(
        '--detailed', '-d',
        is_flag=True,
        help='Select detailed mode of  coverage printing')
@click.option(
        '-p',
        type = int,
        default = 1,
        help='Number of processes'
        )
@click.option(
        '--cgf-file','-c',multiple=True,
        type=click.Path(resolve_path=True,readable=True,exists=True),
        help="Coverage Group File(s). Multiple allowed.",required=True
    )
@click.option(
        '--output-file','-o',
        type=click.Path(writable=True,resolve_path=True),
        help="Coverage Group File."
    )
@click.option('--flen','-f',
        type=click.Choice(['32','64']),
        default='32',
        help="FLEN value for the ISA."
)
@click.option('--xlen','-x',type=click.Choice(['32','64']),default='32',help="XLEN value for the ISA.")
@click.option('--log-redundant',
        is_flag = True,
        help = "Log redundant coverpoints during normalization"
)
def merge(files,detailed,p,cgf_file,output_file,flen,xlen,log_redundant, header_file,cgf_macro):
    rpt = cov.merge_coverage(
            files,preprocessing(Translate_cgf(expand_cgf(cgf_file,int(xlen),int(flen),log_redundant)), header_file, cgf_macro),detailed,p)
    if output_file is None:
        logger.info('Coverage Report:')
        logger.info('\n\n' + rpt)
    else:
        rpt_file = open(output_file,'w')
        utils.dump_yaml(rpt,rpt_file)
        rpt_file.close()
        logger.info('Report File Generated : ' + str(output_file))



@cli.command(help = "Normalize the cgf.")
@click.option(
        '--cgf-file','-c',multiple=True,
        type=click.Path(resolve_path=True,readable=True,exists=True),
        help="Coverage Group File(s). Multiple allowed.",required=True
    )
@click.option(
        '--output-file','-o',
        type=click.Path(writable=True,resolve_path=True),
        help="Coverage Group File",
        required = True
    )
@click.option('--xlen','-x',type=click.Choice(['32','64']),default='32',help="XLEN value for the ISA.")
@click.option('--flen','-f',type=click.Choice(['32','64']),default='32',help="FLEN value for the ISA.")
@click.option('--log-redundant',
        is_flag = True,
        help = "Log redundant coverpoints during normalization"
)
def normalize(cgf_file,output_file,xlen,flen,log_redundant,header_file,cgf_macro):
    logger.info("Writing normalized CGF to "+str(output_file))
    with open(output_file,"w") as outfile:
        utils.dump_yaml(preprocessing(Translate_cgf(expand_cgf(cgf_file,int(xlen),int(flen),log_redundant)), header_file, cgf_macro),outfile)

@cli.command(help = 'Setup the plugin which uses the information from RISCV Opcodes repository to decode.')
@click.option('--url',
                type = str,
                default='https://github.com/riscv/riscv-opcodes',
                required=False,
                help='URL to the riscv-opcodes repo')
@click.option('--branch',type=str,default='master')
@click.option('--plugin-path',
                type=click.Path(resolve_path=True,writable=True),
                help="Target folder to setup the plugin files in. [./]",
                default="./rvop_decoder")
@click.option("--rvop-path",
                type=click.Path(resolve_path=True,writable=True),
                help="Path to RVOpcodes directory.")
# Clone repo
def setup(url,branch, plugin_path, rvop_path):
    # path = os.getcwd() + '/plugins/riscv_opcodes/'
    if not os.path.exists(plugin_path):
        logger.debug("Creating directory: "+str(plugin_path))
        os.mkdir(plugin_path)
    target_dir = os.path.join(plugin_path,"riscv_opcodes/")
    repo = None
    if rvop_path is not None:
        if not os.path.exists(rvop_path):
            logger.warning("RISCV Opcodes folder not found at: "+rvop_path)
            clone = click.prompt("Do you wish to clone from git?",
                        default='Y',type=click.Choice(['Y','n','y','N']),show_choices=True)
            if clone == 'Y' or clone == 'y':
                logger.debug("Cloning from Git.")
                repo = Repo.clone_from(url, rvop_path)
                repo.git.checkout(branch)
            else:
                logger.error("Exiting Setup.")
                raise SystemExit
        os.symlink(rvop_path,target_dir[:-1])
    else:
        logger.debug("Cloning from Git.")
        repo = Repo.clone_from(url, target_dir)
        repo.git.checkout(branch)
    plugin_file = os.path.join(os.path.dirname(__file__), "data/rvopcodesdecoder.py")
    constants_file = os.path.join(os.path.dirname(__file__), "data/constants.py")
    logger.debug("Copying plugin files.")
    shutil.copy(plugin_file,plugin_path)
    shutil.copy(constants_file,plugin_path)
