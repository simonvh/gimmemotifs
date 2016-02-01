from setuptools import setup
from setuptools import Extension, Command
from setuptools.command.install import install

from distutils.command.build import build
from distutils.command.install import INSTALL_SCHEMES
from distutils.util import get_platform
from distutils import log as dlog
import distutils.sysconfig
from subprocess import Popen
from platform import machine
from gimmemotifs.tools import *
from gimmemotifs.config import *
from gimmemotifs.shutils import which
from glob import glob
import os
import sys
import shutil
from stat import ST_MODE
import inspect

CONFIG_NAME = "gimmemotifs.cfg" 
DESCRIPTION  = """GimmeMotifs is a motif prediction pipeline. 
"""

DEFAULT_PARAMS = {
    "max_time": None,
    "analysis": "medium",
    "fraction": 0.2,
    "abs_max": 1000,
    "width": 200,
    "lwidth": 500,
    "pvalue": 0.001,
    "enrichment": 1.5,
    "background": "genomic_matched,random",
    "genome": "hg19",
    "tools": "MDmodule,Weeder,MotifSampler",
    "available_tools": "Weeder,MDmodule,MotifSampler,GADEM,MEME,MEMEW,trawler,Improbizer,BioProspector,AMD,ChIPMunk,Jaspar",
    "cluster_threshold": "0.95",
    "use_strand": False,
    "markov_model": 1,
    "motif_db": "vertebrate_motifs.pwm",
    "scan_cutoff": 0.9,    
}

MOTIF_CLASSES = ["MDmodule", "Meme", "Weeder", "Gadem", "MotifSampler", "Trawler", "Improbizer",  "BioProspector", "Posmo", "ChIPMunk", "Jaspar", "Amd", "Hms", "Homer"]
LONG_RUNNING = ["GADEM"]


# Included binaries after compile
MOTIF_BINS = {
    "MEME": "src/meme_4.6.0/src/meme.bin",
    "MDmodule": "src/MDmodule/MDmodule",
    "BioProspector": "src/BioProspector/BioProspector",
    "GADEM": "src/GADEM_v1.3/src/gadem",
    "Posmo": "src/posmo/posmo",
    "AMD": "src/AMD/AMD.bin",
    "Homer": "src/homer/bin/homer2",
}

data_files=[
    ('gimmemotifs/templates', ['templates/cluster_template.kid', 'templates/report_template.kid', 'templates/report_template_v2.kid', 'templates/cluster_template_v2.kid', 'templates/star.png']),
    ('gimmemotifs/score_dists', ['score_dists/total_wic_mean_score_dist.txt']),
    ('gimmemotifs/genes', ['genes/hg18.bed', 'genes/hg19.bed', 'genes/xenTro2.bed', 'genes/mm9.bed']),
    ('gimmemotifs/bg', ['bg/hg19.MotifSampler.bg', 'bg/hg18.MotifSampler.bg', 'bg/mm9.MotifSampler.bg', 'bg/xenTro2.MotifSampler.bg']),
    ('gimmemotifs/motif_databases', [
                                    'motif_databases/JASPAR2010_vertebrate.pwm',
                                    'motif_databases/vertebrate_motifs.pwm',
                                    'motif_databases/vertebrate_clusters.pwm',
                                    ]),
#    ('gimmemotifs/doc', ['doc/gimmemotifs_manual.pdf','doc/gimmemotifs_manual.html']),
    ('gimmemotifs/examples', ['examples/TAp73alpha.bed','examples/TAp73alpha.fa']),
    ('gimmemotifs/genome_index', ['genome_index/README.txt'])
]


# Fix for install_data, add share to prefix (borrowed from Dan Christiansen) 
for platform, scheme in INSTALL_SCHEMES.iteritems():
    if platform.startswith('unix_'):
        if scheme['data'][0] == '$' and '/' not in scheme['data']:
            scheme['data'] = os.path.join(scheme['data'], 'share')

