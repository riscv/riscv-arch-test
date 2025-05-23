import sys
import os
from riscv_isac.log import logger
import riscv_isac.utils as utils
import riscv_isac.coverage as cov
from elftools.elf.elffile import ELFFile
import re
from ruamel.yaml import YAML
from ruamel import yaml

yaml = YAML(typ="rt")
yaml.default_flow_style = False
yaml.explicit_start = True
yaml.allow_unicode = True
yaml.allow_duplicate_keys = False

safe_yaml = YAML(typ="safe")
safe_yaml.default_flow_style = False
safe_yaml.explicit_start = True
safe_yaml.allow_unicode = True
safe_yaml.allow_duplicate_keys = False

def replace_values(obj, placeholder_data):
    if isinstance(obj, dict):
        updated_dict = {}
        for key, value in obj.items():
            new_key = replace_values(key, placeholder_data)
            new_value = replace_values(value, placeholder_data)
            updated_dict[new_key] = new_value
        return updated_dict
    elif isinstance(obj, list):
        updated_list = [replace_values(item, placeholder_data) for item in obj]
        return updated_list
    elif isinstance(obj, str):
        # Check if the string matches the pattern "${.*}"
        matches = re.findall(r'\${(.*?)}', obj)
        for match in matches:
            if match in placeholder_data:
                obj = obj.replace(f'${{{match}}}', str(placeholder_data[match]))
        return obj
    return obj

def preprocessing(cgf, header_file, cgf_macros):
    logger.info("Preprocessing")
    if header_file is not None:
        with open(header_file, "r") as file:
            from io import StringIO
            string_stream = StringIO()
            safe_yaml.dump(dict(safe_yaml.load(file)), string_stream)
            output_str = string_stream.getvalue()
            string_stream.close()
            placeholder_data = yaml.load(output_str)
            output_yaml = replace_values(cgf, placeholder_data['common'])
            for mac in cgf_macros:
                output_yaml = replace_values(output_yaml, placeholder_data[mac])
            return output_yaml
    else:
        return cgf

def isac(output_file,elf ,trace_file, window_size, cgf, parser_name, decoder_name, parser_path, decoder_path, detailed, test_labels,
        sig_labels, dump, cov_labels, xlen, flen, no_count, procs, *inxFlg, logging=False):
    test_addr = []
    sig_addr = []
    if parser_path:
        sys.path.append(parser_path)
    if decoder_path:
        sys.path.append(decoder_path)
    sys.path.append(os.path.join(os.path.dirname(__file__), "plugins"))

    if elf is not None :
        test_name = elf.rsplit('.', 1)[0]
        if test_labels:
            for startlabel,endlabel in test_labels:
                start_address = utils.collect_label_address(elf, startlabel)
                end_address = utils.collect_label_address(elf, endlabel)
                logger.info('Start Test Label: ' + startlabel + ' @ ' +
                        str(hex(start_address)))
                logger.info('End Test Label  : ' + endlabel + ' @ ' +
                        str(hex(end_address)))
                test_addr.append((start_address,end_address))
        if sig_labels:
            for startlabel,endlabel in sig_labels:
                start_address = utils.collect_label_address(elf, startlabel)
                end_address = utils.collect_label_address(elf, endlabel)
                logger.info('Start Signature Label: ' + startlabel + ' @ ' +
                        str(hex(start_address)))
                logger.info('End Signature Label  : ' + endlabel + ' @ ' +
                        str(hex(end_address)))
                sig_addr.append((start_address,end_address))
    else:
        test_name = trace_file.rsplit(',',1)[0]
    rpt = cov.compute(trace_file, test_name, cgf, parser_name, decoder_name, detailed, xlen, flen, test_addr, dump, cov_labels, sig_addr, window_size, inxFlg, elf, no_count, procs)
    if output_file is not None and logging:
        logger.info('Coverage Report:')
        #logger.info('\n\n' + rpt)
    else:
        rpt_file = open(output_file,'w')
        utils.dump_yaml(rpt, rpt_file)
        rpt_file.close()
        logger.info('Report File Generated : ' + str(output_file))
