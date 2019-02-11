#!/bin/env python
###################################################################
# script: fretta_sanity.py
# Clean boot and lxc and calvados launch
###################################################################

"""
   TAG_MAP:
        title:          Fretta Coherent Scale_Stress
        descr:          Testsuite for Scale_Stress on ncs5500
        platform:       NCS5508
        min-sw-ver:     06.02.02
        test-phase:     dev-test
        modular-pkg:    coherent
        test-type:      functionality
        test-component: ['coherent']
        sw-component: 
        topology:       Fretta-Two-Router-Dynamic
        tgn-type:       spirent
        link-type:      100G,150 and 200
        customer:       not-applicable
        cdets-attribute: fretta-coherent
        run_time:   10hrs
        projects:   DevTest
"""


from ats import tcl
from ats import aetest
from ats.atslog.utils import banner
from ats.results import *
import re
import pdb
import logging
import os
import pprint
import sth
from IPython import embed
import itertools 
from time import sleep
from xtgn_lib.stclib import Spirent, g_stc_handles
from pprint import pprint
from xNetworkEvents import *
from xTopology import routers, tgns
from xFretta_lib import *
from xCommon_lib import *
#from Fretta_pmfc_Scripts.Coh_Libs.Pkt_Libs import *
#from Fretta_pmfc_Scripts.Coh_Libs.DWDM_Libs import *
#from Fretta_pmfc_Scripts.Coh_Libs.MacSec_Libs import *
#from Fretta_pmfc_Scripts.Coh_Libs.utils import *
from Fretta_pmfc_Scripts.Triggers.Triggers_Lib import *
from Fretta_pmfc_Scripts.Triggers.utils import *
from fwd_scripts.fwd_config import *
from XVerification import *
import collections
import time
#from autoparser import pyparse
from xNetworkEvents import *

global event
event = Events()

tcl.eval('package require Mpexpr')

class ConfigError(Exception):
    """raised if any config failed"""

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
#the default severity is debug
log = XLog(level=logging.DEBUG)

def get_test_topo(test_topo):
    global g_topo_data
    global IntfList
    global IterCnt
    global RepeatCnt
    global TraffPortList
    global ProcessList
    global tftpPath
    global tftp_path
    global tftp_addr
    #global LcList
    global rtrsL
    global CliList
    global clear_cli_list
    global ShowCmdList
    global MemLeakProcessList
    global ControllerList
    global Traffic
    global ConvergTime
    global Location
    global response
    global config
    global unconfig
    response = collections.OrderedDict()
    #LcList =[]
    rtrsL = []
    IntfList = []
    ShowCmdList = []
    TraffPortList = []
    ProcessList = []
    CliList = []
    clear_cli_list = []
    MemLeakProcessList = []
    ControllerList = []
    
    g_topo_data = {}
    g_topo_data['R1'] = test_topo['R1']
    g_topo_data['R1a'] = test_topo['R1a']
    g_topo_data['R2'] = test_topo['R2']
    IterCnt = test_topo['IterCnt']
    RepeatCnt = test_topo['RepeatCnt']
    CliList = test_topo['CliList']
    config = test_topo['config']
    unconfig = test_topo['unconfig']
    clear_cli_list = test_topo['clear_cli_list']
    #LcList = test_topo['LcList']
    Traffic = test_topo['Traffic']
    IntfList = test_topo['IntfList']
    ConvergTime = test_topo['ConvergTime']
    ControllerList = test_topo['ControllerList']
    TraffPortList = test_topo['TraffPortList']
    ProcessList = test_topo['ProcessList']
    Location = test_topo['Location']
    ShowCmdList = test_topo['ShowCmdList']
    MemLeakProcessList = test_topo['MemLeakProcessList']
    tftp_path = test_topo['tftp_path']
    tftp_addr= test_topo['tftp_addr']
    tftpPath = tftp_addr + tftp_path

global GV
GV = {}

def verify_show_logging_context(rtr):
    """ Verify show logging and show context. Raise Exception in faliure"""

    success = True

    try:
        rtr.execute('show logging')
        log.info("Show logging execution passed")
    except Exception as err:
        log.info(err)
        log.error('show logging execution failed')
        log.error("Exception type: {}".format(str(err)))
        wait_time = 300
        log.info("waiting for {}s, suspecting connection timedout"
                  .format(wait_time))
        time.sleep(wait_time)
        success = False

    command = r'''show logging | include \"CPUHOG|MALLOCFAIL|Traceback'''
    command += r'''|_ERROR|abnormally|FATAL\"'''
    logging_out = rtr.execute(command)
    ptrn = "(CPUHOG.*)|(MALLOCFAIL.*)|(Traceback.*)|(_ERROR.*)|(abnormally.*)|(FATAL.*)|(restart.*)"
    flag = 0
    for line in logging_out.split('\r\n'):
        matchObj = re.search("show logging.*", line, re.I)
        if matchObj:
            continue
        matchObj = re.search(".*UTC", line, re.I)
        if matchObj:
            continue
        matchObj = re.search("0\/RP[0|1]\/CPU0.*#", line, re.I)
        if matchObj:
            continue
        matchObj = re.search(ptrn, line, re.I)
        if matchObj:
            match = re.search(r'L2-CFM-5-CCM_ERROR_CCMS_MISSED', line, re.I)
            if not match:
                flag += 1
    if flag:
        msg = "Observed error messages in show logging. "
        log.error(msg)
        processes = set()
        for line in logging_out.split('\r\n'):
            matchObj = re.search(r'\(PID\=(\d+)\).*Traceback.*', line, re.I)
            if matchObj:
                processes.add(matchObj.group(1))
        for pid in processes:
            rtr.execute("show processes %s" % pid)
            rtr.execute("show dll pid %s" % pid)

        success = False
    else:
        msg = "No error messages observed in show logging"
        log.info(msg)

    try:
        pyRes = rtr.verify('show context location all', parse_only = 'yes', parser_type = 'textfsm')

        pids = list()
        if 'pid' in pyRes:
            pids = pyRes['pid'].keys()
            crashnames = list()
            for pid in pids:
                crashnames.append(pyRes['pid'][pid]['name'])

            msg = ('Cores/crashes %s Found. ' % crashnames)
            log.error(msg)
            success = False
        else:
            log.info("No Crashes Found")
    except:
        msg = ('Failed to parse show context in the router %s ' % rtr)
        log.error(msg)
        success = False

    try:
        rtr.transmit('admin\r')
        rtr.receive('sysadmin-vm.*')
        rtr.execute('terminal length 0')

        pyRes = rtr.verify('show context location all', parse_only = 'yes', parser_type = 'textfsm')

        pids = list()
        if 'pid' in pyRes:
            pids = pyRes['pid'].keys()
            crashnames = list()
            for pid in pids:
                crashnames.append(pyRes['pid'][pid]['name'])

            msg = ('Cores/crashes %s Found. ' % crashnames)
            log.error(msg)
            success = False
        else:
            log.info("No Crashes Found")

        rtr.execute("clear context location all")

        rtr.transmit('exit\r')
        if not rtr.receive(r'RP/0/RP[0-1].*\#', timeout = 5):
            log.error('Router is not in xr prompt')
            success = False
    except:
        msg = ('Failed to parse show context in the router %s ' % rtr)
        log.error(msg)
        success = False

    try:
        rtr.execute("clear logging")
        rtr.execute("clear context location all")
        log.info("Clear logging and context passed")
    except:
        msg = ("Clear logging and context failed. ")
        log.error(msg)
        success = False

    return success


