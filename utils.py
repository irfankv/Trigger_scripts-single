import time, re, logging, pdb
from ats import tcl

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

GA = dict()

def parse_show_platform(device, vm):
    '''
    parse output of show platform on either
    calvados vm or xr vm and returns dictionary

    Arguments:
        device(Device): device on which to check 'show platform'
        vm(str): 'xr' or 'calvados'

    Returns:
        dictionary
    '''
    cal_pattern = "([A-Z0-9\/]+)\s+[A-Z-0-9]+\s+([A-Z]+)\s+([A-Z\/]+)\s+[A-Z]+"
    xr_pattern = "([A-Z0-9\/]+)\s+[A-Z\(\)\s]+\s+[A-Z]+\s+([A-Z]+\s[A-Za-z]+)\s+([0-9\.]+)"
    if vm == 'calvados':
        output=device.execute('show platform')
        for line in output.split('\n'):
            matchObj = re.search('\-\-\-\-', line, re.I)
            if matchObj:
                continue
            if re.search(cal_pattern, line):
                matchObj = re.search(cal_pattern,line)
                loc = matchObj.group(1)
                hw_state = matchObj.group(2)
                sw_state = matchObj.group(3)
                GA[loc] = {'hw_state' : hw_state, 'sw_state' : sw_state}
    else:
        output=device.execute('show platform vm')
        for line in output.split('\n'):
            matchObj = re.search('\-\-\-\-', line, re.I)
            if matchObj:
                continue
            if re.search(xr_pattern,line):
                matchObj = re.search(xr_pattern,line)
                loc = matchObj.group(1)
                status = matchObj.group(2)
                ip_addr = matchObj.group(3)
                GA[loc] = {'status' : status, 'ip_addr' : ip_addr}
    return GA

def parse_show_platform1(device, vm, location):
    '''
    parse output of show platform on either
    calvados vm or xr vm and returns dictionary

    Arguments:
        device(Device): device on which to check 'show platform'
        vm(str): 'xr' or 'calvados'

    Returns:
        dictionary
    '''
	
    cal_pattern = ('(%s)\s+[A-Z-0-9]+\s+([A-Z_]+)\s+([A-Z_\/]+)\s+[A-Z]+' %location)
    xr_pattern = ('(%s)\s+[A-Z\(\)\s]+\s+[A-Z]+\s+([A-Z]+\s[A-Za-z_]+)\s+([0-9\.]+)' %location)
    if vm == 'calvados':
        device.transmit('admin\r')
        device.receive(r'#')
        device.transmit('show platform\r')
        device.receive(r'#')
        output=device.receive_buffer()
        device.transmit('exit\r')
        device.receive(r'#')
        matchObj = re.search(cal_pattern, output)
        if matchObj:
           loc = matchObj.group(1)
           hw_state = matchObj.group(2)
           log.info('hw_state is %s\n' %hw_state)
           sw_state = matchObj.group(3)
           log.info('sw_state is %s\n' %sw_state)
           GA[loc] = {'hw_state' : hw_state, 'sw_state' : sw_state}
           return True, GA
        else:
           return False, GA
    else:
        output=str(device.execute('show platform vm'))
        matchObj = re.search(xr_pattern, output)
        if matchObj:
           loc = matchObj.group(1)
           status = matchObj.group(2)
           ip_addr = matchObj.group(3)
           GA[loc] = {'status' : status, 'ip_addr' : ip_addr}
           return True, GA
        else:
           return False, GA	

def get_bp_id(device,location):
    log.info('entering proc to get bp id')
    output=device.execute('show controller card inventory summary')
    for line in output.split('\n'):
        if re.search(location,line):
            return line.split()[2]

    return None

