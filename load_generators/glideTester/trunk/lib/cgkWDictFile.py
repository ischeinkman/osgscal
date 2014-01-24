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

class glideKeeperDicts(cvWDictFile.frontendMainDicts):
    def __init__(self,work_dir,
                 web_stage_dir=None): # if None, create a web subdir in the work_dir; someone else need to copy it to the place visible by web_url
        if web_stage_dir==None:
            web_stage_dir=os.path.join(work_dir,'web')
        cvWDictFile.frontendMainDicts.__init__(self,work_dir,web_stage_dir,
                                               workdir_name="web",simple_work_dir=True,assume_groups=False)
        self.add_dir_obj(cWDictFile.symlinkSupport(web_stage_dir,os.path.join(work_dir,'web'),"web"))
        
    def populate(self,final_web_url,gridmap_file):
        self.dicts['frontend_descript'].add('WebURL',final_web_url)
        self.dicts['gridmap'].load(dir=os.path.dirname(gridmap_file),fname=os.path.basename(gridmap_file),
                                   change_self=False,erase_first=True,set_not_changed=False)
        for k in ('GLIDETESTER_InstanceID','GLIDETESTER_SessionID'):
            self.dicts['vars'].add_extended(k,"string",None,None,False,True,True)