class common_setup(aetest.CommonSetup):

    
    """
    TAG_MAP:
        title:          Fretta PM FC COMMON SETUP
        descr:          Testsuite for Fretta PM FC NCS5500
        platform:       NCS5500
        min-sw-ver:     6.1.0
        test-phase:     sanity-test
        modular-pkg:    fretta-platform
        test-type:      functionality
        test-component: ['ipv4-fwd','ipv6-fwd']
        sw-component:   fretta-l3fib
        topology:       tgen-fretta-fretta-tgen
        tgn-type:       spirent
        link-type:      100G
        customer:       all
        cdets-attribute: auto-fwd-ip
        run_time:   90
        projects:   DevTest
    """
    
    global testCaseName
    testCaseName=''
    @aetest.subsection
    def connect_to_Fretta(self):
        """ common setup subsection: connecting devices """
        global g_topo_data

        log.info(banner("Common Setup: Connection to devices"))
        
        #self.script_args['testStep'] = 1
        get_test_topo(self.script_args)
        #g_test_data = get_test_data_from_yaml(self.script_args['test_data_file'])
        
        rtr1_name=g_topo_data['R1']        
        rtr1=routers[rtr1_name]
        rtr2_name = g_topo_data['R2']
        rtr2 = routers[rtr2_name]
        
        # Step 1
        self.script_args['testStep'] = 1
        log.info(banner("STEP %s: Device Connection" %
                        (self.script_args['testStep'])))


        # Create instance of device R1
        device_uut = self.script_args['R1']
        self.script_args['uut'] = self.script_args[
            'testbed'].devices[device_uut]

        tcl.eval('set csccon_default(clear_config_inconsistancy) 0')
        
        self.script_args['uut'].connect()
        log.info("STEP %s: Device Connection Passed" %
                 (self.script_args['testStep']))
        rtr1.execute("terminal length 500")
        rtr1.execute("terminal width 500")
        response["Clear logging buffer \[confirm\] \[y\/n\] \:"] = "econ_sendline y;exp_continue"
        rtr1.execute("clear logging", reply=response)
        rtr1.execute("clear context", reply=response)


            # self.script_args['testStep'] = 2
            # log.info(banner("STEP %s: Device Connection" %
            #                 (self.script_args['testStep'])))
            #
            # device_uut_r2 = self.script_args['R2']
            # self.script_args['uut_r2'] = self.script_args[
            #     'testbed'].devices[device_uut_r2]
            # tcl.eval('set csccon_default(clear_config_inconsistancy) 0')
            # self.script_args['uut_r2'].connect()
            # log.info("STEP %s: Device Connection Passed" %
            #          (self.script_args['testStep']))
            # rtr2.execute("terminal length 500")
            # rtr2.execute("terminal width 500")
            # response["Clear logging buffer \[confirm\] \[y\/n\] \:"] = "econ_sendline y;exp_continue"
            # rtr2.execute("clear logging", reply=response)
            # rtr2.execute("clear context", reply=response)


#######################################################################
###                          TESTCASE BLOCK                         ###
#######################################################################
#
# Place your code that implements the test steps for the test case.
# Each test may or may not contains sections:
#           setup   - test preparation
#           test    - test action

##########################################

class IntfFlap(aetest.Testcase):
    '''
    TAG_MAP:
       title: IntfFlap
       descr: This test case covers shut / no shut of Interfaces.
       platform: NCS5500
       min-sw-ver: 6.1.0
       test-phase: dev-test
       modular-pkg: fretta-platform
       test-type: functionality
       test-component: ['coherent']
       sw-component: fretta-coherent
       topology: tgen-fretta-fretta-tgen
       tgn-type: spirent
       link-type: 100G
       customer: all
       cdets-attribute:  auto-fwd-ip
    '''
    execution_group = 'ipv4' 

    """ This is user Testcases section """
    @aetest.setup
    def prepare_for_subtest(self):
        """ Testcase Setup section """
        log.info(banner(" Aetest Testcase Execution "))

    @aetest.test
    def Shut_NoShut(self):
        #embed()
        testCaseName="Scale_Stress1"
        global g_topo_data,g_test_data
        global GV
        #global LcList
        rtr1_name=g_topo_data['R1']
        rtr=routers[rtr1_name]
        #embed()
        rtr.execute("terminal length 500")
        rtr.execute("terminal width 500")
        
        #capture the memory before trigger
        log.info("Start memory comparision on both routers")
        rtr.execute("show memory compare start")
        rtr.execute("show memory compare start location %s"%Location)
                
        for count in range(IterCnt):
            log.info("shut/no shut of HunGig Interface in Scale")
            #shut
            result = HugShutNoShut(device=rtr,ports=IntfList,mode="shut")
            if result == 1:
                log.info ("Shutting of HundGig Interfaces are successful")
            else:
                log.info ("Shutting of HundGig Interface are not successfull")
                #self.failed() 
                #pdb.set_trace()
            #no shut
            time.sleep(90)
            result = HugShutNoShut(device=rtr,ports=IntfList,mode="nosh")
            if result == 1:
                log.info ("No Shut of HundGig Interfaces are successful")
            else:
                log.info ("No Shut of HundGig Interface are not successfull")
                #self.failed() 
                #pdb.set_trace()

            time.sleep(60)
                
            log.info("Verify HundGig Interface comes UP and \
        		traffic is passing through")
        
            try: 
                rtr.verify('show ipv4 interface Bundle-Ether12001 brief',up_intfs=IntfList)
                rtr.verify ('show ipv4 interface Bundle-Ether11001 brief', up_intfs=IntfList)
            except:
                log.info('Router Interfaces Status Check Failed')
                #self.failed()
                #pdb.set_trace()
            try:
                rtr.execute ("show ethernet cfm peer meps")
                rtr.execute ("show l2vpn forwarding bridge-domain mac-address location 0/6/CPU0 | u w l")
                rtr.execute ("sho l2vpn mac-learning mac all location 0/6/CPU0  | u w l")
                # "sho l2vpn mac-learning mac all location 0/0/CPU0 "
            except:
                log.info ('show policy-map interface TenGigE0/4/0/28/1 input failed')
        
            if Traffic == "on":
                result=StatsIncrementCheck(rtr=rtr,intfL=IntfList)
                if result=="False":
                    log.info("Issue in traffic recovery after Interface shut / no shut")
                    #self.failed() 
                    #pdb.set_trace()  
                else:
                    log.info("Traffic started resuming properly after shut / no shut")
            

        sleep(120) # waiting for 120 second for expected memory to release
        log.info("Stop memory comparision on both routers")
        log.info("Start memory comparision on both routers")
        rtr.execute("show memory compare end")
        rtr.execute("show memory compare end location %s"%Location)
        log.info("Capture the memory usage and analyse the leak")
        #R1
        fail_cnt=0
        for process in MemLeakProcessList:
            result = CompareMemory(rtr,process,Location)
            if result == False:
                log.info("There is some issue in finding memory info for %s"%process)
                fail_cnt=fail_cnt+1
            elif result == "leak":
                log.info("Idenfied memory leak for %s"%process)
                fail_cnt=fail_cnt+1
            elif result == True:
                log.info("There are no leak identified for %s"%process)
        if fail_cnt >= 1:
            log.info("Issue with memory usage after trigger.Need to analyse the core file later on R1")

        log.info("Checking the Tracebacks,Errors in show logging and show context for crash")
        health_check = verify_show_logging_context(rtr)
        if not (health_check):
            log.error("show logging and context failed")
            pdb.set_trace()
       
    @aetest.cleanup
    def clean_this_tc(self):
        """ Testcase cleanup section """
        log.info("No Changes were made in setup section. \
        		Hence clean up is not required")
        log.info("Pass testcase cleanup")

#########################################################