def reload_container(device,container,location):

    log.info('entering proc to reload %s container of node %s' % (container,location))
    device.transmit('admin\r')
    device.receive(r'#',timeout=30)
    if container == 'host':
        log.info('reloading Line Card\n')
        cmd='hw-module location %s reload \r' % location
        device.transmit(cmd)
        device.receive(r'\[no,yes\]',timeout=60)
        device.transmit('yes\r')
    elif container == 'xr':
        log.info('reloading %s container' % container)
        loc=location + '/VM1'
        cmd='sdr default-sdr location %s reload\r' % loc
        device.transmit(cmd)
        device.receive(r'\[no,yes\]',timeout=60)
        device.transmit('yes\r')
    elif container == 'cal':
        log.info('reloading %s container' % container)
        cmd='reload admin location %s\r' % location
        device.transmit(cmd)
        device.receive(r'\[no,yes\]',timeout=60)
        device.transmit('yes\r')
        device.receive(r'#',timeout=60)
        device.transmit('exit\r')
        device.receive(r'#')
        log.info('sleeping for 2 mins for the node to come up')
        time.sleep(120)
        value ,val = parse_show_platform1(device,'calvados',location)
        if value == True:
           if val[location]['sw_state'] == 'OPERATIONAL':
              log.info('node %s is up after cal container reload' % location)
              return 1
           else:
              log.error('node %s is in %s state, after waiting for 2 min\n' %(location, val[location]['sw_state']))
              return 0
        else:
           log.error('node %s is not up. Hence moving to cleanup' % location)
           return 0

    elif container == 'pc':
        log.info('power cyclying the card %s' % location)
        bp_id = get_bp_id(device,location)
        if not bp_id is None:
            cmd='run /opt/cisco/calvados/sbin/card_mgr_client -r -c reset -m cold -s %s\r' % bp_id
            device.transmit(cmd)
            device.receive(r'#',timeout=120)
            output=device.receive_buffer()
            if re.search('Reset operation completed',output):
                log.info('powered down of LC is successful')
            else:
                log.error('powered down of LC is unsuccessful')
                return 0
        else:
            return 0

    device.receive(r'#',timeout=30)
    device.transmit('exit\r')
    device.receive(r'#',timeout=30)

    time.sleep(30)
    device.execute('show platform vm')
    log.info('sleeping for 4 mins for linecard to come up')
    time.sleep(240)

    #check if linecard is in final band
    location1=location
    location=location + '/CPU0'
    iter=1
    flag=0
    while iter <= 3:
        value, val = parse_show_platform1(device,'xr',location)
        if value == True:
           if val[location]['status'] == 'FINAL Band':
              flag = 1
              break
           else:
              log.info('Final status is not in Final Band')
        log.info('retrying \(%s/3\)...sleeping for addtional 2 mins' % iter)
        iter += 1
        time.sleep(120)
    if flag == 0:
        return 0
    else:
        return 1

def LC_Shut(device,container,location):

    log.info('entering proc to reload %s container of node %s' % (container,location))
    device.transmit('admin\r')
    device.receive(r'#',timeout=30)
    if container == 'host':
        log.info('reloading %s node' % container)
        cmd='hw-module location %s shutdown \r' % location
        device.transmit(cmd)
        device.receive(r'\[no,yes\]',timeout=30)
        device.transmit('yes\r')
    elif container == 'xr':
        log.info('reloading %s container' % container)
        loc=location + '/VM1'
        cmd='sdr default-sdr location %s reload\r' % loc
        device.transmit(cmd)
        device.receive(r'\[no,yes\]',timeout=30)
        device.transmit('yes\r')
    elif container == 'cal':
        log.info('reloading %s container' % container)
        cmd='reload admin location %s\r' % location
        device.transmit(cmd)
        device.receive(r'\[no,yes\]',timeout=30)
        device.transmit('yes\r')
    elif container == 'pc':
        log.info('power cyclying the card %s' % location)
        bp_id = get_bp_id(device,location)
        if not bp_id is None:
            cmd='run /opt/cisco/calvados/sbin/card_mgr_client -r -c reset -m cold -s %s\r' % bp_id
            device.transmit(cmd)
            device.receive(r'#',timeout=30)
            output=device.receive_buffer()
            if re.search('Reset operation completed',output):
                log.info('powered down of LC is successful')
            else:
                log.error('powered down of LC is unsuccessful')
                return 0
        else:
            return 0

    device.receive(r'#',timeout=30)
    device.transmit('exit\r')
    device.receive(r'#',timeout=30)

    time.sleep(10)
    device.execute('show platform')
    log.info('checking for POWERED_OFF state')
    #check if linecard is in final band
    location=location
    iter=1
    flag=0
    while iter <= 3:
      output=device.execute('show platform')
      for line in output.split('\n'):
        if re.search(location,line):
          if re.search('POWERED_OFF',line):
            log.info('node is now shutdown')
            flag=1
            break
          else:
            iter += 1
            log.info('retrying \(%s/3\)...sleeping for addtional 2 mins' % iter)
            time.sleep(120)
      if flag == 1:
         break

    if flag == 0:
        return 0
    else:
        return 1
