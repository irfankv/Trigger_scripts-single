# To run the job:
# easypy -tf $VIRTUAL_ENV/ats/examples/tests/connection_example_conf.yaml
#            $VIRTUAL_ENV/ats/examples/jobs/connection_example.py
# Description: This example uses a sample testbed, connects to a device,
#              and executes some commands
import os
from ats.easypy.easypy import run

def main():
    # Find the examples/tests directory where the test script exists
    #traff_type value can be 100,200,150 or 100_200 or 100_150 or 150_200,100_150_200
    test_path = (os.path.dirname(os.path.abspath(__file__))
                 .replace('/jobs', '/tests'))
    acl_intf = []
    for i in range(3,252):
        acl_intf.append("BVI"+str(i))

    run(testscript='/ws/ikyalnoo-bgl/Cafy10_Production/xProjects/Fretta_pmfc_Scripts/irfan/Triggers.py',\
        # run_ids=['common_setup','ConfigUnconfig','common_cleanup'],\
        run_ids=['common_setup', 'ConfigUnconfig', 'common_cleanup'], \
        #run_ids=['common_setup','Scale_Stress27$','Scale_Stress28$','Scale_Stress35$','Scale_Stress36$','Scale_Stress39$','Scale_Stress40$','Scale_Stress41$','Scale_Stress42$','Scale_Stress43$','Scale_Stress44$','common_cleanup'],\
        #skip_ids=['Scale_Stress13','Scale_Stress18'],\
        R1='fretta',\
        R1a = 'fretta-a',\
        R2 = "tortin",
        IntfList = ['TenGigE0/6/0/4/2'],\
        ControllerList = ['0/2/0/0','0/2/0/1'],\
        TraffPortList = ['TenGigE0/4/0/28/1'],\
        IterCnt = 100,\
        RepeatCnt = 100,\
        ProcessList = ['l2fib_mgr'],\
        MemLeakProcessList = [],\
        ShowCmdList = [],
        CliList=["""interface Bundle-Ether3300.2
                        no service-policy input main-irf-combination-V4
                        no ipv4 bgp policy propagation input qos-group destination

                        !
                        interface Bundle-Ether3300.1
                         no service-policy input main-irf-combination
                         no ipv6 bgp policy propagation input qos-group destination
                        !
                    """,], \
        unconfig="""
            no interface bundle-ether 900.*
        """, \
        config = """ 
        
        """ ,\
        #clear mpls ldp neighbor ,clear l2vpn bridge-domain all clear ospf process clear ethernet cfm peer meps all
        clear_cli_list = ["clear mpls ldp neighbor "] ,
        tftp_path='/auto/tftp-blr-users3/varasan/',\
        ConvergTime = 100,\
        Traffic = "off",\
        tftp_addr='10.105.224.25',\
        #Mgmt_Gw='10.105.247.1',\
        #mgmt_mask='255.255.255.0',\
        #mgmt_port_r1='MgmtEth0/RP0/CPU0/0',\
        #mgmt_port_r2='MgmtEth0/RP0/CPU0/0',\
        Location = '0/0/CPU0' )
        
'''
IntfList : list number of interfaces to be a part of trigger
TraffPortList : list number of interfaces for which you need to verify traffic recovery post trigger
IterCnt : Total iteration count of each trigger inside test case. After each iteration the validation part takes place
RepeatCnt : Total repeat count of the trigger prior to validation. For continuous execution.
ProcessList : List of process names for Process restart and crash scenarios
Location : Location of the processes running for process restart/crash scenarios
MemLeakProcessList : List of process names to verify memory leaks post triggers
ShowCmdList : List of show commands to be executed and verify memory leaks or crash
CliList : Give each configuration as a single statement with in quotes with \n inserted for next line of CLI execution
ConvergTime : The amount of time to wait before verifying traffic after any trigger
Traffic : Whether the traffic validation is required or not. If yes then given option as "on" and keep the traffic running in the background before starting the script
LcList : List of LC locations to be used for reload test cases.
'''



       