class RepatedIntfFlap(aetest.Testcase):
    '''
    TAG_MAP:
       title: RepatedIntfFlap
       descr: This test case covers Repeated shut / no shut of Interfaces.
       platform: NCS5500
       min-sw-ver: 6.1.0
       test-phase: dev-test
       modular-pkg: fretta-platform
       test-type: functionality
       test-component: ['coherent']
       sw-component: fretta-coherent
       topology: tgen-fretta-fretta-tgen
       tgn-type: spirent
       link-type: 100G
       customer: all
       cdets-attribute:  auto-fwd-ip
    '''
    execution_group = 'ipv4' 

    """ This is user Testcases section """
    @aetest.setup
    def prepare_for_subtest(self):
        """ Testcase Setup section """
        log.info(banner(" Aetest Testcase Execution "))

    @aetest.test
    def Shut_NoShut(self):
        #embed()
        testCaseName="Scale_Stress1"
        global g_topo_data,g_test_data
        global GV
        #global LcList
        rtr1_name=g_topo_data['R1']
        rtr=routers[rtr1_name]
        rtr.execute("terminal length 500")
        rtr.execute("terminal width 500")
        
        log.info("Start memory comparision on both routers")
        rtr.execute("show memory compare start")
        rtr.execute("show memory compare start location %s"%Location)
                
        for count in range(IterCnt):
            log.info("shut/no shut of HunGig Interface in Scale")
            #capture the memory before trigger
            #shut
            result = HugShutNoShut(device=rtr,ports=IntfList,mode="flap",flp_cnt=RepeatCnt)
            if result == 1:
                log.info ("Flapping of HundGig Interfaces are successful")
            else:
                log.info ("Flapping of HundGig Interface are not successfull")
                #self.failed() 
                #pdb.set_trace()

            log.info("Verify HundGig Interface comes UP and \
        	    traffic is passing through")
        
            try: 
                rtr.verify('show ipv4 interface brief',up_intfs=IntfList)
            except:
                log.info('Router Interfaces Status Check Failed')
                #self.failed()
                #pdb.set_trace()
        
            if Traffic == "on":
                result=StatsIncrementCheck(rtr=rtr,intfL=IntfList)
                if result=="False":
                    log.info("Issue in traffic recovery after Interface shut / no shut")
                    #self.failed()  
                    #pdb.set_trace() 
                else:
                    log.info("Traffic started resuming properly after repeated shut / no shut")
            
        sleep(120) # waiting for 120 second for expected memory to release
        log.info("Stop memory comparision on both routers")
        log.info("Start memory comparision on both routers")
        rtr.execute("show memory compare end")
        rtr.execute("show memory compare end location %s"%Location)
        log.info("Capture the memory usage and analyse the leak")
        #R1
        fail_cnt=0
        for process in MemLeakProcessList:
            result = CompareMemory(rtr,process,Location)
            if result == False:
                log.info("There is some issue in finding memory info for %s"%process)
                fail_cnt=fail_cnt+1
            elif result == "leak":
                log.info("Idenfied memory leak for %s"%process)
                fail_cnt=fail_cnt+1
            elif result == True:
                log.info("There are no leak identified for %s"%process)
        if fail_cnt >= 1:
            log.info("Issue with memory usage after trigger.Need to analyse the core file later on R1")

        log.info("Checking the Tracebacks,Errors in show logging and show context for crash")
        health_check = verify_show_logging_context(rtr)
        if not (health_check):
            log.error("show logging and context failed")
            pdb.set_trace()
       
    @aetest.cleanup
    def clean_this_tc(self):
        """ Testcase cleanup section """
        log.info("No Changes were made in setup section. \
        		Hence clean up is not required")
        log.info("Pass testcase cleanup")

##################################################################

class IntfFlapBulk(aetest.Testcase):
    '''
    TAG_MAP:
       title: IntfFlapInBulk
       descr: This test case covers shut / no shut of Interfaces.
       platform: NCS5500
       min-sw-ver: 6.1.0
       test-phase: dev-test
       modular-pkg: fretta-platform
       test-type: functionality
       test-component: ['coherent']
       sw-component: fretta-coherent
       topology: tgen-fretta-fretta-tgen
       tgn-type: spirent
       link-type: 100G
       customer: all
       cdets-attribute:  auto-fwd-ip
    '''
    execution_group = 'ipv4' 

    """ This is user Testcases section """
    @aetest.setup
    def prepare_for_subtest(self):
        """ Testcase Setup section """
        log.info(banner(" Aetest Testcase Execution "))

    @aetest.test
    def Shut_NoShut(self):
        #embed()
        testCaseName="Scale_Stress1"
        global g_topo_data,g_test_data
        global GV
        #global LcList
        rtr1_name=g_topo_data['R1']
        rtr1=routers[rtr1_name]
        rtr2_name = g_topo_data['R2']
        rtr2 = routers[rtr2_name]
        rtr1.execute("terminal length 500")
        rtr1.execute("terminal width 500")
        rtr2.execute("terminal length 500")
        rtr2.execute("terminal width 500")
        
         #capture the memory before trigger
        log.info("Start memory comparision on both routers")
        rtr1.execute("show memory compare start")
        rtr1.execute("show memory compare start location %s"%Location)
        log.info("Start memory comparision on both routers")
        rtr2.execute("show memory compare start")
        rtr2.execute("show memory compare start location 0/0/cpu0")
                
        for count in range(IterCnt):
            log.info("shut/no shut of HunGig Interface in Bulk for all ports in single commit")
            #shut
            result = HugShutNoShut(device=rtr1,ports=IntfList,mode="shut_blk")
            if result == 1:
                log.info ("Bulk Shut of HundGig Interfaces are successful")
            else:
                log.info ("Bulk Shut of HundGig Interface are not successfull")
                #self.failed() 
                #pdb.set_trace()
            #no shut
            result = HugShutNoShut(device=rtr1,ports=IntfList,mode="nosh_blk")
            if result == 1:
                log.info ("Bulk no shut of HundGig Interfaces are successful")
            else:
                log.info ("Bulk no shut of HundGig Interface are not successfull")
                #self.failed() 
                #pdb.set_trace()
                
            log.info("Verify HundGig Interface comes UP and \
        		traffic is passing through")
        
            try: 
                rtr1.verify('show ipv4 interface brief',up_intfs=IntfList)
            except:
                log.info('Router Interfaces Status Check Failed')
                #self.failed()
                #pdb.set_trace()
        
            if Traffic == "on":
                result=StatsIncrementCheck(rtr=rtr1,intfL=IntfList)
                if result=="False":
                    log.info("Issue in traffic recovery after Interface shut / no shut")
                    #self.failed()  
                    #pdb.set_trace() 
                else:
                    log.info("Traffic started resuming properly after shut / no shut")
            

        sleep(120) # waiting for 120 second for expected memory to release
        log.info("Stop memory comparision on both routers")
        log.info("Start memory comparision on both routers")
        rtr1.execute("show memory compare end")
        rtr1.execute("show memory compare end location %s"%Location)
        log.info("Capture the memory usage and analyse the leak")
        #R1
        fail_cnt=0
        for process in MemLeakProcessList:
            result = CompareMemory(rtr1,process,Location)
            if result == False:
                log.info("There is some issue in finding memory info for %s"%process)
                fail_cnt=fail_cnt+1
            elif result == "leak":
                log.info("Idenfied memory leak for %s"%process)
                fail_cnt=fail_cnt+1
            elif result == True:
                log.info("There are no leak identified for %s"%process)
        if fail_cnt >= 1:
            log.info("Issue with memory usage after trigger.Need to analyse the core file later on R1")

        log.info("Checking the Tracebacks,Errors in show logging and show context for crash")
        health_check = verify_show_logging_context(rtr1)
        if not (health_check):
            log.error("show logging and context failed")
            pdb.set_trace()
       
    @aetest.cleanup
    def clean_this_tc(self):
        """ Testcase cleanup section """
        log.info("No Changes were made in setup section. \
        		Hence clean up is not required")
        log.info("Pass testcase cleanup")

##################################################################

