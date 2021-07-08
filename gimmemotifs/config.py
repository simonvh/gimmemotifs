# Copyright (c) 2009-2019 Simon van Heeringen <simon.vanheeringen@gmail.com>
#
# This module is free software. You can redistribute it and/or modify it under
# the terms of the MIT License, see the file COPYING included with this
# distribution.
""" Configuration for GimmeMotifs """
import configparser
import sysconfig
import glob
import sys
import xdg
import os
import pathlib
import logging
import pkg_resources
import inspect
from gimmemotifs.shutils import which

logger = logging.getLogger("gimme.config")

# CONSTANTS #
BG_TYPES = ["random", "genomic", "gc", "promoter"]
FA_VALID_BGS = ["random", "promoter", "gc", "custom", "genomic"]
BED_VALID_BGS = ["random", "genomic", "gc", "promoter", "custom"]
BG_RANK = {"custom": 1, "promoter": 2, "gc": 3, "random": 4, "genomic": 5}
FASTA_EXT = [".fasta", ".fa", ".fsa"]
DIRECT_NAME = "direct"
INDIRECT_NAME = "indirect\nor predicted"

CACHE_DIR = os.path.join(xdg.XDG_CACHE_HOME, "gimmemotifs")
CONFIG_DIR = os.path.join(xdg.XDG_CONFIG_HOME, "gimmemotifs")

MOTIF_CLASSES = [
    "MDmodule",
    "MEME",
    "MEMEW",
    "DREME",
    "Weeder",
    "GADEM",
    "MotifSampler",
    "Trawler",
    "Improbizer",
    "BioProspector",
    "Posmo",
    "ChIPMunk",
    "AMD",
    "HMS",
    "Homer",
    "XXmotif",
    "ProSampler",
    "Yamda",
    "DiNAMO",
    "RPMCMC",
]


