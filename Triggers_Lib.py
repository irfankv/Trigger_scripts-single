#!/bin/env python
# All rights reserved.
#
__author__  = "Vel Kalai Arasan <varasan@cisco.com>"
__version__ = '1.0'

from ats import tcl
from ats import aetest, atslog
#import sys, re, time, logging, string, os, subprocess
import sys, re, logging, string, os, subprocess
from time import sleep
import pdb
from IPython import embed
import sth
import datetime
from array import *

sys.path.append(os.path.join(os.environ['AUTOTEST'], 'lib/cisco-shared/palladium'))

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def HugShutNoShut(device=None,mode=None,ports=None,flp_cnt=1):
    '''
    This Proc is to handle most of the possible port events of HundredGig Port.Below are example combinations.
    mode = shut/nosh/shut_blk/nosh_blk/flap
    flp_cnt = Specify how many times the flap should happen
    port argument are passed as a list in function call
    '''
    RtrCfgStr =" "    
    for port in ports:
        if mode == "shut":
            rtr_cfg = '''
                interface %s
                shutdown
                !
                ''' %(port)
            device.config(rtr_cfg)
        if mode == "nosh":
            rtr_cfg = '''
                interface %s
                no shutdown
                !
                ''' %(port)
            device.config(rtr_cfg)
        if mode == "shut_blk":
            RtrCfgStr += '''
                interface %s
                shutdown
                !
                ''' %(port)
            device.config(RtrCfgStr)
        if mode == "nosh_blk":
            RtrCfgStr += '''
                interface %s
                no shut
                !
                ''' %(port)
            device.config(RtrCfgStr)
        if mode == "flap":
            for i in range(flp_cnt):
                rtr_cfg = '''
                    interface %s
                    shutdown
                    !
                    ''' %(port)
                device.config(rtr_cfg)
                sleep(5)
                rtr_cfg = '''
                    interface %s
                    no shutdown
                    !
                    ''' %(port)
                device.config(rtr_cfg)
                sleep(5)
                device.execute("show access-lists ipv4 bvi100 hardware egress location 0/0/CPU0")
    return 1

#############################################################################

def CompareMemory (rtr, process_name, ln_cpu = 'none'):
    
    if ln_cpu == 'none':
        output = rtr.execute ("show memory compare report | i %s" % (process_name))
    else:
        output = rtr.execute ("show memory compare report location %s | i %s" % (ln_cpu, process_name))
    List=[]
    List=output.split("\n")
    for lst in List:
        if process_name in lst:
            match=re.search('([0-9 ]+)[ ]+(%s)[ ]+([0-9]+)[ ]+([0-9]+)[ ]+([0-9]+)'%process_name,lst)
            if match:
                diff = int(match.group(5)) 
                if diff == 0:
                    log.info("There are no leaks found as memory usage is same before and after the trigger for %s"%process_name)
                    return True
                else:
                    log.info("Memory leak found for %s"%process_name)
                    log.info("Difference in memory - %d" % diff)
                    log.info("Take the dumpcore of %s and save to evaluate later"%process_name)
                    if ln_cpu == 'none':
                        output = rtr.execute ("show processes %s" % (process_name))
                        m = re.search(r'Job Id: (\d*)',output)
                        pid = int(m.group(1))
                        rtr.execute("dumpcore running %s" %pid)       
                        return "leak"
                    else:
                        output = rtr.execute ("show processes %s location %s" % (process_name,ln_cpu))
                        m = re.search(r'Job Id: (\d*)',output)
                        pid = int(m.group(1))
                        rtr.execute("dumpcore running %s location %s" %(pid,ln_cpu))       
                        return "leak"
            else:
                return False
                

#############Verify Ports##########################################

