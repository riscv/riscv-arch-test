# See LICENSE.incore for details

"""Common Utils """
import io
import sys
import os
import subprocess
import shlex
import riscv_isac
from riscv_isac.log import logger
import ruamel
from ruamel.yaml import YAML
from ruamel.yaml.representer import RoundTripRepresenter,SafeRepresenter
import yaml as pyyaml
from elftools.elf.elffile import ELFFile

def create_yaml(typ="rt", indent=None, block_seq_indent=None):
    yaml = YAML(typ=typ)
    yaml.default_flow_style = False
    yaml.explicit_start = True
    yaml.allow_unicode = True
    yaml.allow_duplicate_keys = False
    if indent is not None:
        yaml.indent = indent
    if block_seq_indent is not None:
        yaml.block_seq_indent = block_seq_indent
    return yaml

yaml = create_yaml()

safe_yaml = create_yaml(typ="safe")

def collect_label_address(elf, label):
    with open(elf, 'rb') as f:
        elffile = ELFFile(f)
        # elfclass is a public attribute of ELFFile, read from its header
        symtab = elffile.get_section_by_name('.symtab')
        size = symtab.num_symbols()
        mains = symtab.get_symbol_by_name(label)
        main = mains[0]
    return int(main.entry['st_value'])

def get_value_at_location(elf_path, location, bytes):
    with open(elf_path, 'rb') as f:
        elffile = ELFFile(f)
        # Iterate through the sections to find the relevant one (or use a specific section by name)
        for section in elffile.iter_sections():
            if section['sh_addr'] <= location < section['sh_addr'] + section.data_size:
                offset = location - section['sh_addr']
                f.seek(section['sh_offset'] + offset)
                value = f.read(bytes)  # Assuming a 32-bit value, adjust if different
                return int.from_bytes(value, byteorder='little', signed=False)
    return None

def dump_yaml(foo, outfile=None, indent=None, block_seq_indent=None):
    """
    Dump yaml to outfile. If outfile is None, dump to string. If indent or
    block_seq_indent is set, create a new yaml object with such config.
    """
    # Create a default yaml object if no custom settings are provided
    yaml = create_yaml() if indent is None and block_seq_indent is None else create_yaml(indent=indent, block_seq_indent=block_seq_indent)

    if outfile is None:
        buf = io.StringIO()
        yaml.width = 1000
        yaml.dump(foo, buf)
        return buf.getvalue()
    return yaml.dump(foo, outfile)

def create_yaml(indent=None, block_seq_indent=None):
    yaml = ruamel.yaml.YAML()
    if indent is not None:
        yaml.indent = indent
    if block_seq_indent is not None:
        yaml.block_seq_indent = block_seq_indent
    return yaml

def load_yaml_file(foo):
    try:
        with open(foo, "r") as file:
            return yaml.load(file)
    except ruamel.yaml.constructor.DuplicateKeyError as msg:
        logger = logging.getLogger(__name__)
        error = "\n".join(str(msg).split("\n")[2:-7])
        logger.error(error)
        raise SystemExit

class makeUtil():
    """
    Utility for ease of use of make commands like `make` and `pmake`.
    Supports automatic addition and execution of targets. Uses the class
    :py:class:`shellCommand` to execute commands.
    """
    def __init__(self,makeCommand='make',makefilePath="./Makefile"):
        """ Constructor.

        :param makeCommand: The variant of make to be used with optional arguments.
            Ex - `pmake -j 8`

        :type makeCommand: str

        :param makefilePath: The path to the makefile to be used.

        :type makefilePath: str

        """
        self.makeCommand=makeCommand
        self.makefilePath = makefilePath
        self.targets = []
    def add_target(self,command,tname=""):
        """
        Function to add a target to the makefile.

        :param command: The command to be executed when the target is run.

        :type command: str

        :param tname: The name of the target to be used. If not specified, TARGET<num> is used as the name.

        :type tname: str
        """
        if tname == "":
            tname = "TARGET"+str(len(self.targets))
        with open(self.makefilePath,"a") as makefile:
            makefile.write("\n\n.PHONY : " + tname + "\n" + tname + " :\n\t"+command.replace("\n","\n\t"))
            self.targets.append(tname)
    def execute_target(self,tname,cwd="./"):
        """
        Function to execute a particular target only.

        :param tname: Name of the target to execute.

        :type tname: str

        :param cwd: The working directory to be set while executing the make command.

        :type cwd: str

        :raise AssertionError: If target name is not present in the list of defined targets.

        """
        assert tname in self.targets, "Target does not exist."
        shellCommand(self.makeCommand+" -f "+self.makefilePath+" "+tname).run(cwd=cwd)
    def execute_all(self,cwd):
        """
        Function to execute all the defined targets.

        :param cwd: The working directory to be set while executing the make command.

        :type cwd: str

        """
        shellCommand(self.makeCommand+" -f "+self.makefilePath+" "+" ".join(self.targets)).run(cwd=cwd)