def LC_Reload(device,container,location):

    log.info('entering proc to reload %s container of node %s' % (container,location))
    device.transmit('admin\r')
    device.receive(r'#',timeout=30)
    if container == 'host':
        log.info('reloading %s node' % container)
        cmd='hw-module location %s reload \r' % location
        device.transmit(cmd)
        device.receive(r'\[no,yes\]',timeout=30)
        device.transmit('yes\r')
    elif container == 'xr':
        log.info('reloading %s container' % container)
        loc=location + '/VM1'
        cmd='sdr default-sdr location %s reload\r' % loc
        device.transmit(cmd)
        device.receive(r'\[no,yes\]',timeout=30)
        device.transmit('yes\r')
    elif container == 'cal':
        log.info('reloading %s container' % container)
        cmd='reload admin location %s\r' % location
        device.transmit(cmd)
        device.receive(r'\[no,yes\]',timeout=30)
        device.transmit('yes\r')
    elif container == 'pc':
        log.info('power cyclying the card %s' % location)
        bp_id = get_bp_id(device,location)
        if not bp_id is None:
            cmd='run /opt/cisco/calvados/sbin/card_mgr_client -r -c reset -m cold -s %s\r' % bp_id
            device.transmit(cmd)
            device.receive(r'#',timeout=30)
            output=device.receive_buffer()
            if re.search('Reset operation completed',output):
                log.info('powered down of LC is successful')
            else:
                log.error('powered down of LC is unsuccessful')
                return 0
        else:
            return 0

    device.receive(r'#',timeout=30)
    device.transmit('exit\r')
    device.receive(r'#',timeout=30)

    time.sleep(10)
    device.execute('show platform')
    log.info('sleeping for 3 mins for linecard to come up')
    time.sleep(180)
    #check if linecard is in final band
    location=location + '/CPU0'
    iter=1
    flag=0
    while iter <= 3:
      output=device.execute('show platform')
      for line in output.split('\n'):
        if re.search(location,line):
          if re.search('IOS',line):
            log.info('node is now UP')
            flag=1
            break
          else:
            iter += 1
            log.info('retrying \(%s/3\)...sleeping for addtional 2 mins' % iter)
            time.sleep(120)
      if flag == 1:
         break

    if flag == 0:
        return 0
    else:
        return 1

def get_proc_details(device,proc_name,location):

    log.info('entering module get_proc_details')
	
    cmd='show process %s location %s' % (proc_name, location)
    output=device.execute(cmd)
	
    for line in output.split('\n'):
        if re.search('Process state: ([A-Za-z]+)', line):
            proc_state=re.search('Process state: ([A-Za-z]+)', line).group(1)
        if re.search('Respawn count: (\d+)', line):
            resp_cnt=re.search('Respawn count: (\d+)', line).group(1)

    if 'proc_state' in locals() and 'resp_cnt' in locals():
        return proc_state, int(resp_cnt)
    else:
        raise Exception ("process state and respawn count is not found")	
	
def process_restart(device, proc_name, location, type='restart', iteration=1, delay=60):
    ''' 
    type: restart/crash process on the location provided
		
    Default iteration is 1 and can be increased based on user need
		
    returns 1 on success and 0 on failure
	    
    '''

    log.info('entering process process_restart')
	
    count=1
    fail_flag=0
    while count <= iteration:
        log.info('Clearing the context before %s' %type)
        device.execute('clear context')

        log.info('fetching process details before %s' % type)
		
        try:
            proc_state_bef_restart, resp_cnt_bef_restart = get_proc_details(device, proc_name, location)
        except Exception as e:
            log.error(e)
            return 0

        log.info('%sing process %s iteration \(%s/%s\)...' % (type, proc_name, count, iteration))
        cmd='process %s %s location %s' % (type, proc_name, location)
        device.execute(cmd)

        if type == 'restart':
            time.sleep(30)
            log.info('sleeping 30 seconds after process %s' % type)
        else:
            time.sleep(180)
            log.info('sleeping for 3 minutes after process %s' % type)

        log.info('fetching process details after %s' % type)
		
        try:
            proc_state_aft_restart, resp_cnt_aft_restart = get_proc_details(device, proc_name, location)
        except Exception as e:
            log.error(e)
            return 0
			
        if proc_state_bef_restart == proc_state_aft_restart:
            log.info('process is %s both before and after %s' % (proc_state_aft_restart, type))
        else:
            log.error('process state is not same')
            fail_flag = 1

        if resp_cnt_bef_restart+1 == resp_cnt_aft_restart:
            log.info('respawn count is incremented after process %s' % type)
        else:
            log.error('respawn count before/after %s is %s/%s' % (type,resp_cnt_bef_restart,resp_cnt_aft_restart))
            fail_flag=1
			
        count += 1
		
        log.info('sleeping %s seconds before the next iteration' % delay)
        time.sleep(delay)
	
    if fail_flag == 0:
        return 1
    else:
        return 0

