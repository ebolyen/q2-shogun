# ----------------------------------------------------------------------------
# Copyright (c) 2016-2018, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

import os
import subprocess
import tempfile
import shutil

import yaml
import biom
import pandas as pd
from qiime2.util import duplicate
from q2_types.feature_data import DNAFASTAFormat

from q2_shogun._formats import Bowtie2IndexDirFmt


def _run_command(cmd, verbose=True):
    if verbose:
        print("Running external command line application. This may print "
              "messages to stdout and/or stderr.")
        print("The command being run is below. This command cannot "
              "be manually re-run as it will depend on temporary files that "
              "no longer exist.")
        print("\nCommand:", end=' ')
        print(" ".join(cmd), end='\n\n')
    subprocess.run(cmd, check=True)


def setup_database_dir(tmpdir, database, refseqs, reftaxa):
    BOWTIE_PATH = 'bowtie2'
    duplicate(str(refseqs), os.path.join(tmpdir, refseqs.path.name))
    duplicate(str(reftaxa), os.path.join(tmpdir, reftaxa.path.name))
    shutil.copytree(str(database), os.path.join(tmpdir, BOWTIE_PATH),
                    copy_function=duplicate)
    params = {
        'general': {
            'taxonomy': reftaxa.path.name,
            'fasta': refseqs.path.name
        },
        'bowtie2': os.path.join(BOWTIE_PATH, database.get_name())
    }
    with open(os.path.join(tmpdir, 'metadata.yaml'), 'w') as fh:
        yaml.dump(params, fh, default_flow_style=False)


def load_table(tab_fp):
    '''Convert classic OTU table to biom feature table'''
    return biom.table.Table.from_tsv(tab_fp, None, None, None)


def minipipe(query: DNAFASTAFormat, reference_reads: DNAFASTAFormat,
             reference_taxonomy: pd.Series, database: Bowtie2IndexDirFmt,
             taxacut: float=0.8,
             threads: int=1, percent_id: float=0.98) -> (
                     biom.Table, biom.Table, biom.Table, biom.Table):
    with tempfile.TemporaryDirectory('q2-shogun') as tmpdir:
        database_dir = tmpdir.name
        setup_database_dir(database_dir,
                           database, reference_reads, reference_taxonomy)

        # run pipeline
        cmd = ['shogun', 'pipeline', '-i', str(query), '-d', database_dir,
               '-o', database_dir, '-a', 'bowtie2', '-x', taxacut,
               '-t', threads, '-p', percent_id]
        _run_command(cmd)

        # output selected results as feature tables
        tables = ['taxatable.strain.txt',
                  'taxatable.strain.kegg.txt',
                  'taxatable.strain.kegg.modules.txt',
                  'taxatable.strain.kegg.pathways.txt']
        return tuple(load_table(os.path.join(database_dir, t)) for t in tables)