class RepatedIntfFlapBulk(aetest.Testcase):
    '''
    TAG_MAP:
       title: RepatedIntfFlap
       descr: This test case covers Repeated bulk shut / no shut of Interfaces.
       platform: NCS5500
       min-sw-ver: 6.1.0
       test-phase: dev-test
       modular-pkg: fretta-platform
       test-type: functionality
       test-component: ['coherent']
       sw-component: fretta-coherent
       topology: tgen-fretta-fretta-tgen
       tgn-type: spirent
       link-type: 100G
       customer: all
       cdets-attribute:  auto-fwd-ip
    '''
    execution_group = 'ipv4' 

    """ This is user Testcases section """
    @aetest.setup
    def prepare_for_subtest(self):
        """ Testcase Setup section """
        log.info(banner(" Aetest Testcase Execution "))

    @aetest.test
    def Shut_NoShut(self):
        #embed()
        testCaseName="Scale_Stress1"
        global g_topo_data,g_test_data
        global GV
        #global LcList
        rtr1_name=g_topo_data['R1']
        rtr=routers[rtr1_name]
        rtr.execute("terminal length 500")
        rtr.execute("terminal width 500")
        
        log.info("Start memory comparision on both routers")
        rtr.execute("show memory compare start")
        rtr.execute("show memory compare start location %s"%Location)
                
        for count in range(IterCnt):
            log.info("shut/no shut of HunGig Interface in Scale")
            #capture the memory before trigger
            #shut
            result = HugShutNoShut(device=rtr,ports=IntfList,mode="flap",flp_cnt=RepeatCnt)
            if result == 1:
                log.info ("Flapping of HundGig Interfaces are successful")
            else:
                log.info ("Flapping of HundGig Interface are not successfull")
                #self.failed() 
                #pdb.set_trace()

            log.info("Verify HundGig Interface comes UP and \
        	    traffic is passing through")
        
        
        try: 
            rtr.verify('show ipv4 interface brief',up_intfs=IntfList)
        except:
            log.info('Router Interfaces Status Check Failed')
            #self.failed()
            #pdb.set_trace()
        
        if Traffic == "on":
            result=StatsIncrementCheck(rtr=rtr,intfL=IntfList)
            if result=="False":
                log.info("Issue in traffic recovery after Interface shut / no shut")
                #self.failed()   
                #pdb.set_trace()
            else:
                log.info("Traffic started resuming properly after repeated bulk shut / no shut")
                        
        sleep(120) # waiting for 120 second for expected memory to release
        log.info("Stop memory comparision on both routers")
        log.info("Start memory comparision on both routers")
        rtr.execute("show memory compare end")
        rtr.execute("show memory compare end location %s"%Location)
        log.info("Capture the memory usage and analyse the leak")
        #R1
        fail_cnt=0
        for process in MemLeakProcessList:
            result = CompareMemory(rtr,process,Location)
            if result == False:
                log.info("There is some issue in finding memory info for %s"%process)
                fail_cnt=fail_cnt+1
            elif result == "leak":
                log.info("Idenfied memory leak for %s"%process)
                fail_cnt=fail_cnt+1
            elif result == True:
                log.info("There are no leak identified for %s"%process)
        if fail_cnt >= 1:
            log.info("Issue with memory usage after trigger.Need to analyse the core file later on R1")

        log.info("Checking the Tracebacks,Errors in show logging and show context for crash")
        health_check = verify_show_logging_context(rtr)
        if not (health_check):
            log.error("show logging and context failed")
            pdb.set_trace()
       
    @aetest.cleanup
    def clean_this_tc(self):
        """ Testcase cleanup section """
        log.info("No Changes were made in setup section. \
        		Hence clean up is not required")
        log.info("Pass testcase cleanup")
        

##################################################################

class ConfigUnconfig(aetest.Testcase):
    '''
    TAG_MAP:
       title: ConfigUnconfig
       descr: This test case covers Config & Rollback.
       platform: NCS5500
       min-sw-ver: 6.1.0
       test-phase: dev-test
       modular-pkg: fretta-platform
       test-type: functionality
       test-component: ['coherent']
       sw-component: fretta-coherent
       topology: tgen-fretta-fretta-tgen
       tgn-type: spirent
       link-type: 100G
       customer: all
       cdets-attribute:  auto-fwd-ip
    '''
    execution_group = 'ipv4' 

    """ This is user Testcases section """
    @aetest.setup
    def prepare_for_subtest(self):
        """ Testcase Setup section """
        log.info(banner(" Aetest Testcase Execution "))

    @aetest.test
    def Shut_NoShut(self):
        #embed()
        testCaseName="Scale_Stress1"
        global g_topo_data,g_test_data
        global GV
        #global LcList
        rtr1_name=g_topo_data['R1']
        rtr1=routers[rtr1_name]
        rtr1.execute("terminal length 500")
        rtr1.execute("terminal width 500")
        
         #capture the memory before trigger
        log.info("Start memory comparision on both routers")
        rtr1.execute("show memory compare start")
        rtr1.execute("show memory compare start location %s"%Location)

        # rtr2_name = g_topo_data['R2']
        # rtr2 = routers[rtr2_name]
        # rtr2.execute("terminal length 500")
        # rtr2.execute("terminal width 500")
        #
        # # capture the memory before trigger
        # log.info("Start memory comparision on both routers")
        # rtr2.execute("show memory compare start")
        # rtr2.execute("show memory compare start location 0/0/CPU0")
                
        config_strR1=""
        # for clis in CliList:
        #     config_strR1+= clis
        # rtr.config(config_strR1)
        # sleep(15)

        for count in range(IterCnt):
            for rtr in [rtr1]:
                config_strR1 = config
                unconfig_strR1 = unconfig
                rtr.config(unconfig_strR1)
                sleep(10)
                rtr.execute("rollback configuration last 1")
                sleep (10)
                
                pin = rtr.execute("ping 57.1.200.1")
                match = re.search(r'Success rate is (?P<rate>\d+) percent', pin)
                success_rate = match.group('rate')
                log.info('Ping {} with success rate of {}%'.format("66.3.12.1", success_rate,))
                #rtr.execute("show policy-map interface bundle-ether 3300 input")
                #rtr.execute ("show policy-map interface bundle-ether 3300 output")

                    
        if Traffic == "on":
            result=StatsIncrementCheck(rtr=rtr,intfL=IntfList)
            if result=="False":
                log.info("Issue in traffic recovery after repeated config & rollback")
                #self.failed()   
                #pdb.set_trace()
            else:
                log.info("Traffic started resuming properly after repeated config & rollback")
            
        sleep(120) # waiting for 120 second for expected memory to release
        log.info("Stop memory comparision on both routers")
        log.info("Start memory comparision on both routers")
        rtr1.execute("show memory compare end")
        rtr1.execute("show memory compare end location %s"%Location)
        log.info("Capture the memory usage and analyse the leak")
        #R1
        fail_cnt=0
        for process in MemLeakProcessList:
            result = CompareMemory(rtr,process,Location)
            if result == False:
                log.info("There is some issue in finding memory info for %s"%process)
                fail_cnt=fail_cnt+1
            elif result == "leak":
                log.info("Idenfied memory leak for %s"%process)
                fail_cnt=fail_cnt+1
            elif result == True:
                log.info("There are no leak identified for %s"%process)
        if fail_cnt >= 1:
            log.info("Issue with memory usage after trigger.Need to analyse the core file later on R1")

        log.info("Checking the Tracebacks,Errors in show logging and show context for crash")
        health_check = verify_show_logging_context(rtr)
        if not (health_check):
            log.error("show logging and context failed")
            pdb.set_trace()
       
    @aetest.cleanup
    def clean_this_tc(self):
        """ Testcase cleanup section """
        log.info("No Changes were made in setup section. \
        		Hence clean up is not required")
        log.info("Pass testcase cleanup")

##################################################################