class build_tools(Command):
    description = "compile all included motif prediction tools"

    def initialize_options(self):
        self.build_base = None
        self.plat_name = None
        self.build_tools_dir = None
        self.machine = None

    def finalize_options(self):    
        if self.plat_name is None:
            self.plat_name = get_platform()
        self.set_undefined_options('build',('build_base', 'build_base'))
        plat_specifier = ".%s-%s" % (self.plat_name, sys.version[0:3])
        self.build_tools_dir = os.path.join(self.build_base, 'tools' + plat_specifier)
        self.set_undefined_options('build',('custom_build', 'build_tools_dir'))
        self.machine = machine()

    def run(self):
        from compile_externals import compile_all
        prefix = distutils.sysconfig.get_config_var("prefix")
        
        if not os.path.exists(self.build_tools_dir):
            os.mkdir(self.build_tools_dir)

        # Try to compile everything
        compile_all(os.path.join(prefix, "share/gimmemotifs"))

        # Copy everything that has been compiled
        for bin in MOTIF_BINS.values():
            if os.path.exists(bin):
                shutil.copy(bin, self.build_tools_dir)

        # Copy seqlogo
        if os.path.exists("src/weblogo"):
            dlog.info("building seqlogo")
            patterns = ["src/weblogo/logo.*", "src/weblogo/template.*", "src/weblogo/seqlogo"]
            for p in patterns:
                for file in glob(p):
                    shutil.copy(file, self.build_tools_dir)

        # Copy posmo deps
        if os.path.exists("src/posmo"):
            shutil.copy("src/posmo/clusterwd", self.build_tools_dir)
        
        # Copy ChIPMunk
        if os.path.exists("src/ChIPMunk"):
            if os.path.exists(os.path.join(self.build_tools_dir, "ChIPMunk")):
                shutil.rmtree(os.path.join(self.build_tools_dir, "ChIPMunk"))
            shutil.copytree("src/ChIPMunk", os.path.join(self.build_tools_dir, "ChIPMunk"))
        # Copy HMS
        if os.path.exists("src/HMS"):
            if os.path.exists(os.path.join(self.build_tools_dir, "HMS")):
                shutil.rmtree(os.path.join(self.build_tools_dir, "HMS"))
            shutil.copytree("src/HMS", os.path.join(self.build_tools_dir, "HMS"))

        # Copy trawler
        if os.path.exists("src/trawler_standalone-1.2"):
            dlog.info("building trawler")
            if os.path.exists(os.path.join(self.build_tools_dir, "trawler")):
                shutil.rmtree(os.path.join(self.build_tools_dir, "trawler"))
            shutil.copytree("src/trawler_standalone-1.2", os.path.join(self.build_tools_dir, "trawler"))

        # Copy MotifSampler & Improbizer (ameme)
        if self.machine == "x86_64":
            if os.path.exists("src/MotifSampler"):
                dlog.info("copying MotifSampler 64bit")
                shutil.copy("src/MotifSampler/MotifSampler_x86_64", os.path.join(self.build_tools_dir, "MotifSampler"))
                shutil.copy("src/MotifSampler/CreateBackgroundModel_x86_64", os.path.join(self.build_tools_dir, "CreateBackgroundModel"))
            if os.path.exists("src/Improbizer"):
                dlog.info("copying Improbizer (ameme) 64bit")
                shutil.copy("src/Improbizer/ameme_x86_64", os.path.join(self.build_tools_dir, "ameme"))
        else: 
            if os.path.exists("src/MotifSampler"):
                dlog.info("copying MotifSampler 32bit")
                shutil.copy("src/MotifSampler/MotifSampler_i386", os.path.join(self.build_tools_dir, "MotifSampler"))
                shutil.copy("src/MotifSampler/CreateBackgroundModel_i386", os.path.join(self.build_tools_dir, "CreateBackgroundModel"))
            if os.path.exists("src/Improbizer"):
                dlog.info("copying Improbizer (ameme) 32bit")
                shutil.copy("src/Improbizer/ameme_i386", os.path.join(self.build_tools_dir, "ameme"))

