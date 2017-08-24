#!/usr/bin/env python

###############################################################
# < next few lines under version control, D O  N O T  E D I T >
# $Date$
# $Revision$
# $Author$
# $Id$
###############################################################
'''
    PROGRAM:
        Create the ROCOTO workflow given the configuration of the GFS parallel

    AUTHOR:
        Rahul.Mahajan
        rahul.mahajan@noaa.gov

    FILE DEPENDENCIES:
        1. config files for the parallel; e.g. config.base, config.fcst[.gfs], etc.
        Without these dependencies, the script will fail

    OUTPUT:
        1. PSLOT.xml: XML workflow
        2. PSLOT.crontab: crontab for ROCOTO run command
'''

import os
import sys
from datetime import datetime, timedelta
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import rocoto
import workflow_utils as wfu

gfs_tasks = ['prep', 'anal', 'fcst', 'post', 'vrfy', 'arch']
hyb_tasks = ['eobs', 'eomg', 'eupd', 'ecen', 'efcs', 'epos', 'earc']

def main():
    parser = ArgumentParser(description='Setup XML workflow and CRONTAB for a GFS parallel.', formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('--expdir',help='full path to experiment directory containing config files', type=str, required=False, default=os.environ['PWD'])
    args = parser.parse_args()

    configs = wfu.get_configs(args.expdir)

    _base = wfu.config_parser([wfu.find_config('config.base', configs)])

    if args.expdir != _base['EXPDIR']:
        print 'MISMATCH in experiment directories!'
        print 'config.base: EXPDIR = %s' % _base['EXPDIR']
        print 'input arg: --expdir = %s' % args.expdir
        sys.exit(1)

    tasks = gfs_tasks + hyb_tasks if _base['DOHYBVAR'] == 'YES' else gfs_tasks

    dict_configs = wfu.source_configs(configs, tasks)

    # First create workflow XML
    create_xml(dict_configs)

    # Next create the crontab
    wfu.create_crontab(dict_configs['base'])

    return


def get_gfs_cyc_dates(base):
    '''
        Generate GFS dates from experiment dates and gfs_cyc choice
        Set realtime flag
    '''

    base_out = base.copy()

    gfs_cyc = base['gfs_cyc']
    sdate = base['SDATE']
    edate = base['EDATE']

    interval_gfs = wfu.get_gfs_interval(gfs_cyc)

    # Set GFS cycling dates
    hrdet = 0
    if gfs_cyc == 1:
        hrinc = 24 - sdate.hour
        hrdet = edate.hour
    elif gfs_cyc == 2:
        if sdate.hour in [0, 12]:
            hrinc = 12
        elif sdate.hour in [6, 18]:
            hrinc = 6
        if edate.hour in [6, 18]:
            hrdet = 6
    elif gfs_cyc == 4:
        hrinc = 6
    sdate_gfs = sdate + timedelta(hours=hrinc)
    edate_gfs = edate - timedelta(hours=hrdet)
    if sdate_gfs > edate:
        print 'W A R N I N G!'
        print 'Starting date for GFS cycles is after Ending date of experiment'
        print 'SDATE = %s,     EDATE = %s' % (sdate.strftime('%Y%m%d%H'), edate.strftime('%Y%m%d%H'))
        print 'SDATE_GFS = %s, EDATE_GFS = %s' % (sdate_gfs.strftime('%Y%m%d%H'), edate_gfs.strftime('%Y%m%d%H'))
        gfs_cyc = 0

    base_out['gfs_cyc'] = gfs_cyc
    base_out['SDATE_GFS'] = sdate_gfs
    base_out['EDATE_GFS'] = edate_gfs
    base_out['INTERVAL_GFS'] = interval_gfs

    # over-write realtime flag with T or F
    realtime = 'F'
    if base.has_key('REALTIME'):
        realtime = 'T' if base['REALTIME'].upper() in ['Y', 'YES', '.T.', '.TRUE.'] else 'F'
    base_out['REALTIME'] = realtime

    return base_out


def get_preamble():
    '''
        Generate preamble for XML
    '''

    strings = []

    strings.append('<?xml version="1.0"?>\n')
    strings.append('<!DOCTYPE workflow\n')
    strings.append('[\n')
    strings.append('\t<!--\n')
    strings.append('\tPROGRAM\n')
    strings.append('\t\tMain workflow manager for cycling Global Forecast System\n')
    strings.append('\n')
    strings.append('\tAUTHOR:\n')
    strings.append('\t\tRahul Mahajan\n')
    strings.append('\t\trahul.mahajan@noaa.gov\n')
    strings.append('\n')
    strings.append('\tNOTES:\n')
    strings.append('\t\tThis workflow was automatically generated at %s\n' % datetime.now())
    strings.append('\t-->\n')

    return ''.join(strings)


def get_definitions(base):
    '''
        Create entities related to the experiment
    '''

    strings = []

    strings.append('\n')
    strings.append('\t<!-- Experiment parameters such as name, starting, ending dates -->\n')
    strings.append('\t<!ENTITY PSLOT "%s">\n' % base['PSLOT'])
    strings.append('\t<!ENTITY SDATE "%s">\n' % base['SDATE'].strftime('%Y%m%d%H%M'))
    strings.append('\t<!ENTITY EDATE "%s">\n' % base['EDATE'].strftime('%Y%m%d%H%M'))
    strings.append('\n')
    strings.append('\t<!ENTITY REALTIME "%s">\n' % base['REALTIME'])
    strings.append('\t<!ENTITY DMPDIR   "%s">\n' % base['DMPDIR'])
    strings.append('\n')
    strings.append('\t<!-- Experiment and Rotation directory -->\n')
    strings.append('\t<!ENTITY EXPDIR "%s">\n' % base['EXPDIR'])
    strings.append('\t<!ENTITY ROTDIR "%s">\n' % base['ROTDIR'])
    strings.append('\n')
    strings.append('\t<!-- Directories for driving the workflow -->\n')
    strings.append('\t<!ENTITY JOBS_DIR "%s/fv3gfs/jobs">\n' % base['BASE_WORKFLOW'])
    strings.append('\n')
    strings.append('\t<!-- Machine related entities -->\n')
    strings.append('\t<!ENTITY ACCOUNT    "%s">\n' % base['ACCOUNT'])
    strings.append('\t<!ENTITY QUEUE      "%s">\n' % base['QUEUE'])
    strings.append('\t<!ENTITY QUEUE_ARCH "%s">\n' % base['QUEUE_ARCH'])
    strings.append('\t<!ENTITY SCHEDULER  "%s">\n' % wfu.get_scheduler(base['machine']))
    strings.append('\n')
    strings.append('\t<!-- Toggle HPSS archiving -->\n')
    strings.append('\t<!ENTITY ARCHIVE_TO_HPSS "YES">\n')
    strings.append('\n')
    strings.append('\t<!-- ROCOTO parameters that control workflow -->\n')
    strings.append('\t<!ENTITY CYCLETHROTTLE "3">\n')
    strings.append('\t<!ENTITY TASKTHROTTLE  "20">\n')
    strings.append('\t<!ENTITY MAXTRIES      "2">\n')
    strings.append('\n')

    return ''.join(strings)


def get_gfs_dates(base):
    '''
        Generate GFS dates entities
    '''

    strings = []

    strings.append('\n')
    strings.append('\t<!-- Starting and ending dates for GFS cycle -->\n')
    strings.append('\t<!ENTITY SDATE_GFS    "%s">\n' % base['SDATE_GFS'].strftime('%Y%m%d%H%M'))
    strings.append('\t<!ENTITY EDATE_GFS    "%s">\n' % base['EDATE_GFS'].strftime('%Y%m%d%H%M'))
    strings.append('\t<!ENTITY INTERVAL_GFS "%s">\n' % base['INTERVAL_GFS'])

    return ''.join(strings)


def get_gdasgfs_resources(dict_configs, cdump='gdas'):
    '''
        Create GDAS or GFS resource entities
    '''

    strings = []

    strings.append('\n')
    strings.append('\t<!-- BEGIN: Resource requirements for %s part of the workflow -->\n' % cdump.upper())
    strings.append('\n')

    machine = dict_configs['base']['machine']

    tasks = ['prep', 'anal', 'fcst', 'post', 'vrfy', 'arch']
    for task in tasks:

        cfg = dict_configs[task]

        wtimestr, resstr, queuestr = wfu.get_resources(machine, cfg, task, cdump=cdump)
        taskstr = '%s_%s' % (task.upper(), cdump.upper())

        strings.append('\t<!ENTITY QUEUE_%s     "%s">\n' % (taskstr, queuestr))
        strings.append('\t<!ENTITY WALLTIME_%s  "%s">\n' % (taskstr, wtimestr))
        strings.append('\t<!ENTITY RESOURCES_%s "%s">\n' % (taskstr, resstr))
        strings.append('\t<!ENTITY NATIVE_%s    "">\n'   % (taskstr))

        strings.append('\n')

    strings.append('\t<!-- END: Resource requirements for %s part of the workflow -->\n' % cdump.upper())

    return ''.join(strings)


def get_hyb_resources(dict_configs, cdump='gdas'):
    '''
        Create hybrid resource entities
    '''

    strings = []

    strings.append('\n')
    strings.append('\t<!-- BEGIN: Resource requirements for hybrid part of the workflow -->\n')
    strings.append('\n')

    machine = dict_configs['base']['machine']

    tasks = ['eobs', 'eomg', 'eupd', 'ecen', 'efcs', 'epos', 'earc']
    for task in tasks:

        cfg = dict_configs['eobs'] if task in ['eomg'] else dict_configs[task]

        wtimestr, resstr, queuestr = wfu.get_resources(machine, cfg, task, cdump=cdump)
        taskstr = '%s_%s' % (task.upper(), cdump.upper())

        strings.append('\t<!ENTITY QUEUE_%s     "%s">\n' % (taskstr, queuestr))
        strings.append('\t<!ENTITY WALLTIME_%s  "%s">\n' % (taskstr, wtimestr))
        strings.append('\t<!ENTITY RESOURCES_%s "%s">\n' % (taskstr, resstr))
        strings.append('\t<!ENTITY NATIVE_%s    "">\n'   % (taskstr))

        strings.append('\n')

    strings.append('\t<!-- END: Resource requirements for hybrid part of the workflow-->\n')

    return ''.join(strings)


def get_gdasgfs_tasks(cdump='gdas', dohybvar='NO'):
    '''
        Create GDAS or GFS tasks
    '''

    envars = []
    envars.append(rocoto.create_envar(name='EXPDIR', value='&EXPDIR;'))
    envars.append(rocoto.create_envar(name='CDATE', value='<cyclestr>@Y@m@d@H</cyclestr>'))
    envars.append(rocoto.create_envar(name='CDUMP', value='%s' % cdump))

    tasks = []

    # prep
    deps = []
    dep_dict = {'type':'task', 'name':'%spost' % 'gdas', 'offset':'-06:00:00'}
    deps.append(rocoto.add_dependency(dep_dict))
    data = '&DMPDIR;/@Y@m@d@H/%s/%s.t@Hz.updated.status.tm00.bufr_d' % (cdump, cdump)
    dep_dict = {'type':'data', 'data':data}
    deps.append(rocoto.add_dependency(dep_dict))
    dependencies = rocoto.create_dependency(dep_condition='and', dep=deps)
    task = wfu.create_wf_task('prep', cdump=cdump, envar=envars, dependency=dependencies)

    tasks.append(task)
    tasks.append('\n')

    # anal
    deps = []
    dep_dict = {'type':'task', 'name':'%sprep' % cdump}
    deps.append(rocoto.add_dependency(dep_dict))
    if dohybvar in ['y', 'Y', 'yes', 'YES']:
        dep_dict = {'type':'task', 'name':'%sepos' % 'gdas', 'offset':'-06:00:00'}
        deps.append(rocoto.add_dependency(dep_dict))
        dependencies = rocoto.create_dependency(dep_condition='and', dep=deps)
    else:
        dependencies = rocoto.create_dependency(dep=deps)
    task = wfu.create_wf_task('anal', cdump=cdump, envar=envars, dependency=dependencies)

    tasks.append(task)
    tasks.append('\n')

    # fcst
    deps = []
    dep_dict = {'type':'task', 'name':'%sanal' % cdump}
    deps.append(rocoto.add_dependency(dep_dict))
    if cdump in ['gdas']:
        dep_dict = {'type':'cycleexist', 'condition':'not', 'offset':'-06:00:00'}
        deps.append(rocoto.add_dependency(dep_dict))
        dependencies = rocoto.create_dependency(dep_condition='or', dep=deps)
    elif cdump in ['gfs']:
        dependencies = rocoto.create_dependency(dep=deps)
    task = wfu.create_wf_task('fcst', cdump=cdump, envar=envars, dependency=dependencies)

    tasks.append(task)
    tasks.append('\n')

    # post
    deps = []
    dep_dict = {'type':'task', 'name':'%sfcst' % cdump}
    deps.append(rocoto.add_dependency(dep_dict))
    dependencies = rocoto.create_dependency(dep=deps)
    task = wfu.create_wf_task('post', cdump=cdump, envar=envars, dependency=dependencies)

    tasks.append(task)
    tasks.append('\n')

    # vrfy
    deps = []
    dep_dict = {'type':'task', 'name':'%spost' % cdump}
    deps.append(rocoto.add_dependency(dep_dict))
    dependencies = rocoto.create_dependency(dep=deps)
    task = wfu.create_wf_task('vrfy', cdump=cdump, envar=envars, dependency=dependencies)

    tasks.append(task)
    tasks.append('\n')

    # arch
    deps = []
    dep_dict = {'type':'task', 'name':'%svrfy' % cdump}
    deps.append(rocoto.add_dependency(dep_dict))
    dep_dict = {'type':'streq', 'left':'&ARCHIVE_TO_HPSS;', 'right':'YES'}
    deps.append(rocoto.add_dependency(dep_dict))
    dependencies = rocoto.create_dependency(dep_condition='and', dep=deps)
    task = wfu.create_wf_task('arch', cdump=cdump, envar=envars, dependency=dependencies)

    tasks.append(task)
    tasks.append('\n')

    return ''.join(tasks)


def get_hyb_tasks(EOMGGROUPS, EFCSGROUPS, EARCGROUPS, cdump='gdas'):
    '''
        Create Hybrid tasks
    '''

    envars = []
    envars.append(rocoto.create_envar(name='EXPDIR', value='&EXPDIR;'))
    envars.append(rocoto.create_envar(name='CDATE', value='<cyclestr>@Y@m@d@H</cyclestr>'))
    envars.append(rocoto.create_envar(name='CDUMP', value='%s' % cdump))

    ensgrp = rocoto.create_envar(name='ENSGRP', value='#grp#')

    tasks = []

    # eobs
    deps = []
    dep_dict = {'type':'task', 'name':'%sprep' % cdump}
    deps.append(rocoto.add_dependency(dep_dict))
    dep_dict = {'type':'task', 'name':'%sepos' % cdump, 'offset':'-06:00:00'}
    deps.append(rocoto.add_dependency(dep_dict))
    dependencies = rocoto.create_dependency(dep_condition='and', dep=deps)
    task = wfu.create_wf_task('eobs', cdump=cdump, envar=envars, dependency=dependencies)

    tasks.append(task)
    tasks.append('\n')

    # eomn, eomg
    varname = 'grp'
    varval = EOMGGROUPS
    deps = []
    dep_dict = {'type':'task', 'name':'%seobs' % cdump}
    deps.append(rocoto.add_dependency(dep_dict))
    dependencies = rocoto.create_dependency(dep=deps)
    eomgenvars = envars + [ensgrp]
    task = wfu.create_wf_task('eomg', cdump=cdump, envar=eomgenvars, dependency=dependencies, metatask='eomn', varname=varname, varval=varval)

    tasks.append(task)
    tasks.append('\n')

    # eupd
    deps = []
    dep_dict = {'type':'metatask', 'name':'%seomn' % cdump}
    deps.append(rocoto.add_dependency(dep_dict))
    dependencies = rocoto.create_dependency(dep=deps)
    task = wfu.create_wf_task('eupd', cdump=cdump, envar=envars, dependency=dependencies)

    tasks.append(task)
    tasks.append('\n')

    # ecen
    deps = []
    dep_dict = {'type':'task', 'name':'%sanal' % cdump}
    deps.append(rocoto.add_dependency(dep_dict))
    dep_dict = {'type':'task', 'name':'%seupd' % cdump}
    deps.append(rocoto.add_dependency(dep_dict))
    dependencies = rocoto.create_dependency(dep_condition='and', dep=deps)
    task = wfu.create_wf_task('ecen', cdump=cdump, envar=envars, dependency=dependencies)

    tasks.append(task)
    tasks.append('\n')

    # efmn, efcs
    varname = 'grp'
    varval = EFCSGROUPS
    deps = []
    dep_dict = {'type':'task', 'name':'%secen' % cdump}
    deps.append(rocoto.add_dependency(dep_dict))
    dep_dict = {'type':'cycleexist', 'condition':'not', 'offset':'-06:00:00'}
    deps.append(rocoto.add_dependency(dep_dict))
    dependencies = rocoto.create_dependency(dep_condition='or', dep=deps)
    efcsenvars = envars + [ensgrp]
    task = wfu.create_wf_task('efcs', cdump=cdump, envar=efcsenvars, dependency=dependencies, \
           metatask='efmn', varname=varname, varval=varval)

    tasks.append(task)
    tasks.append('\n')

    # epos
    deps = []
    dep_dict = {'type':'metatask', 'name':'%sefmn' % cdump}
    deps.append(rocoto.add_dependency(dep_dict))
    dependencies = rocoto.create_dependency(dep=deps)
    task = wfu.create_wf_task('epos', cdump=cdump, envar=envars, dependency=dependencies)

    tasks.append(task)
    tasks.append('\n')

    # eamn, earc
    varname = 'grp'
    varval = EARCGROUPS
    deps = []
    dep_dict = {'type':'task', 'name':'%sepos' % cdump}
    deps.append(rocoto.add_dependency(dep_dict))
    dependencies = rocoto.create_dependency(dep=deps)
    earcenvars = envars + [ensgrp]
    task = wfu.create_wf_task('earc', cdump=cdump, envar=earcenvars, dependency=dependencies, \
           metatask='eamn', varname=varname, varval=varval)

    tasks.append(task)
    tasks.append('\n')

    return ''.join(tasks)


def get_workflow_header(base):
    '''
        Create the workflow header block
    '''

    strings = []

    strings.append('\n')
    strings.append(']>\n')
    strings.append('\n')
    strings.append('<workflow realtime="&REALTIME;" scheduler="&SCHEDULER;" cyclethrottle="&CYCLETHROTTLE;" taskthrottle="&TASKTHROTTLE;">\n')
    strings.append('\n')
    strings.append('\t<log verbosity="10"><cyclestr>&EXPDIR;/logs/@Y@m@d@H.log</cyclestr></log>\n')
    strings.append('\n')
    strings.append('\t<!-- Define the cycles -->\n')
    strings.append('\t<cycledef group="first">&SDATE;     &SDATE;     06:00:00</cycledef>\n')
    strings.append('\t<cycledef group="gdas" >&SDATE;     &EDATE;     06:00:00</cycledef>\n')
    if base['gfs_cyc'] != 0:
        strings.append('\t<cycledef group="gfs"  >&SDATE_GFS; &EDATE_GFS; &INTERVAL_GFS;</cycledef>\n')

    strings.append('\n')

    return ''.join(strings)


def get_workflow_footer():
    '''
        Generate workflow footer
    '''

    strings = []
    strings.append('\n</workflow>\n')

    return ''.join(strings)


def create_xml(dict_configs):
    '''
        Given an dictionary of sourced config files,
        create the workflow XML
    '''

    if dict_configs['base']['gfs_cyc'] != 0:
        dict_configs['base'] = get_gfs_cyc_dates(dict_configs['base'])

    base = dict_configs['base']

    # Start collecting workflow pieces
    preamble = get_preamble()
    definitions = get_definitions(base)
    workflow_header = get_workflow_header(base)
    workflow_footer = get_workflow_footer()

    # Get GDAS related entities, resources, workflow
    gdas_resources = get_gdasgfs_resources(dict_configs)
    gdas_tasks = get_gdasgfs_tasks(dohybvar=base['DOHYBVAR'])

    # Get hybrid related entities, resources, workflow
    if base['DOHYBVAR'] == "YES":

        # Determine EOMG/EFCS groups based on ensemble size and grouping
        nens = base['NMEM_ENKF']
        eobs = dict_configs['eobs']
        efcs = dict_configs['efcs']
        earc = dict_configs['earc']
        nens_eomg = eobs['NMEM_EOMGGRP']
        nens_efcs = efcs['NMEM_EFCSGRP']
        nens_earc = earc['NMEM_EARCGRP']
        neomg_grps = nens / nens_eomg
        nefcs_grps = nens / nens_efcs
        nearc_grps = nens / nens_earc
        EOMGGROUPS = ' '.join(['%02d' % x for x in range(1, neomg_grps+1)])
        EFCSGROUPS = ' '.join(['%02d' % x for x in range(1, nefcs_grps+1)])
        EARCGROUPS = ' '.join(['%02d' % x for x in range(0, nearc_grps+1)])

        hyb_resources = get_hyb_resources(dict_configs)
        hyb_tasks = get_hyb_tasks(EOMGGROUPS, EFCSGROUPS, EARCGROUPS )

    # Get GFS cycle related entities, resources, workflow
    if base['gfs_cyc'] != 0:
        gfs_dates = get_gfs_dates(base)
        gfs_resources = get_gdasgfs_resources(dict_configs, cdump='gfs')
        gfs_tasks = get_gdasgfs_tasks(cdump='gfs', dohybvar=base['DOHYBVAR'])

    xmlfile = []
    xmlfile.append(preamble)
    xmlfile.append(definitions)
    if base['gfs_cyc'] != 0:
        xmlfile.append(gfs_dates)
    xmlfile.append(gdas_resources)
    if base['DOHYBVAR'] == "YES":
        xmlfile.append(hyb_resources)
    if base['gfs_cyc'] != 0:
        xmlfile.append(gfs_resources)
    xmlfile.append(workflow_header)
    xmlfile.append(gdas_tasks)
    if base['DOHYBVAR'] == 'YES':
        xmlfile.append(hyb_tasks)
    if base['gfs_cyc'] != 0:
        xmlfile.append(gfs_tasks)
    xmlfile.append(wfu.create_firstcyc_task())
    xmlfile.append(workflow_footer)

    # Write the XML file
    fh = open('%s/%s.xml' % (base['EXPDIR'], base['PSLOT']), 'w')
    fh.write(''.join(xmlfile))
    fh.close()

    return


if __name__ == '__main__':
    main()
    sys.exit(0)