#######################################################
#
# Description:
#   Web files creation module
#
# Author:
#   Igor Sfiligoi @ UCSD
#
#######################################################

import os,os.path
# this is imported from
#  glideinWMS/creation/lib
# but needs modules from
#  glideinWMS/lib
# as well
from glideinwms.creation.lib import cvWDictFile
from glideinwms.creation.lib import cWDictFile
from glideinwms.creation.lib import cWConsts

class glideKeeperDicts(cvWDictFile.frontendDicts):
    def __init__(self,work_dir,
                 web_stage_dir=None): # if None, create a web subdir in the work_dir; someone else need to copy it to the place visible by web_url
        if web_stage_dir==None:
            web_stage_dir=os.path.join(work_dir,'web')
        cvWDictFile.frontendDicts.__init__(self,work_dir,web_stage_dir,
                                           group_list=["glidetester"],
                                           workdir_name="web",simple_work_dir=True)
        self.group_name=self.sub_dicts.keys()[0] # single group, so the first one is the only one
        self.main_dicts.add_dir_obj(cWDictFile.symlinkSupport(web_stage_dir,os.path.join(work_dir,'web'),"web"))
        
    def populate(self,final_web_url,gridmap_file):
        self.main_dicts.dicts['frontend_descript'].add('WebURL',final_web_url)
        self.main_dicts.dicts['frontend_descript'].add('Groups',self.group_name)
        self.main_dicts.dicts['gridmap'].load(dir=os.path.dirname(gridmap_file),fname=os.path.basename(gridmap_file),
                                              change_self=False,erase_first=True,set_not_changed=False)
        for k in ('GLIDETESTER_InstanceID','GLIDETESTER_SessionID'):
            self.main_dicts.dicts['vars'].add_extended(k,"string",None,None,False,True,True)