class build_config(Command):
    description = "create a rudimentary config file"
    
    def initialize_options(self):
        self.build_cfg = None
        self.build_base = None
        self.build_tools_dir = None
    
    def finalize_options(self):    
        self.set_undefined_options('build', ('build_base', 'build_base'))
        self.set_undefined_options('build_tools', ('build_tools_dir', 'build_tools_dir'))
        #self.set_undefined_options('install', ('install_data', 'install_dir'))
        self.build_cfg = os.path.join(self.build_base, "cfg")

    def run(self):
        if not os.path.exists(self.build_cfg):
            os.mkdir(self.build_cfg)

        from gimmemotifs.config import MotifConfig
        cfg = MotifConfig(use_config="cfg/gimmemotifs.cfg.base")
        
        dlog.info("locating motif programs")
        available = []
        for program in MOTIF_CLASSES:
            # Get class
            m = eval(program)()
            cmd = m.cmd
            
            ### ugly, fixme :)
            if cmd == "trawler.pl":
                cmd = "trawler/bin/trawler.pl"
            if cmd == "ChIPMunk.sh":
                cmd = "ChIPMunk/ChIPMunk.sh"
            if cmd == "hms":
                cmd = "HMS/hms"

            bin = ""
            if cmd == "/bin/false":
                # motif db
                bin = "/bin/false"    
            elif os.path.exists(os.path.join(self.build_tools_dir, cmd)):
                bin = os.path.join(self.build_tools_dir, cmd)
                dlog.info("using included version of %s: %s" % (program, bin))
            else:
                ### ugly, fixme :)
                if cmd == "trawler/bin/trawler.pl":
                    cmd = "trawler.pl"
                if     cmd == "ChIPMunk/ChIPMunk.sh":
                    cmd = "ChIPMunk.sh"
                if cmd == "HMS/hms":
                    cmd = "hms"

                if program in MOTIF_BINS.keys():
                    dlog.info("could not find compiled version of %s" % program)
                bin = which(cmd)
                if bin:
                    dlog.info("using installed version of %s: %s" % (program, bin))
                else:
                    dlog.info("not found: %s" % program)
            
            ### Some more ugly stuff
            if bin:
                dir = bin.replace(m.cmd,"")
                if program == "Weeder":
                    dir = bin.replace("weederTFBS.out","")
                elif program == "Meme":
                    dir = bin.replace("bin/meme.bin", "").replace("meme.bin", "")
                elif program == "Trawler":
                    dir = bin.replace("bin/trawler.pl", "")
                elif program == "ChIPMunk":
                    dir = bin.replace("ChIPMunk.sh", "")

                available.append(m.name)
                cfg.set_program(m.name, {"bin":bin, "dir":dir})

        # Weblogo
        bin = ""
        seq_included = os.path.join(self.build_tools_dir, "seqlogo")
        if os.path.exists(seq_included):
            bin = seq_included
            dlog.info("using included version of weblogo: %s" % seq_included)
        else:
            bin = which("seqlogo")
            dlog.info("using installed version of seqlogo: %s" % (bin))
        if bin:
            cfg.set_seqlogo(bin)
        else:
            dlog.info("couldn't find seqlogo")
        
        # Set the available tools in the config file
        DEFAULT_PARAMS["available_tools"] = ",".join(available)
        
        for tool in available:
            if tool in LONG_RUNNING:
                dlog.info("PLEASE NOTE: %s can take a very long time to run on large datasets. Therefore it is not added to the default tools. You can always enable it later, see documentation for details" % tool)
                available.remove(tool)

        DEFAULT_PARAMS["tools"] = ",".join(available)
        cfg.set_default_params(DEFAULT_PARAMS)

        # Write (temporary) config file
        config_file = os.path.join(self.build_cfg, "%s" % CONFIG_NAME)
        dlog.info("writing (temporary) configuration file: %s" % config_file)
        f = open(config_file, "wb")
        cfg.write(f)
        f.close()

    def get_outputs(self):
        return self.outfiles or []