class ShowCommands(aetest.Testcase):
    '''
    TAG_MAP:
       title: ShowCommands
       descr: This test case covers ShowCommands execution and look for memory leaks.
       platform: NCS5500
       min-sw-ver: 6.1.0
       test-phase: dev-test
       modular-pkg: fretta-platform
       test-type: functionality
       test-component: ['coherent']
       sw-component: fretta-coherent
       topology: tgen-fretta-fretta-tgen
       tgn-type: spirent
       link-type: 100G
       customer: all
       cdets-attribute:  auto-fwd-ip
    '''
    execution_group = 'ipv4' 

    """ This is user Testcases section """
    @aetest.setup
    def prepare_for_subtest(self):
        """ Testcase Setup section """
        log.info(banner(" Aetest Testcase Execution "))

    @aetest.test
    def Shut_NoShut(self):
        #embed()
        testCaseName="Scale_Stress1"
        global g_topo_data,g_test_data
        global GV
        #global LcList
        rtr1_name=g_topo_data['R1']
        rtr=routers[rtr1_name]
        rtr.execute("terminal length 500")
        rtr.execute("terminal width 500")
        
         #capture the memory before trigger
        log.info("Start memory comparision on both routers")
        rtr.execute("show memory compare start")
        rtr.execute("show memory compare start location %s"%Location)
                
        config_strR1=""
          
        for count in range(IterCnt):
            log.info("Execute show commands one by one")
            for cli in ShowCmdList:
                rtr.execute("%s"%cli) 
            
        sleep(120) # waiting for 120 second for expected memory to release
        log.info("Stop memory comparision on both routers")
        log.info("Start memory comparision on both routers")
        rtr.execute("show memory compare end")
        rtr.execute("show memory compare end location %s"%Location)
        log.info("Capture the memory usage and analyse the leak")
        #R1
        fail_cnt=0
        for process in MemLeakProcessList:
            result = CompareMemory(rtr,process,Location)
            if result == False:
                log.info("There is some issue in finding memory info for %s"%process)
                fail_cnt=fail_cnt+1
            elif result == "leak":
                log.info("Idenfied memory leak for %s"%process)
                fail_cnt=fail_cnt+1
            elif result == True:
                log.info("There are no leak identified for %s"%process)
        if fail_cnt >= 1:
            log.info("Issue with memory usage after trigger.Need to analyse the core file later on R1")

        log.info("Checking the Tracebacks,Errors in show logging and show context for crash")
        health_check = verify_show_logging_context(rtr)
        if not (health_check):
            log.error("show logging and context failed")
            pdb.set_trace()
    @aetest.cleanup
    def clean_this_tc(self):
        """ Testcase cleanup section """
        log.info("No Changes were made in setup section. \
        		Hence clean up is not required")
        log.info("Pass testcase cleanup")

##################################################################
            
class CommitReplaceRollBack(aetest.Testcase):
    '''
    TAG_MAP:
       title: CommitReplaceRollBack
       descr: This test case covers CommitReplaceRollBack.
       platform: NCS5500
       min-sw-ver: 6.1.0
       test-phase: dev-test
       modular-pkg: fretta-platform
       test-type: functionality
       test-component: ['coherent']
       sw-component: fretta-coherent
       topology: tgen-fretta-fretta-tgen
       tgn-type: spirent
       link-type: 100G
       customer: all
       cdets-attribute:  auto-fwd-ip
    '''
    execution_group = 'ipv4' 

    """ This is user Testcases section """
    @aetest.setup
    def prepare_for_subtest(self):
        """ Testcase Setup section """
        log.info(banner(" Aetest Testcase Execution "))

    @aetest.test
    def Shut_NoShut(self):
        #embed()
        testCaseName="Scale_Stress1"
        global g_topo_data,g_test_data
        global GV
        #global LcList
        rtr1_name=g_topo_data['R1']
        rtr=routers[rtr1_name]
        rtr.execute("terminal length 500")
        rtr.execute("terminal width 500")
        
         #capture the memory before trigger
        log.info("Start memory comparision on both routers")
        rtr.execute("show memory compare start")
        rtr.execute("show memory compare start location %s"%Location)
                
        config_strR1=""
          
        for count in range(IterCnt):
            log.info('applying configuration')
            rtr.transmit('configure terminal\r')
            rtr.receive(r'#',timeout=20)
            rtr.transmit('no l2vpn\r')
            #rtr.receive(r':',timeout=20)
            #rtr.transmit('yes\r')
            rtr.receive(r'#',timeout=20)
            rtr.transmit('commit\r')
            rtr.receive(r'#', timeout=240)
            rtr.transmit('end\r')
            rtr.receive(r'#', timeout=20)
            sleep(240)
            rtr.transmit('rollback configuration last 1\r')
            rtr.receive(r'#',timeout=240)
            sleep(240)
            output=rtr.receive_buffer()

            if re.search('Failed to commit one or more configuration items', output):
                raise Exception('configuration apply failed')
                #pdb.set_trace()
            else:
                log.info('configuration applied successfully')
                
            log.info('waiting for Convergence time for traffic recovery')
            sleep(ConvergTime) 
            
            #sleep(120) # waiting for 120 second for expected memory to release
            log.info("Stop memory comparision on both routers")
            log.info("Start memory comparision on both routers")
            rtr.execute("show memory compare end")
            rtr.execute("show memory compare end location %s"%Location)
            log.info("Capture the memory usage and analyse the leak")
            #R1
            fail_cnt=0
            for process in MemLeakProcessList:
                result = CompareMemory(rtr,process,Location)
                if result == False:
                    log.info("There is some issue in finding memory info for %s"%process)
                    fail_cnt=fail_cnt+1
                elif result == "leak":
                    log.info("Idenfied memory leak for %s"%process)
                    fail_cnt=fail_cnt+1
                elif result == True:
                    log.info("There are no leak identified for %s"%process)
            if fail_cnt >= 1:
                log.info("Issue with memory usage after trigger.Need to analyse the core file later on R1")
            
            if Traffic == "on":
                result=StatsIncrementCheck(rtr=rtr,intfL=IntfList)
                if result=="False":
                    log.info("Issue in traffic recovery after commit replace and rollback")
                    #self.failed()  
                    #pdb.set_trace() 
                else:
                    log.info("Traffic started resuming properly after commit replace and rollback")

        log.info("Checking the Tracebacks,Errors in show logging and show context for crash")
        health_check = verify_show_logging_context(rtr)
        if not (health_check):
            log.error("show logging and context failed")
            pdb.set_trace()
    @aetest.cleanup
    def clean_this_tc(self):
        """ Testcase cleanup section """
        log.info("No Changes were made in setup section. \
        		Hence clean up is not required")
        log.info("Pass testcase cleanup")


###############################################################################################

class RepCommitReplaceRollBack(aetest.Testcase):
    '''
    TAG_MAP:
       title: RepCommitReplaceRollBack
       descr: This test case covers Repeated CommitReplace and Roll Back.
       platform: NCS5500
       min-sw-ver: 6.1.0
       test-phase: dev-test
       modular-pkg: fretta-platform
       test-type: functionality
       test-component: ['coherent']
       sw-component: fretta-coherent
       topology: tgen-fretta-fretta-tgen
       tgn-type: spirent
       link-type: 100G
       customer: all
       cdets-attribute:  auto-fwd-ip
    '''
    execution_group = 'ipv4' 

    """ This is user Testcases section """
    @aetest.setup
    def prepare_for_subtest(self):
        """ Testcase Setup section """
        log.info(banner(" Aetest Testcase Execution "))

    @aetest.test
    def Shut_NoShut(self):
        #embed()
        testCaseName="Scale_Stress1"
        global g_topo_data,g_test_data
        global GV
        #global LcList
        rtr1_name=g_topo_data['R1']
        rtr=routers[rtr1_name]
        rtr.execute("terminal length 500")
        rtr.execute("terminal width 500")
        
         #capture the memory before trigger
        log.info("Start memory comparision on both routers")
        rtr.execute("show memory compare start")
        rtr.execute("show memory compare start location %s"%Location)
                
        config_strR1=""
          
        for count in range(IterCnt):
            log.info('applying configuration')
            #cmd='load ' + Startup_Config + '\r'
            rtr.transmit('configure terminal\r')
            rtr.receive(r'#',timeout=20)
            rtr.transmit('commit replace\r')
            rtr.receive(r':',timeout=20)
            rtr.transmit('yes\r')
            rtr.receive(r'#',timeout=20)
            rtr.transmit('exit\r') 
            rtr.transmit('rollback configuration last 1\r')
            rtr.receive(r'#',timeout=20)
            output=rtr.receive_buffer()

            if re.search('Failed to commit one or more configuration items', output):
                raise Exception('configuration apply failed')
                #pdb.set_trace()
            else:
                log.info('configuration applied successfully')
                
        log.info('waiting for Convergence time for traffic recovery')
        sleep(ConvergTime) 
            
        #sleep(120) # waiting for 120 second for expected memory to release
        log.info("Stop memory comparision on both routers")
        log.info("Start memory comparision on both routers")
        rtr.execute("show memory compare end")
        rtr.execute("show memory compare end location %s"%Location)
        log.info("Capture the memory usage and analyse the leak")
        #R1
        fail_cnt=0
        for process in MemLeakProcessList:
            result = CompareMemory(rtr,process,Location)
            if result == False:
                log.info("There is some issue in finding memory info for %s"%process)
                fail_cnt=fail_cnt+1
            elif result == "leak":
                log.info("Idenfied memory leak for %s"%process)
                fail_cnt=fail_cnt+1
            elif result == True:
                log.info("There are no leak identified for %s"%process)
        if fail_cnt >= 1:
            log.info("Issue with memory usage after trigger.Need to analyse the core file later on R1")
            
        if Traffic == "on":
            result=StatsIncrementCheck(rtr=rtr,intfL=IntfList)
            if result=="False":
                log.info("Issue in traffic recovery after repeated commit replace and rollback")
                #self.failed()   
                #pdb.set_trace()
            else:
                log.info("Traffic started resuming properly after repeated commit replace and rollback")

        log.info("Checking the Tracebacks,Errors in show logging and show context for crash")
        health_check = verify_show_logging_context(rtr)
        if not (health_check):
            log.error("show logging and context failed")
            pdb.set_trace()
       
    @aetest.cleanup
    def clean_this_tc(self):
        """ Testcase cleanup section """
        log.info("No Changes were made in setup section. \
        		Hence clean up is not required")
        		