def verify_ping1(device,dstip,vrf='default'):
    # ping remote interfaces
    cmd = 'ping vrf %s %s' % (vrf, str(dstip))
    status_se = device.execute(cmd)
    m = re.search(r'Success rate is 0 percent', str(status_se))
    if m != None:
        errMsg = 'Ping Failed for %s %s' % (device, dstip)
        raise Exception(errMsg)
    return

def verify_intf_status(device,intf):
    # verify if interface is Up/Up
    cmd = 'show ipv4 int br | in %s' % intf
    output = device.execute(cmd)
    for line in output.split('\n'):
        line = line.split()
        if line[0] == str(intf):
            if line[2] == 'Up' and line[3] == 'Up':
                log.info('interface %s is Up/Up' % intf)
            else:
                errMsg = 'interface %s is not Up/Up' % intf
                raise Exception(errMsg) 

def reload_router(device, device1=False):
    ''' this will reload the device
        return 1 if success
	return 0 if fail
    '''
	
    log.info('entering module router_reload')
	
    cmd='hw-module location all reload\r'
    time_val=400
	
    device.transmit('admin\r')
    device.receive(r'#',timeout=15)
    device.transmit(cmd)
    device.receive(r'\[no,yes\]',timeout=15)
    device.transmit('yes\r')
    device.receive(r'#',timeout=30)
	
    log.info('waiting for system to come up')
    flag=0
    rpfo_flag=0
    chk_msg=('Press RETURN to get started')
    if check_console_msg(device, chk_msg, sleepTime=20, retryCount=60):
        log.info("Succesfully received Return message")
        time.sleep(30)
        device.transmit('\r')            
        flag=1
    else:
        device.transmit('\r')
        chk_msg=('RP Node is not ready or active for login')
        if check_console_msg(device, chk_msg, sleepTime=20, retryCount=60):
            log.info("Succesfully received standby message")
            rpfo_flag=1

    '''time_waited = 0
    flag=0
    rpfo_flag=0
    while time_waited <= time_val:
        if device.receive(r'Press RETURN to get started'):
            log.info('Got RETURN\n')
            time.sleep(30)
            device.transmit('\r')            
        if device.receive(r'User Access Verification'):
            log.info('Got User Access\n')
            flag=1
            break
        if device.receive(r'ios con0/RP0/CPU0 is in standby'):
            log.info('RP Switchover found\n')
            rpfo_flag=1
            break
        else:
            time.sleep(60)
            time_waited += 60
            device.transmit('\r')
    time.sleep(30)'''
    if rpfo_flag == 1:
        if device1 == False:
            log.error('Provide a valid 2nd RP handle\n')
            return 0
        else:
            device.transmit('\r')
            device.disconnect()
            device1.connect()
            log.info('Performing RPFO')
            active_rp0 = get_active_rp(device1)
            active_rp0 = active_rp0 + "/CPU0"
            result = uut2.rp_xr_exec("redundancy switchover location %s" % active_rp0 , answer="y")
            if re.search("Initiating switch-over.*%s" % active_rp0.upper() ,result,re.DOTALL):
                log.info("Redundancy Switchover Passed from Active RP %s" %active_rp0)
            else:
                log.error("Redundancy Switchover Failed from Active RP %s" % active_rp0)
                return 0
            log.info('Disconnecting R2')
            device1.disconnect()
            time.sleep(20)
            log.info('Connecting back R1')
            device.connect()
            log.info('system is up after reload')
            return 1
    if flag == 1:
        #device.transmit('\r')
        device.receive(r'Username:',timeout=60)
        device.transmit('root\r')
        device.receive(r'Password:',timeout=60)
        device.transmit('lab\r')
        device.receive(r'#',timeout=60)
        log.info('system is up after reload')
        return 1
    else:
        log.error('router is not up after reload')
        return 0