class install_tools(Command):
    description = "install (compiled) motif prediction tools"
    
    def initialize_options(self):
        self.tools_dir = None
        self.install_dir = None
        self.install_tools_dir = None
    
    def finalize_options(self):    
        self.set_undefined_options('build_tools', ('build_tools_dir', 'tools_dir'))
        self.set_undefined_options('install', ('install_data', 'install_dir'))
        self.install_tools_dir = os.path.join(self.install_dir, "gimmemotifs/tools")

    def run(self):
        dir = "src/Algorithm-Cluster-1.49/"
        if os.path.exists(os.path.join(dir, "Makefile")):
            Popen(["make","install"], cwd=dir, stdout=PIPE).communicate()

        dst = os.path.join(self.install_dir, "gimmemotifs/tools")
        self.outfiles = self.copy_tree(self.tools_dir, self.install_tools_dir)
        for file in self.outfiles:
            #trawler pl's
            if file.endswith("pl"):
                os.chmod(file, 0755)
    
    def get_outputs(self):
        return self.outfiles or []

class install_config(Command):
    description = "create and install a customized configuration file"

    def remove_nonsense(self, dir):
        if dir.find("BUILDROOT") != -1:
            components = os.path.normpath(os.path.abspath(dir)).split(os.sep)
            for i in range(len(components)):
                if components[i] == "BUILDROOT":
                    return os.path.sep.join([""] + components[i + 2:])
        elif dir.find("debian") != -1:
            components = os.path.normpath(os.path.abspath(dir)).split(os.sep)
            for i in range(len(components)):
                if components[i] == "debian":
                    return self.remove_nonsense(os.path.sep.join([""] + components[i + 2:]))
            
        return dir


    def initialize_options(self):
        self.build_base = None
        self.install_dir = None
        self.build_cfg = None
        self.build_tools_dir = None
        self.install_tools_dir = None

    def finalize_options(self):
        self.set_undefined_options('build', ('build_base', 'build_base'))
        self.set_undefined_options('install', ('install_data', 'install_dir'))
        self.set_undefined_options('build_config', ('build_cfg', 'install_dir'))
        self.set_undefined_options('build_tools', ('build_tools_dir', 'build_tools_dir'))
        self.set_undefined_options('install_tools', ('install_tools_dir', 'install_tools_dir'))
    
    def run(self):
        from gimmemotifs.config import MotifConfig
        
        cfg = MotifConfig(use_config=self.build_cfg)

        data_dir = self.remove_nonsense(os.path.abspath(self.install_dir))
        
        cfg.set_template_dir(os.path.join(data_dir, 'gimmemotifs/templates'))
        cfg.set_gene_dir(os.path.join(data_dir, 'gimmemotifs/genes'))
        cfg.set_score_dir(os.path.join(data_dir, 'gimmemotifs/score_dists'))
        cfg.set_index_dir(os.path.join(data_dir, 'gimmemotifs/genome_index'))
        cfg.set_motif_dir(os.path.join(data_dir, 'gimmemotifs/motif_databases'))
        cfg.set_bg_dir(os.path.join(data_dir, 'gimmemotifs/bg'))
        cfg.set_tools_dir(os.path.join(data_dir, 'gimmemotifs/tools'))
        
        final_tools_dir = self.remove_nonsense(self.install_tools_dir)
        for program in MOTIF_CLASSES:
            m = eval(program)()
            if cfg.is_configured(m.name):
                bin = cfg.bin(m.name).replace(self.build_tools_dir, final_tools_dir) 
                dir = cfg.dir(m.name)
                if dir:
                    dir = dir.replace(self.build_tools_dir, final_tools_dir)
                cfg.set_program(m.name, {"bin":bin, "dir":dir})
            
        dir = cfg.get_seqlogo()
        dir = dir.replace(self.build_tools_dir, final_tools_dir)
        cfg.set_seqlogo(dir)

        # Use a user-specific configfile if any other installation scheme is used