def VerifyPorts(device=None,ports=None,type=None,state="Up"):
    '''
    This Proc is to verify port status of Optics Controller and 
    CoherentDSP.Below are example combinations.
    type =Its the list .Pass a list while calling "CohDSP,Optics"
    state=This is to indicate whether to expect controllers to be UP or Down
           Options or Up / Down.
    port argument are passed as a list in function call
    '''
    flag=0
    for port in ports:
        succ_cnt=0
        if state == "Up":
            contlr="Up"
            Admin="In Service"
            Laser="On"
            LED="Green"
        else:
            contlr="Administratively Down"
            Admin="Out Of Service"
            Laser="Off"
            LED="Off"
        if type[0]=="Optics" or type[1]=="Optics":
            output = device.execute("show controllers optics %s | i State" % (port))
            List=[]
            List=output.split("\n")
            for lst in List:
                if contlr in lst:
                    log.info("Controller State is: %s" %(contlr))
                    succ_cnt+=1
                elif Admin in lst:
                    log.info("Admin State is: %s" %(Admin))
                    succ_cnt+=1
                elif Laser in lst:
                    log.info("Laser State is: %s" %(Laser))
                    succ_cnt+=1
                elif LED in lst:
                    log.info("LED State is: %s" %(LED))
                    succ_cnt+=1
            if succ_cnt == 4:
                log.info("Optics Controller state is expected for port :%s"%(port))
            else:
                log.info("Optics Controller state is not as expected for port:%s"%(port))   
                flag+=1                
        if type[0]=="CohDSP" or type[1]=="CohDSP":
            succ_cnt=0
            if state == "Up":
                DSP="Up"
            else:
                DSP="Admin Down"
            output = device.execute("show controllers coherentDSP %s | i State" % (port))
            List=[]
            List=output.split("\n")
            for lst in List:
                if DSP in lst:
                    log.info("CohDSP State is: %s" %(contlr))
                    succ_cnt+=1
            if succ_cnt == 1:
                log.info("CohDSP Controller state is expected for port :%s"%(port))
            else:
                log.info("CohDSP Controller state is not as expected for port:%s"%(port))   
                flag+=1
    
    if flag==0:
        return True
    else:
        return False       


##########################################################################

def StatsIncrementCheck (rtr,intfL):
    '''This function capture the interface counter stats and return the same
    Intf : is the list'''
    
    #verify interface counters
    for intf in intfL:
        result = rtr.execute("sh interfaces %s | i packets in"%(intf))
        for line in result.split('\n'):
	        exact = line.strip()
	        regexp = re.search (r'Packets input',exact,re.I)
	        if regexp:
		        val = re.match(r'(.*) Packets .*',exact, re.I)
		        pkt_in = val.group(1)
    
        result = rtr.execute("sh interfaces %s | i packets out"%(intf))
        for line in result.split('\n'):
	        exact = line.strip()
	        regexp = re.search (r'Packets output',exact,re.I)
	        if regexp:
		        val = re.match(r'(.*) Packets .*',exact, re.I)
		        pkt_out = val.group(1)
        if int(pkt_out) and int(pkt_in) >= 10000:
            log.info("Step:Traffic resumed properly")
        else:
            log.info("Some issue with data path on %s"%intf)
            return False
    #return True
    
##############################################################################

def ProcessRestart_rtr(rtr,process_name,ln_cpu):
    rtr.execute("show clock")
    rtr.execute("process restart %s location %s" % (process_name, ln_cpu))

    # Wait for the restart to complete.
    delay_secs = 30
    for n in range(6, delay_secs + 1):
        rtr.execute("show clock")
        output = rtr.execute("show processes %s location %s | include Process state:" % (process_name, ln_cpu))
        #time.sleep(1)
        sleep(10)
    if output.count("Run") == 1:
        rtr.execute("show clock")
        return True
    log.info("%s process restart on %s failed to complete in %d seconds" % (process_name, ln_cpu, delay_secs,))
    #show_logs(rtr,ln_cpu)
    return False
    
def ProcessStop (rtr,process_name,ln_cpu='0/0/CPU0'):
    rtr.execute("show clock")
    rtr.execute("process shutdown %s location %s" % (process_name, ln_cpu))

    # Wait for the restart to complete.
    delay_secs = 10
    for n in range(5, delay_secs + 1):
        rtr.execute("show clock")
        return True

def ProcessCrash (rtr,process_name,ln_cpu):
    rtr.execute("show clock")
    rtr.execute("process crash %s location %s" % (process_name, ln_cpu))

    # Wait for the restart to complete.
    delay_secs = 20
    for n in range(5, delay_secs + 1):
        rtr.execute("show clock")
        output = rtr.execute("show processes %s location %s | include Process state:" % (process_name, ln_cpu))
        #time.sleep(1)
        sleep(1)
    if output.count("Run") == 1:
        rtr.execute("show clock")
        return True
    log.info("%s process crash on %s failed to complete in %d seconds" % (process_name, ln_cpu, delay_secs,))
    #show_logs(rtr,ln_cpu)
    return False