###################################################################################################

class ContinuousLcReload(aetest.Testcase):
    '''
    TAG_MAP:
       title: ContinuousLcReload
       descr: This test case covers Continuous LC Reload.
       platform: NCS5500
       min-sw-ver: 6.1.0
       test-phase: dev-test
       modular-pkg: fretta-platform
       test-type: functionality
       test-component: ['coherent']
       sw-component: fretta-coherent
       topology: tgen-fretta-fretta-tgen
       tgn-type: spirent
       link-type: 100G
       customer: all
       cdets-attribute:  auto-fwd-ip
    '''
    execution_group = 'ipv4' 

    """ This is user Testcases section """
    @aetest.setup
    def prepare_for_subtest(self):
        """ Testcase Setup section """
        log.info(banner(" Aetest Testcase Execution "))

    @aetest.test
    def Shut_NoShut(self):
        #embed()
        testCaseName="Scale_Stress1"
        global g_topo_data,g_test_data
        global GV
        #global LcList
        rtr1_name=g_topo_data['R1']
        rtr=routers[rtr1_name]
        rtr.execute("terminal length 500")
        rtr.execute("terminal width 500")
        LcNode = Location.replace('/CPU0','')
        

        for count in range(IterCnt):
            result = LC_Reload(rtr,'host',LcNode)
            sleep(10)
            #rtr.execute("show access-lists scale hardware egress location 0/5/CPU0")
            if result != 1:
                log.info("Failed to reload LC")
            sleep(5)
            result = VerifyVm(rtr,lc = Location)
            if result!=True:
                log.info("LC is not up")
                #self.failed()
                ##pdb.set_trace()
            
            log.info('waiting for Convergence time for traffic recovery')
            sleep(ConvergTime)
            #rtr.execute("show l2vpn forwarding bridge-domain mac-address location 0/6/CPU0 | u w l")
            #rtr.execute ("show l2vpn forwarding bridge-domain mac-address location 0/7/CPU0 | u w l")
            

            if Traffic == "on":
                result=StatsIncrementCheck(rtr=rtr,intfL=IntfList)
                if result=="False":
                    log.info("Issue in traffic recovery after Continuous LC Reload")
                    #self.failed()  
                    pdb.set_trace() 
                else:
                    log.info("Traffic started resuming properly after Continuous LC Reload")

        log.info("Checking the Tracebacks,Errors in show logging and show context for crash")
        health_check = verify_show_logging_context(rtr)
        if not (health_check):
            log.error("show logging and context failed")
            pdb.set_trace()
       
    @aetest.cleanup
    def clean_this_tc(self):
        """ Testcase cleanup section """
        log.info("No Changes were made in setup section. \
        		Hence clean up is not required")
        		
###########################################################################################

class ChassisReload(aetest.Testcase):
    '''
    TAG_MAP:
       title: ChassisReload
       descr: This test case covers Continuous Chassis Reload.
       platform: NCS5500
       min-sw-ver: 6.1.0
       test-phase: dev-test
       modular-pkg: fretta-platform
       test-type: functionality
       test-component: ['coherent']
       sw-component: fretta-coherent
       topology: tgen-fretta-fretta-tgen
       tgn-type: spirent
       link-type: 100G
       customer: all
       cdets-attribute:  auto-fwd-ip
    '''
    execution_group = 'ipv4' 

    """ This is user Testcases section """
    @aetest.setup
    def prepare_for_subtest(self):
        """ Testcase Setup section """
        log.info(banner(" Aetest Testcase Execution "))

    @aetest.test
    def Shut_NoShut(self):
        #embed()
        testCaseName="Scale_Stress1"
        global g_topo_data,g_test_data
        global GV
        #global LcList
        rtr1_name=g_topo_data['R1']
        rtr=routers[rtr1_name]
        rtr.execute("terminal length 500")
        rtr.execute("terminal width 500")
        LcNode = Location.replace('/CPU0','')
        
        for count in range(IterCnt):
            out = reload_router(rtr)
            if out!=1:
                log.info("LC is not up, verifying the status of vm")
            sleep(120)
            result = VerifyVm(rtr,Location)
            if result!=True:
                log.info("LC is not up")
                #self.failed()
                pdb.set_trace()
            
            #R1
            
            if Traffic == "on":
                result=StatsIncrementCheck(rtr=rtr,intfL=IntfList)
                if result=="False":
                    log.info("Issue in traffic recovery after Chassis Reload")
                    #self.failed()  
                    pdb.set_trace() 
                else:
                    log.info("Traffic started resuming properly after Chassis Reload")

        log.info("Checking the Tracebacks,Errors in show logging and show context for crash")
        health_check = verify_show_logging_context(rtr)
        if not (health_check):
            log.error("show logging and context failed")
            pdb.set_trace()
       
    @aetest.cleanup
    def clean_this_tc(self):
        """ Testcase cleanup section """
        log.info("No Changes were made in setup section. \
        		Hence clean up is not required")
        		        		
############################################################################################  
 