#        if os.path.abspath(self.install_dir) == "/usr/share":
        config_file = os.path.join(self.install_dir, "gimmemotifs/%s" % CONFIG_NAME)
        self.outfiles = [config_file] 


        if os.path.exists(config_file):
            new_config = config_file + ".tmp"
            dlog.info("INFO: Configfile %s already exists!" % config_file)
            dlog.info("INFO: Will create %s, which contains the new config." % new_config)
            dlog.info("INFO: If you want to use the newly generated config you can move %s to %s, otherwise you can delete %s.\n" % (new_config, config_file, new_config))

            f =  open(new_config, "wb")
            cfg.write(f)
        else: 
            dlog.info("writing configuration file %s" % config_file)
            f =  open(config_file, "wb")
            cfg.write(f)
        
        if os.path.abspath(self.install_dir) != "/usr/share":
            dlog.info("PLEASE NOTE: GimmeMotifs is installed in a non-standard location.")
            dlog.info("PLEASE NOTE: This is fine, but then every user should have a file called ~/.gimmemotifs.cfg")
            dlog.info("PLEASE NOTE: The file %s is fully configured during install and can be used for that purpose." % config_file)
    
    def get_outputs(self):
        return self.outfiles or []

class custom_build(build):
    def run(self):
        build.run(self)
        self.run_command('build_tools')
        self.run_command('build_config')

class custom_install(install):
    sub_commands = install.sub_commands + [
            ('install_tools', lambda self: True),
            ('install_config', lambda self: True)
            ]

    # Make sure we install in the correct locations on Ubuntu
    def finalize_options(self):
        install.finalize_options(self)
        if self.install_data == "/usr":
            self.install_data = "/usr/share"
        if self.install_data.endswith("/usr"):
            parts = self.install_data.split(os.sep)
            if parts[-3] == "debian":
                self.install_data = os.path.join(self.install_data, "share")

    
    def run(self):
        install.run(self)
    
module1 = Extension('gimmemotifs.c_metrics', sources = ['gimmemotifs/c_metrics.c'], libraries = ['gsl', 'gslcblas'])

setup (name = 'gimmemotifs',
        cmdclass={"build":custom_build, 
                            "build_tools":build_tools,
                            "build_config":build_config,
                            "install":custom_install, 
                            "install_tools":install_tools,
                            "install_config":install_config,
                            },
        version = GM_VERSION,
        description = DESCRIPTION,
        author='Simon van Heeringen',
        author_email='s.vanheeringen@ncmls.ru.nl',
        url='http://www.ncmls.eu/bioinfo/gimmemotifs/',
        license='MIT',
        packages=['gimmemotifs', 'gimmemotifs/commands'],
        ext_modules = [module1],
        scripts=[
            'scripts/get_fpr_based_pwmscan_threshold.py',
            'scripts/add_organism.py',
            'scripts/generate_background_sequences.py',
            'scripts/closest_motif_match.py',
            'scripts/motif_cluster.py',
            'scripts/create_genome_index.py',
            'scripts/gimme_motifs.py',
            'scripts/motif_roc.py',
            'scripts/motif_roc_metrics.py',
            'scripts/motif_localization_plots.py',
            'scripts/pwm2logo.py',
            'scripts/track2fasta.py',
            'scripts/pwmscan.py',
            'scripts/gimme_max.py',
            'scripts/gimme',
            ],
        data_files=data_files,
        install_requires = [
            "setuptools >= 0.7",
            "numpy >= 1.6.0",
            "scipy >= 0.9.0",
            "matplotlib >= 1.1.1",
            "kid >= 0.9.6",
            "pyyaml >= 3.10",
            "Pycluster >= 1.52",
            "pybedtools",
        ],
        dependency_links = [
            "http://bonsai.hgc.jp/~mdehoon/software/cluster/software.htm",
            #"http://www.parallelpython.com/content/view/18/32/",
#            "http://www.parallelpython.com/index2.php?option=com_content&task=view&id=18&pop=1&page=0&Itemid=32",
#           "https://pypi.python.org/pypi/pp",
#            "http://www.parallelpython.com/downloads/pp/pp-1.6.4.tar.gz",
        ],
)