def collect_logs(device,loc):
    ''' will collect the show commands '''

    #location ip address would be node * 3 + 4    
    loc = loc.split('/')[-1]
    val = int(loc) * 4 + 4
    ip = '192.0.%s.1' % val

    device.transmit('admin\r')
    device.receive(r'#',timeout=30)
    device.transmit('run ssh %s\r' % ip)
    device.receive(r'\$',timeout=30)
    device.transmit('lspci -vt\r')
    device.receive(r'\$',timeout=30)
    device.transmit('ssh 10.0.2.16\r')
    device.receive(r'\$',timeout=30)
    device.transmit('/usr/sbin/pcimemread 0xd340040C 4\r')
    device.receive(r'\$',timeout=30)
    device.transmit('/usr/sbin/pcimemread 0xd3400304 4\r')
    device.receive(r'\$',timeout=30)
    device.transmit('exit\r')
    device.receive(r'\$',timeout=30)
    device.transmit('exit\r')
    device.receive(r'#',timeout=30)
    device.transmit('exit\r')
    device.receive(r'#',timeout=30)

def trigger_reload(rtr, lc,prompt='#'):
    '''
    Execute hw-module reload command for the given list of LC's and wait for the rc to get reloaded
    '''
    final_status=0
    if '/CPU0' in lc:
        lc1=lc.replace('/CPU0','')
    rtr.transmit('admin\r')
#PDB SET TRACE REMOVED BY SCRIPT.
    rtr.receive(r'#', timeout=5)
    rtr.transmit('hw-module location %s reload force\r'%lc1)
    rtr.receive(r'[no,yes]', timeout=30)
    rtr.transmit('yes\r')
    rtr.receive(r'#', timeout=30)
    rtr.transmit('exit\r') 
    #In every itereation check whether the LC is in appropriate state 
    time.sleep(10)
    flag = 0
    plat={}
    xr_pattern=('.*(%s)\s+.*\s+[A-Z]+\s+([A-Z]+\s[A-Za-z]+).*' %lc)
    for i in range(1,11):
        output=rtr.execute('show platform vm')
        if lc in output:
            matchObj = re.search(xr_pattern,output)
            if matchObj:
                loc = matchObj.group(1)
                status = matchObj.group(2)
                log.info('LC: %s , Current status: %s\n' %(loc, status))
                if loc==lc and status=='FINAL Band':
                    final_status = 1
                    break
        time.sleep(60)
    time.sleep(120)
    if final_status == 1:
        log.info("LC is in operational state")
        return True
    else:
        log.info("LC is not up even after 10 min with current status: %s\n" %status)
        return False

'''
Get active RP node in the system in the form of 0/RP0/CPU0 or 0/RP1/CPU0
'''
def get_xr_active_rp(uut1):
   log.info("Entering get_xr_active_rp")
   try:
      # get the show redundency output and parse for the Active RP node
      output = uut1.verify("show redundancy", os_type='xr',
                                parser_type = 'router_show', parse_only='yes')
      return output['active_node'].upper()
   except Exception as err:
      errMsg = 'Error determining active RP - please check the parse\nError:%s' \
                % (str(err))
      log.info(errMsg)
      
'''
Return the active RP node in the form of 0/RP0 or 0/RP1
'''
def get_active_rp(uut1):
   log.info("Entering get_active_rp")
   try:
       active_xr_rp = get_xr_active_rp(uut1)
       return '/'.join(active_xr_rp.split('/')[:2])
   except Exception as err:
       errMsg = 'Error determining active RP - please check the parse\nError:%s' \
                 % (str(err))
       log.info(errMsg)

def check_console_msg(device, chk_msg, sleepTime=2, retryCount=20):
		log.info("Initiating process to check console message- %s" % (chk_msg))

		#
		ret_status = 1
		for i in range (0, int(retryCount)):
			i+=1
			get_console_op = None
			tcl.eval('receive %s "%s"' % (device.handle, chk_msg))

			#
			get_console_op = tcl.eval('set receive_buffer')
			get_console_op = " ".join(get_console_op.split())
			log.info("get_console_op")
			log.info(get_console_op)

			#		
			get_cmd_op = get_line_from_output(chk_msg, get_console_op)

			#
			print("+"*10)
			log.info("chk_msg")
			log.info(chk_msg)

			#
			print("+"*10)
			log.info("get_cmd_op")
			log.info(get_cmd_op)
			print("+"*10)

			#
			if get_cmd_op != None:
				log.info("Succesfully verfied message- %s from console o/p" % (chk_msg))
				log.info(get_cmd_op)
				ret_status = 0
				break
			else:
				log.info("Attempt %d: Unable to find message- %s from console o/p " % (i, chk_msg))
				time.sleep(sleepTime)

			if i == int(retryCount):
				log.error("Failed: unable to find message- %s from console o/p " % (chk_msg))
				ret_status = 1

		#
		if ret_status == 0:
			return get_cmd_op
		else:
			return False

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