class MotifConfig(object):
    """Configuration object for the gimmemotifs module."""

    __shared_state = {}

    prefix = sysconfig.get_config_var("prefix")

    # Default config that is installed with GimmeMotifs
    default_config = pkg_resources.resource_filename(
        "gimmemotifs", "../data/cfg/gimmemotifs.default.cfg"
    )

    #
    package_dir = os.path.dirname(
        os.path.abspath(inspect.getfile(inspect.currentframe()))
    )

    user_config = os.path.join(CONFIG_DIR, "gimmemotifs.cfg")

    config_dir = "share/gimmemotifs/gimmemotifs.cfg"
    configs = [user_config]
    config = None
    TOOL_SECTION = "tools"

    def __init__(self, use_config=""):
        self.__dict__ = self.__shared_state
        if use_config:
            self.config = configparser.ConfigParser()
            cfg = self.config.read(use_config)
        elif not self.config:
            self.config = configparser.ConfigParser()
            cfg = self.config.read(self.configs)
            if not cfg:
                logger.info("No config found.")
                self.create_default_config()
                cfg = self.config.read(self.configs)
            if not cfg:
                raise ValueError("Configuration file not found," "could not create it!")

        self._upgrade_config()

    def _upgrade_config(self, config_fname=None):
        if "width" in self.config["params"]:
            if "size" not in self.config["params"]:
                self.config.set(
                    option="size",
                    section="params",
                    value=self.config["params"]["width"],
                )
            del self.config["params"]["width"]
        if "lwidth" in self.config["params"]:
            if "lsize" not in self.config["params"]:
                self.config.set(
                    option="lsize",
                    section="params",
                    value=self.config["params"]["lwidth"],
                )
            del self.config["params"]["lwidth"]

        if config_fname is None or not config_fname:
            config_fname = self.configs[0]
        with open(config_fname, "w") as f:
            self.write(f)

    def create_default_config(self):
        logger.info("Creating new config.")

        available_tools = []
        self.config.read(self.default_config)
        for m in MOTIF_CLASSES:
            try:
                exe = self.config.get(m, "bin")
                mdir = self.config.get(m, "dir")
                tool_dir = os.path.join(self.package_dir, mdir)
                cmd = os.path.join(tool_dir, exe)
                if which(cmd):
                    logger.info("Using included version of %s.", m)
                    available_tools.append(m)
                else:
                    cmd = which(exe)
                    if cmd:
                        logger.info("Using system version of %s.", m)
                        self.set_program(m, {"bin": cmd, "dir": os.path.dirname(cmd)})
                        available_tools.append(m)
                    else:
                        logger.warn(
                            "%s not found. To include it you will have to install it.",
                            m,
                        )

            except configparser.NoSectionError:
                logger.warn("{} not in config".format(m))

        params = self.get_default_params()
        params["available_tools"] = ",".join(available_tools)
        self.set_default_params(params)

        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(self.user_config, "w") as f:
            self.config.write(f)
        logger.info("Configuration file: %s", self.user_config)

    def bin(self, program):
        try:
            exe_base = self.config.get(program, "bin")
            if not os.path.exists(exe_base):
                mdir = self.config.get(program, "dir")
                build_dir = next(
                    iter(glob.glob(f"build/lib*{sys.version[:3]}/gimmemotifs")), ""
                )
                dirs = [
                    mdir,
                    os.path.join(self.package_dir, mdir),
                    os.path.join(build_dir, mdir),
                ]
                for bla in dirs:
                    exe = os.path.join(bla, exe_base)
                    if os.path.exists(exe):
                        return os.path.abspath(exe)

        except Exception:
            raise ValueError("No configuration found for %s" % program)
        return exe_base

    def set_default_params(self, params):
        if not self.config.has_section("params"):
            self.config.add_section("params")

        for k, v in params.items():
            self.config.set("params", k, str(v))

    def get_default_params(self):
        d = dict(self.config.items("params"))
        for k in ["use_strand", "use_cache"]:
            d[k] = self.config.getboolean("params", k)

        if "size" not in d:
            d["size"] = d["width"]
        return d

    def dir(self, program):
        if self.config.has_section(program):
            if self.config.has_option(program, "dir"):
                try:
                    mdir = self.config.get(program, "dir")
                    build_dir = next(
                        iter(glob.glob(f"build/lib*{sys.version[:3]}/gimmemotifs")), ""
                    )
                    dirs = [
                        mdir,
                        os.path.join(self.package_dir, mdir),
                        os.path.join(build_dir, mdir),
                    ]
                    for mdir in dirs:
                        if os.path.exists(mdir):
                            return mdir
                except Exception:
                    return None
            else:
                return os.path.dirname(self.bin(program))
        else:
            raise ValueError("No configuration found for %s" % program)

    def set_program(self, program, d):
        if not self.config.has_section(program):
            self.config.add_section(program)

        for par, value in d.items():
            self.config.set(program, par, value)

    def get_data_dir(self, ddir):
        my_dir = self.config.get("main", ddir)
        if not os.path.exists(my_dir):
            my_dir = pkg_resources.resource_filename(
                "gimmemotifs", os.path.join("../data", my_dir)
            )
        return my_dir

    def set_template_dir(self, path):
        if not self.config.has_section("main"):
            self.config.add_section("main")
        self.config.set("main", "template_dir", path)

    def get_template_dir(self):
        return self.get_data_dir("template_dir")

    def set_score_dir(self, path):
        if not self.config.has_section("main"):
            self.config.add_section("main")
        self.config.set("main", "score_dir", path)

    def get_score_dir(self):
        return self.get_data_dir("score_dir")

    def set_motif_dir(self, path):
        if not self.config.has_section("main"):
            self.config.add_section("main")
        self.config.set("main", "motif_databases", path)

    def get_motif_dir(self):
        return self.get_data_dir("motif_databases")

    def set_gene_dir(self, path):
        if not self.config.has_section("main"):
            self.config.add_section("main")
        self.config.set("main", "gene_dir", path)

    def get_gene_dir(self):
        return self.get_data_dir("gene_dir")

    def set_bg_dir(self, path):
        if not self.config.has_section("main"):
            self.config.add_section("main")
        self.config.set("main", "bg", path)

    def get_bg_dir(self):
        return self.get_data_dir("bg")

    def set_tools_dir(self, path):
        if not self.config.has_section("main"):
            self.config.add_section("main")
        self.config.set("main", "tools", path)

    def get_tools_dir(self):
        return self.config.get("main", "tools")

    def is_configured(self, program):
        return self.config.has_section(program)

    def save(self):
        self.config.write(open(os.path.expanduser("~/.gimmemotifs.cfg"), "w"))

    def write(self, fo):
        self.config.write(fo)

    def list_installed_libraries(self):
        """Return a list of all motif libraries installed in this distribution.

        Each returned string is suitable for use with `gimmemotifs.motif.read_motifs()`.
        """
        libraries_dir = pathlib.Path(self.get_motif_dir()).resolve()
        library_paths = glob.glob(str(libraries_dir / "*.pfm"))
        return sorted([pathlib.Path(p).name for p in library_paths])


def parse_denovo_params(user_params=None):
    """Return default GimmeMotifs parameters.

    Defaults will be replaced with parameters defined in user_params.

    Parameters
    ----------
    user_params : dict, optional
        User-defined parameters.

    Returns
    -------
    params : dict
    """
    config = MotifConfig()

    if user_params is None:
        user_params = {}
    params = config.get_default_params()
    params.update(user_params)

    if params.get("torque"):
        logger.debug("Using torque")
    else:
        logger.debug("Using multiprocessing")

    params["background"] = [x.strip() for x in params["background"].split(",")]

    logger.debug("Parameters:")
    for param, value in params.items():
        logger.debug("  %s: %s", param, value)

    # Maximum time?

    if params["max_time"]:
        try:
            max_time = params["max_time"] = float(params["max_time"])
        except Exception:
            logger.debug("Could not parse max_time value, setting to no limit")
            params["max_time"] = -1

    if params["max_time"] > 0:
        logger.debug("Time limit for motif prediction: %0.2f hours", max_time)
        params["max_time"] = 3600 * params["max_time"]
        logger.debug("Max_time in seconds %0.0f", max_time)
    else:
        logger.debug("No time limit for motif prediction")

    return params


# if __name__ == "__main__":
#    m = MotifConfig()
#    print m.is_configured("meme")