class ProcessRestart(aetest.Testcase):
    '''
    TAG_MAP:
       title: ProcessRestart
       descr: This test case covers Process Restart.
       platform: NCS5500
       min-sw-ver: 6.1.0
       test-phase: dev-test
       modular-pkg: fretta-platform
       test-type: functionality
       test-component: ['coherent']
       sw-component: fretta-coherent
       topology: tgen-fretta-fretta-tgen
       tgn-type: spirent
       link-type: 100G
       customer: all
       cdets-attribute:  auto-fwd-ip
    '''
    execution_group = 'ipv4' 

    """ This is user Testcases section """
    @aetest.setup
    def prepare_for_subtest(self):
        """ Testcase Setup section """
        log.info(banner(" Aetest Testcase Execution "))

    @aetest.test
    def Shut_NoShut(self):
        #embed()
        testCaseName="Scale_Stress1"
        global g_topo_data,g_test_data
        global GV
        #global LcList
        rtr1_name=g_topo_data['R1']
        rtr=routers[rtr1_name]
        rtr.execute("terminal length 500")
        rtr.execute("terminal width 500")
        LcNode = Location.replace('/CPU0','')     
        
        for count in range(IterCnt):
            for proc in ProcessList:
                result = ProcessRestart_rtr(rtr,proc,Location)
                if result == False:
                    log.info("Process restart failed")
                    #self.failed()
                    pdb.set_trace()
            rtr.execute("show l2vpn forwarding bridge-domain mac-address location 0/6/CPU0 | u w l")
            rtr.execute ("show l2vpn forwarding bridge-domain mac-address location 0/7/CPU0 | u w l")
            rtr.execute ("sho l2vpn mac-learning mac all location 0/6/CPU0 | u w l")
            rtr.execute ("sho l2vpn mac-learning mac all location 0/7/CPU0 | u w l")
            #R1
            
            if Traffic == "on":
                result=StatsIncrementCheck(rtr=rtr,intfL=IntfList)
                if result=="False":
                    log.info("Issue in traffic recovery after process restarts")
                    #self.failed()  
                    pdb.set_trace()
                else:
                    log.info("Traffic started resuming properly after process restarts")

        log.info("Checking the Tracebacks,Errors in show logging and show context for crash")
        health_check = verify_show_logging_context(rtr)
        if not (health_check):
            log.error("show logging and context failed")
            pdb.set_trace()
       
    @aetest.cleanup
    def clean_this_tc(self):
        """ Testcase cleanup section """
        log.info("No Changes were made in setup section. \
        		Hence clean up is not required")     		

##################################################################

class ProcessCrash(aetest.Testcase):
    '''
    TAG_MAP:
       title: ProcessCrash
       descr: This test case covers Process Crash.
       platform: NCS5500
       min-sw-ver: 6.1.0
       test-phase: dev-test
       modular-pkg: fretta-platform
       test-type: functionality
       test-component: ['coherent']
       sw-component: fretta-coherent
       topology: tgen-fretta-fretta-tgen
       tgn-type: spirent
       link-type: 100G
       customer: all
       cdets-attribute:  auto-fwd-ip
    '''
    execution_group = 'ipv4' 

    """ This is user Testcases section """
    @aetest.setup
    def prepare_for_subtest(self):
        """ Testcase Setup section """
        log.info(banner(" Aetest Testcase Execution "))

    @aetest.test
    def Shut_NoShut(self):
        #embed()
        testCaseName="Scale_Stress1"
        global g_topo_data,g_test_data
        global GV
        #global LcList
        rtr1_name=g_topo_data['R1']
        rtr=routers[rtr1_name]
        rtr.execute("terminal length 500")
        rtr.execute("terminal width 500")
        LcNode = Location.replace('/CPU0','')      
        
        for count in range(IterCnt):
            for proc in ProcessList:
                result = ProcessCrash(rtr,proc,Location)
                if result == False:
                    log.info("Process crash failed")
                    #self.failed()
                    pdb.set_trace()
            #R1
            
            if Traffic == "on":
                result=StatsIncrementCheck(rtr=rtr,intfL=IntfList)
                if result=="False":
                    log.info("Issue in traffic recovery after process crash")
                    #self.failed()  
                    pdb.set_trace() 
                else:
                    log.info("Traffic started resuming properly after process crash")

        log.info("Checking the Tracebacks,Errors in show logging and show context for crash")
        health_check = verify_show_logging_context(rtr)
        if not (health_check):
            log.error("show logging and context failed")
            pdb.set_trace()
       
    @aetest.cleanup
    def clean_this_tc(self):
        """ Testcase cleanup section """
        log.info("No Changes were made in setup section. \
        		Hence clean up is not required")     		


####################################################################

class ProcessShutStart(aetest.Testcase):
    '''
    TAG_MAP:
       title: ProcessCrash
       descr: This test case covers Process Shut and Start.
       platform: NCS5500
       min-sw-ver: 6.1.0
       test-phase: dev-test
       modular-pkg: fretta-platform
       test-type: functionality
       test-component: ['coherent']
       sw-component: fretta-coherent
       topology: tgen-fretta-fretta-tgen
       tgn-type: spirent
       link-type: 100G
       customer: all
       cdets-attribute:  auto-fwd-ip
    '''
    execution_group = 'ipv4' 

    """ This is user Testcases section """
    @aetest.setup
    def prepare_for_subtest(self):
        """ Testcase Setup section """
        log.info(banner(" Aetest Testcase Execution "))

    @aetest.test
    def Shut_NoShut(self):
        #embed()
        testCaseName="Scale_Stress1"
        global g_topo_data,g_test_data
        global GV
        #global LcList
        rtr1_name=g_topo_data['R1']
        rtr=routers[rtr1_name]
        rtr.execute("terminal length 500")
        rtr.execute("terminal width 500")
        LcNode = Location.replace('/CPU0','')      
        
        for count in range(IterCnt):
            for proc in ProcessList:
                result=ProcessStop(rtr,proc,Location)
                if result == False:
                    log.info("Process stop failed")
                    #self.failed()
                    pdb.set_trace()
                result=ProcessStart(rtr,proc,Location)
                if result == False:
                    log.info("Process start failed")
                    #self.failed()
                    pdb.set_trace()
            #R1
            
            if Traffic == "on":
                result=StatsIncrementCheck(rtr=rtr,intfL=IntfList)
                if result=="False":
                    log.info("Issue in traffic recovery after process shut and start")
                    #self.failed()   
                else:
                    log.info("Traffic started resuming properly after process shut and start")

        log.info("Checking the Tracebacks,Errors in show logging and show context for crash")
        health_check = verify_show_logging_context(rtr)
        if not (health_check):
            log.error("show logging and context failed")
            pdb.set_trace()
       
    @aetest.cleanup
    def clean_this_tc(self):
        """ Testcase cleanup section """
        log.info("No Changes were made in setup section. \
        		Hence clean up is not required")     		


#####################################################################################

class RPSwitchover(aetest.Testcase):
    '''
    TAG_MAP:
       title: RPSwitchover
       descr: This test case covers RPSwitchover.
       platform: NCS5500
       min-sw-ver: 6.1.0
       test-phase: dev-test
       modular-pkg: fretta-platform
       test-type: functionality
       test-component: ['coherent']
       sw-component: fretta-coherent
       topology: tgen-fretta-fretta-tgen
       tgn-type: spirent
       link-type: 100G
       customer: all
       cdets-attribute:  auto-fwd-ip
    '''
    execution_group = 'ipv4' 

    """ This is user Testcases section """
    @aetest.setup
    def prepare_for_subtest(self):
        """ Testcase Setup section """
        log.info(banner(" Aetest Testcase Execution "))

    @aetest.test
    def Shut_NoShut(self):
        #embed()
        testCaseName="Scale_Stress1"
        global g_topo_data,g_test_data
        global GV
        #global LcList
        rtr1_name=g_topo_data['R1']
        rtr1a_name = g_topo_data['R1a']
        rtr=routers[rtr1_name]
        rtra=routers[rtr1a_name]
        rtr.execute("terminal length 500")
        rtr.execute("terminal width 500")
        LcNode = Location.replace('/CPU0','')      
        
        #RPSO
        for count in range(IterCnt):
            try:
                status=RpfoAndVerify(rtr,rtra)
                sleep(5)
                if status!=False:
                    #rtr.execute("show access-lists ipv4 scale hardware egress location 0/5/CPU0")
                    log.info('RSP switchover sucessful')

                else:
                    log.info('Failure with RSP switchover')
                    #self.failed()
                    #pdb.set_trace()
            except Exception as err:
                    errMsg = ' ErroR: %s' % str(err)
                    log.info(errMsg)
                    #self.failed()
                    #pdb.set_trace()
            sleep(ConvergTime)
            rtr.execute("show access-lists ipv4 scale hardware egress location 0/5/CPU0")
            if Traffic == "on":
                result=StatsIncrementCheck(rtr=rtr,intfL=IntfList)
                if result=="False":
                    log.info("Issue in traffic recovery after RP switchover")
                    #self.failed() 
                    #pdb.set_trace()  
                else:
                    log.info("Traffic started resuming properly after RP Switchover")
            
            #RPFO
            log.info("Siwtch back to Old RP and Verify Traffic")
            try:
                status=RpfoAndVerify(rtra,rtr)
                if status!=False:
                    log.info('RSP switchover sucessful')
                else:
                    log.info('Failure with RSP switchover')
                    #self.failed()
                    #pdb.set_trace()
            except Exception as err:
                    errMsg = ' ErroR: %s' % str(err)
                    log.info(errMsg)
                    #self.failed()
                    
            sleep(ConvergTime)
            if Traffic == "on":
                result=StatsIncrementCheck(rtr=rtr,intfL=IntfList)
                if result=="False":
                    log.info("Issue in traffic recovery after RP switchover")
                    #self.failed() 
                    #pdb.set_trace()  
                else:
                    log.info("Traffic started resuming properly after RP Failover")

        log.info("Checking the Tracebacks,Errors in show logging and show context for crash")
        health_check = verify_show_logging_context(rtr)
        if not (health_check):
            log.error("show logging and context failed")
            pdb.set_trace()
            
       
    @aetest.cleanup
    def clean_this_tc(self):
        """ Testcase cleanup section """
        log.info("No Changes were made in setup section. \
        		Hence clean up is not required")