class combineReader(object):
    def __init__(self, file_names):
        self._to_do = list(file_names[:])
        self._fp = None

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        if self._fp:
            self._fp.close()

    def read(self, size=None):
        res = ''
        while True:
            if self._fp is None:
                if not self._to_do:
                    return res
                else:
                    self._fp = open(self._to_do.pop(0))
            if size is None:
                data = self._fp.read()
            else:
                data = self._fp.read(size)
            if size is None or not data:
                self._fp.close()
                self._fp = None
            res += data
            if size is None:
                continue
            size -= len(data)
            if size == 0:
                break
        return res

def load_cgf(files):
    with combineReader(files) as fp:
        # Intermediate fix for no aliasing in output cgf.
        # Load in safe mode, dump to string and load in
        # rt mode to support comments.
        # TODO: Find a better way of doing this by
        # overloading functions from the original library
        # representers.
        from io import StringIO
        string_stream = StringIO()
        safe_yaml.dump(dict(safe_yaml.load(fp)),string_stream)
        output_str = string_stream.getvalue()
        string_stream.close()
        return yaml.load(output_str)

class Command():
    """
    Class for command build which is supported
    by :py:mod:`suprocess` module. Supports automatic
    conversion of :py:class:`pathlib.Path` instances to
    valid format for :py:mod:`subprocess` functions.
    """

    def __init__(self, *args, pathstyle='auto', ensure_absolute_paths=False):
        """Constructor.

        :param pathstyle: Determine the path style when adding instance of
            :py:class:`pathlib.Path`. Path style determines the slash type
            which separates the path components. If pathstyle is `auto`, then
            on Windows backslashes are used and on Linux forward slashes are used.
            When backslashes should be prevented on all systems, the pathstyle
            should be `posix`. No other values are allowed.

        :param ensure_absolute_paths: If true, then any passed path will be
            converted to absolute path.

        :param args: Initial command.

        :type pathstyle: str

        :type ensure_absolute_paths: bool
        """
        self.ensure_absolute_paths = ensure_absolute_paths
        self.pathstyle = pathstyle
        self.args = []

        for arg in args:
            self.append(arg)

    def append(self, arg):
        """Add new argument to command.

        :param arg: Argument to be added. It may be list, tuple,
            :py:class:`Command` instance or any instance which
            supports :py:func:`str`.
        """
        to_add = []
        if type(arg) is list:
            to_add = arg
        elif type(arg) is tuple:
            to_add = list(arg)
        elif isinstance(arg, type(self)):
            to_add = arg.args
        elif isinstance(arg, str) and not self._is_shell_command():
            to_add = shlex.split(arg)
        else:
            # any object which will be converted into str.
            to_add.append(arg)

        # Convert all arguments to its string representation.
        # pathlib.Path instances
        to_add = [
            self._path2str(el) if isinstance(el, pathlib.Path) else str(el)
            for el in to_add
        ]
        self.args.extend(to_add)

    def clear(self):
        """Clear arguments."""
        self.args = []

    def run(self, **kwargs):
        """Execute the current command.

        Uses :py:class:`subprocess.Popen` to execute the command.

        :return: The return code of the process     .
        :raise subprocess.CalledProcessError: If `check` is set
                to true in `kwargs` and the process returns
                non-zero value.
        """
        kwargs.setdefault('shell', self._is_shell_command())
        cwd = self._path2str(kwargs.get(
            'cwd')) if not kwargs.get('cwd') is None else self._path2str(
                os.getcwd())
        kwargs.update({'cwd': cwd})
        logger.debug(cwd)
        # When running as shell command, subprocess expects
        # The arguments to be string.
        logger.debug(str(self))
        cmd = str(self) if kwargs['shell'] else self
        x = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             **kwargs)
        out, err = x.communicate()
        out = out.rstrip()
        err = err.rstrip()
        if x.returncode != 0:
            if out:
                logger.error(out.decode("ascii"))
            if err:
                logger.error(err.decode("ascii"))
        else:
            if out:
                logger.warning(out.decode("ascii"))
            if err:
                logger.warning(err.decode("ascii"))
        return x.returncode

    def _is_shell_command(self):
        """
        Return true if current command is supposed to be executed
        as shell script otherwise false.
        """
        return any('|' in arg for arg in self.args)

    def _path2str(self, path):
        """Convert :py:class:`pathlib.Path` to string.

        The final form of the string is determined by the
        configuration of `Command` instance.

        :param path: Path-like object which will be converted
                     into string.
        :return: String representation of `path`
        """
        path = pathlib.Path(path)
        if self.ensure_absolute_paths and not path.is_absolute():
            path = path.resolve()

        if self.pathstyle == 'posix':
            return path.as_posix()
        elif self.pathstyle == 'auto':
            return str(path)
        else:
            raise ValueError(f"Invalid pathstyle {self.pathstyle}")

    def __add__(self, other):
        cmd = Command(self,
                      pathstyle=self.pathstyle,
                      ensure_absolute_paths=self.ensure_absolute_paths)
        cmd += other
        return cmd

    def __iadd__(self, other):
        self.append(other)
        return self

    def __iter__(self):
        """
        Support iteration so functions from :py:mod:`subprocess` module
        support `Command` instance.
        """
        return iter(self.args)

    def __repr__(self):
        return f'<{self.__class__.__name__} args={self.args}>'

    def __str__(self):
        return ' '.join(self.args)