def get_line_from_output(expected, actual, after_key=None):
		"""
		This functions gets expected result from output result and returns matched line with more than 2 index found in line
		Usage: _get_line_from_output(expected=<expected result>, actual=<actual result>, after_key=<NONE or expected string>)		

		Inputs:
	
		This function takes following params as input-

		Mandatory:
		
		1) actual (output result)
		2) expected (expected result)
		
		Optional:
	
		1) after_key (string after the expected need to find)
	
		Returns:
		In success case returns: expected line
		In Failure case returns: NONE

		"""
		exp = ".*%s.*" % expected
		after_key_found = False
		if actual != None :
			actual_split = actual.split('\r\n')
			for line in actual_split :
				if after_key != None: 
					matchObj = re.search(after_key , line)
					if matchObj :
						after_key_found = True

				if after_key_found:		
					matchObj = re.search(exp , line)
					if matchObj :
						log.info("Returning- %s" % (line))
						return line

				if after_key == None: 
					matchObj = re.search(exp , line)
					if matchObj :
						if len(line.split()) == 1: continue
						log.info("Returning- %s" % (line))
						return line
		else:
			return None

def get_clock_info(device, param=None):
		# 00:55:13.028 UTC Fri Jan 02 2015
		dict = execute_commands(device, "sh clock")
		if dict == None:
			return False
		else:
			line = dict["sh clock"].split("\r\n")[1]
			dict["hh"] = int(line.split()[0].split(":")[0])
			dict["mm"] = int(line.split()[0].split(":")[1])
			dict["ss"] = int(line.split()[0].split(":")[2].split(".")[0])
			dict["month"] = str(line.split()[3])
			dict["date"] = int(line.split()[4])
			dict["year"] = int(line.split()[5])
		if param != None:
			return dict[param]
		else:
			return dict
			
def set_clock(device, hh=23, mm=59, ss=55, month="dec", date=1, year=2017, no_ntp=False):
		dict = get_clock_info(device)

		if hh==23 and mm==59 and ss==55 and month=="dec" and date == 1 and year==2017:
			date = int(dict["date"]) + 1
		month = dict["month"]
		year = dict["year"]
		if date >= 28:
			log.info("Increasing year %s by 1 year" % (str(dict["year"])))
			year = int(dict["year"]) + 1
			date = 1
		if no_ntp:
			if not device.config("no ntp"): return False
		dict = execute_commands(device, "clock set %d:%d:%d %s %d %d" % (hh,mm,ss,month,date,year))
		sleep(7)
		if dict == None:
			return False
		else:
			return True

def execute_commands(device, cmd_list, error_list_check=True, rtn_err_str_op=False):
		"""
		This function execute the list of command in provided container for device. 
		
		Usage: execute_commands(device=<device handle>, cmd_list=<List of commands to  be executed>, error_list_check=<True or False>,rtn_err_str_op=<True or False> )		
		
		Inputs:
	
		This function takes following params as input-

		Mandatory:-
			
			1) device (device handle)
			2) cmd_list (list of commands to be executed)
			3) error_list_check (True=List of errors pre-defined will be verified OR False=No error string check)
			4)rtn_err_str_op (True= Returns the error message after execution OR False = no error string will be returned)
		Optional:-
			NONE	

		Returns:
		
		Returns output in form of dictionary where keys are command name.
		"""
		out_dict = {}
		exec_errors = ["syntax error" , "Invalid input", "Error:",  "Another request", "internal error", "open shared object file:","No such file or directory", "command not found", "cannot access"]

		if type(cmd_list) == str :
			#Convert command into list format.
			cmd_list = [cmd_list]

		for cmd in cmd_list :
			try :
				out_dict[cmd] = device.execute(cmd)
				if error_list_check:
					if any(x in out_dict[cmd] for x in exec_errors):
						log.error("Execution of command- %s status is: Failure " % (cmd))
						if rtn_err_str_op:
							log.error("Command: \"%s\" output contains an error string: %s." % (cmd, x))
						if not rtn_err_str_op:
							out_dict[cmd] = None
							log.error("Command: \"%s\" output contains an error string: %s , setting output value as None" % (cmd, x))
						else:
							log.info("Execution of command- %s status is: Success " % (cmd))
			except :
				out_dict[cmd] = None
				log.error("Command: \"%s\" is not executed, setting output value as None" % cmd)
			#log.info("Command: %s, Output: %s" % (cmd, out_dict[cmd]))
		return out_dict