def ProcessStart (rtr,process_name,ln_cpu='0/0/CPU0'):
    rtr.execute("show clock")
    rtr.execute("process start %s location %s" % (process_name, ln_cpu))

    # Wait for the start to complete.
    delay_secs = 20
    for n in range(5, delay_secs + 1):
        rtr.execute("show clock")
        output = rtr.execute("show processes %s location %s | include Process state:" % (process_name, ln_cpu))
    if output.count("Run") == 1:
        rtr.execute("show clock")
        return True
    log.info("%s process start on %s failed to complete in %d seconds" % (process_name, ln_cpu, delay_secs,))
    #show_logs(rtr,ln_cpu)
    return False

#############################################################################

def GetActiveRp(device):
    log.info("Entering get_active_rp")
    try:
        active_xr_rp = get_xr_active_rp(device)
        return '/'.join(active_xr_rp.split('/')[:2])
    except Exception as err:
        errMsg = 'Error determining active RP - please check the parse\nError:%s' \
                 % (str(err))
        log.info(errMsg)


def RpfoAndVerify(device1, device2):
    active_rp0 = GetActiveRp(device1)
    active_rp0 = active_rp0 + "/CPU0"
    #pdb.set_trace() 
    result = device1.rp_xr_exec("redundancy switchover location %s" %active_rp0 , answer="y")
    if re.search("Initiating switch-over.*%s" % active_rp0.upper() ,result,re.DOTALL):
        log.info("Redundancy Switchover Passed from Active RP %s" %active_rp0)
    else:
        raise Exception("Redundancy Switchover Failed from Active RP %s" %active_rp0)
    device1.disconnect()
    sleep(70)
    log.info('Disconnected console1\n Connecting Console2....... ')
    tcl.eval('csccon_add_state_pattern enable {RP/0/RP0/CPU0:fretta#}')
    device2.connect()
    device2.rp_xr_exec('terminal length 0')
    device2.rp_xr_exec('terminal width 512')
    active_rp1 = GetActiveRp(device2)
    if active_rp1 == active_rp0:
        log.info("Active RP switch over did not happen. Active RP is still %s" % active_rp1)
        return False
    else:
        log.info("Active RP switch over successful . %s => %s" % (active_rp0,active_rp1))
        return True

def get_xr_active_rp(device):
    log.info("Entering get_xr_active_rp")
    try:
        # get the show redundency output and parse for the Active RP node
        output = device.verify("show redundancy", os_type='xr',
                                parser_type = 'router_show', parse_only='yes')
        return output['active_node'].upper()
    except Exception as err:
        errMsg = 'Error determining active RP - please check the parse\nError:%s' \
                % (str(err))
        log.info(errMsg)

################################################################

def VerifyVm(rtr,lc='all'):
    
    flag = 0
    plat={}
    xr_pattern = "([A-Z0-9\/]+)\s+[A-Z\(\)\s]+\s+[A-Z]+\s+([A-Z]+\s[A-Za-z]+)\s+([0-9\.]+)"
    for i in range(1,3):
        sleep(60)
        output=rtr.execute('show platform vm')
        for line in output.split('\n'):
            matchObj = re.search('\-\-\-\-', line, re.I)
            if matchObj:
                continue
            if re.search(xr_pattern,line):
                matchObj = re.search(xr_pattern,line)
                loc = matchObj.group(1)
                status = matchObj.group(2)
                ip_addr = matchObj.group(3)
                if loc==lc and status=='FINAL Band':
                    plat[loc] = {'status' : status, 'ip_addr' : ip_addr}
                    break
    if plat[lc]['status']=='FINAL Band':
        log.info("LC is in operational state")
        return True
    else:
        log.info("Verifying the LC vm")
        lc = lc.replace('/CPU0','')
        rtr.transmit('admin\r')
        rtr.expect(r'#',timeout=5)
        output=rtr.transmit('show vm location %s'%lc)
        pattern = "[a-zA-Z]+\-[a-zA-Z]+\s*[a-zA-Z]+"
        for line in output.split('\n'):
            matchObj = re.search('\-\-\-\-',line, re.I)
            if matchObj:
                continue
            if re.search(pattern,line):
                matchObj = re.search(pattern,line).grou()
                status = matchObj.split(' ')[-1]
            if status == 'running':
                log.info("VM is up and running")
                rtr.transmit('exit\r')
                return True
            else:
                log.info ("VM is in down state")
                rtr.transmit('exit\r')
                return False