class shellCommand(Command):
    """
        Sub Class of the command class which always executes commands as shell commands.
    """

    def __init__(self, *args, pathstyle='auto', ensure_absolute_paths=False):
        """
        :param pathstyle: Determine the path style when adding instance of
            :py:class:`pathlib.Path`. Path style determines the slash type
            which separates the path components. If pathstyle is `auto`, then
            on Windows backslashes are used and on Linux forward slashes are used.
            When backslashes should be prevented on all systems, the pathstyle
            should be `posix`. No other values are allowed.

        :param ensure_absolute_paths: If true, then any passed path will be
            converted to absolute path.

        :param args: Initial command.

        :type pathstyle: str

        :type ensure_absolute_paths: bool

        """
        return super().__init__(*args,
                                pathstyle=pathstyle,
                                ensure_absolute_paths=ensure_absolute_paths)

    def _is_shell_command(self):
        return True

def sys_command(command):
    logger.warning('$ {0} '.format(' '.join(shlex.split(command))))
    x = subprocess.Popen(shlex.split(command),
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         )
    try:
        out, err = x.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        x.kill()
        out, err = x.communicate()

    out = out.rstrip()
    err = err.rstrip()
    if x.returncode != 0:
        if out:
            logger.error(out.decode("ascii"))
        if err:
            logger.error(err.decode("ascii"))
    else:
        if out:
            logger.debug(out.decode("ascii"))
        if err:
            logger.debug(err.decode("ascii"))
    return out.decode("ascii")

def sys_command_file(command, filename):
    cmd = command.split(' ')
    cmd = [x.strip(' ') for x in cmd]
    cmd = [i for i in cmd if i]
    logger.debug('{0} > {1}'.format(' '.join(cmd), filename))
    fp = open(filename, 'w')
    out = subprocess.Popen(cmd, stdout=fp, stderr=fp)
    stdout, stderr = out.communicate()
    fp.close()

def import_instr_alias(alias):
    '''
    Return instructions pertaining to a particular alias

    alias:  (string) The alias to be imported

    '''

    # Function to flatten nested lists
    from collections import Iterable
    def flatten(lis):
        for item in lis:
            if isinstance(item, Iterable) and not isinstance(item, str):
                for x in flatten(item):
                    yield x
            else:        
                yield item
    
    isac_path = os.path.dirname(riscv_isac.__file__)
    alias_dict = load_yaml_file(isac_path + '/data/instr_alias.yaml')
    if alias in alias_dict:
        return list(flatten(alias_dict[alias]))
    else:
        return None