class ClearCLICommdns(aetest.Testcase):
    '''
    TAG_MAP:
       title: ClearCLICommdns
       descr: This test case covers the clear CLI's.
       platform: NCS5500
       min-sw-ver: 6.1.0
       test-phase: dev-test
       modular-pkg: fretta-platform
       test-type: functionality
       test-component: ['coherent']
       sw-component: fretta-coherent
       topology: tgen-fretta-fretta-tgen
       tgn-type: spirent
       link-type: 100G
       customer: all
       cdets-attribute:  auto-fwd-ip
    '''
    execution_group = 'ipv4'

    """ This is user Testcases section """

    @aetest.setup
    def prepare_for_subtest(self):
        """ Testcase Setup section """
        log.info(banner(" Aetest Testcase Execution "))

    @aetest.test
    def Shut_NoShut(self):
        # embed()
        testCaseName = "Scale_Stress1"
        global g_topo_data, g_test_data
        global GV
        # global LcList
        rtr1_name = g_topo_data['R1']
        rtr = routers[rtr1_name]
        rtr.execute("terminal length 500")
        rtr.execute("terminal width 500")

        # capture the memory before trigger
        log.info("Start memory comparision on both routers")
        rtr.execute("show memory compare start")
        rtr.execute("show memory compare start location %s" % Location)
        response[r"all bridge\-domains which are in this state\? \(y\/n\)\[n\] "] = "econ_sendline y;exp_continue"
        response["Reset ALL OSPF processes\? \[no\]\:"] = "econ_sendline y;exp_continue"
        response["Clear logging buffer \[confirm\] \[y\/n\] \:"] = "econ_sendline y;exp_continue"
        rtr.execute("clear logging", reply=response)
        rtr.execute("clear context", reply=response)
        for count in range(IterCnt):
            config_strR1 = ""
            for clis in clear_cli_list:
                # config_strR1 += clis
                try:
                    rtr.execute(clis, reply=response)
                except Exception as e:
                    log.error('clear %s is failed as %s' % (clis, e))
            # pdb.set_trace()
            # rtr.execute(config_strR1)
            # if rtr.receive(r'.*\(y\/n)\[n] ', timeout=30) :
            #    rtr.transmit('y', timeout=30)
            sleep(20)
            rtr.execute("show l2vpn forwarding bridge-domain mac-address location 0/3/CPU0 | u w l")
            rtr.execute ("sho l2vpn mac-learning mac all location 0/3/CPU0 | u w l")
            rtr.execute ("show l2vpn forwarding bridge-domain mac-address location 0/2/CPU0 | u w l")
            rtr.execute ("sho l2vpn mac-learning mac all location 0/2/CPU0 | u w l")
        if Traffic == "on":
            result = StatsIncrementCheck(rtr=rtr, intfL=IntfList)
            if result == "False":
                log.info("Issue in traffic recovery after repeated config & rollback")
                # self.failed()
                # pdb.set_trace()
            else:
                log.info("Traffic started resuming properly after repeated config & rollback")
        sleep(120)  # waiting for 120 second for expected memory to release
        log.info("Stop memory comparision on both routers")
        log.info("Start memory comparision on both routers")
        rtr.execute("show memory compare end")
        rtr.execute("show memory compare end location %s" % Location)
        log.info("Capture the memory usage and analyse the leak")
        # R1
        fail_cnt = 0
        for process in MemLeakProcessList:
            result = CompareMemory(rtr, process, Location)
            if result == False:
                log.info("There is some issue in finding memory info for %s" % process)
                fail_cnt = fail_cnt + 1
            elif result == "leak":
                log.info("Idenfied memory leak for %s" % process)
                fail_cnt = fail_cnt + 1
            elif result == True:
                log.info("There are no leak identified for %s" % process)
        if fail_cnt >= 1:
            log.info("Issue with memory usage after trigger.Need to analyse the core file later on R1")
        log.info("Checking the Tracebacks,Errors in show logging and show context for crash")
        health_check = verify_show_logging_context(rtr)
        if not (health_check):
            log.error("show logging and context failed")
            pdb.set_trace()

    @aetest.cleanup
    def clean_this_tc(self):
        """ Testcase cleanup section """
        log.info("No Changes were made in setup section. \
                Hence clean up is not required")
        log.info("Pass testcase cleanup")
        		
##################################################################
########################################################################
####                       COMMON CLEANUP SECTION                    ###
########################################################################
#
# Remove the BASE CONFIGURATION that was applied earlier in the
# common cleanup section, clean the left over

class common_cleanup(aetest.CommonCleanup):

    @aetest.subsection
    def common_clean(self):
        get_test_topo(self.script_args)
        global g_topo_data
        global GV
        #g_test_data = get_test_data_from_yaml(self.script_args['test_data_file'])

        self.script_args['testStep']=1
        check_result=1
        log.info('No Clean up is required to maintain its state')
        
      #  rtr1_name=g_topo_data['R1']
      #  rtr2_name=g_topo_data['R2']
        
      #  global GV
      # uut1 = GV['uut1']
      #  uut2 = GV['uut2']
        
       # Startup_Config = self.script_args['Startup_Conf']
        #for fretta_rtr in [rtr1_name,rtr2_name]:
        #    log.info('applying configuration')
        #    cmd='load ' + Startup_Config + '\r'
        #    routers[fretta_rtr].transmit('configure terminal\r')
        #    routers[fretta_rtr].receive(r'#',timeout=20)
        #    routers[fretta_rtr].transmit('commit replace\r')
        #    routers[fretta_rtr].receive(r':',timeout=20)
        #    routers[fretta_rtr].transmit('yes\r')
        #    routers[fretta_rtr].receive(r'#',timeout=20)
        #    routers[fretta_rtr].transmit(cmd)
        #    routers[fretta_rtr].receive(r'#',timeout=20)
        #    routers[fretta_rtr].transmit('commit\r')
        #    routers[fretta_rtr].receive(r'#',timeout=20)
        #    routers[fretta_rtr].transmit('exit\r') 
        #    output=routers[fretta_rtr].receive_buffer()

        #    if re.search('Failed to commit one or more configuration items', output):
        #        raise Exception('configuration apply failed')
        #        self.failed()
        #    else:
        #        log.info('configuration applied successfully')
            
         
        
        ##############################################################
        #clean up the session, release the ports reserved and cleanup the dbfile
        ##############################################################
        
      #  cleanup_sta = sth.cleanup_session (port_handle= GV['port_handle'],clean_dbfile= '1')
      #  status = cleanup_sta['status']
      #  if (status == '0') :
	  #      log.info("run sth.cleanup_session failed")
	  #      self.failed()
      #  else:
	  #      log.info("***** run sth.cleanup_session successfully")



##################################################################

if __name__ == '__main__':
    aetest.main()
