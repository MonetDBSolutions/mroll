import os
from os.path import expanduser

HOME = expanduser("~")
SYS_CONFIG = os.path.join(HOME, '.config')
MROLL_CONFIG_DIR = os.path.join(SYS_CONFIG, 'mroll')
MROLL_CONFIG_FILE = os.path.join(MROLL_CONFIG_DIR, 'config.ini')

class Config:
    work_dir = None

    @classmethod
    def from_file(cls, configfile):
        if not os.path.exists(configfile):
            raise RuntimeError('Error: No config file found in \'{}\'. Run setup command first!'.format(MROLL_CONFIG_DIR))
        import configparser
        config = configparser.ConfigParser()
        config.read(configfile)
        mroll_confi_map = config['mroll']
        conf = cls.__new__(cls)
        for k in mroll_confi_map:
            setattr(conf, k, mroll_confi_map[k])
        return conf
