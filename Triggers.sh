#!/bin/csh

# old setenv FRETTA_PATH /ws/ikyalnoo-bgl/pyats/examples/scripts/triggers/triggers/xProjects/Fretta_pmfc_Scripts/Triggers
setenv FRETTA_PATH /ws/ikyalnoo-bgl/Cafy10_Production/xProjects/Fretta_pmfc_Scripts/irfan
setenv TESTBED fretta
# old setenv GIT_REPO /ws/ikyalnoo-bgl/pyats/examples/scripts/triggers/triggers
setenv GIT_REPO /ws/ikyalnoo-bgl/Cafy10_Production
source $GIT_REPO/pyats/bin/activate1.csh
#setenv SPIRENT_HLTAPI_LIBRARY /ws/senandag-bgl/spirent/Spirent_TestCenter_4.64/Spirent_TestCenter_Application_Linux
#setenv SPIRENT_LIBRARY /ws/thia-bgl/spirent/Spirent_TestCenter_4.64/Spirent_TestCenter_Application_Linux
setenv STC_PRIVATE_INSTALL_DIR /auto/wsvarasan-bgl/SPIRENT/Spirent_TestCenter_4.70/Spirent_TestCenter_Application_Linux/API/Python
setenv TCLLIBPATH "/auto/wsvarasan-bgl/SPIRENT/Spirent_TestCenter_4.70/Spirent_TestCenter_Application_Linux /auto/wsvarasan-bgl/SPIRENT/hltapi/HLTAPI_4.52_GA/SourceCode"
setenv HLPYAPI_LOG /auto/wsvarasan-bgl/SPIRENT/logs
setenv AUTOTEST /auto/bglgate/autotest/ats5.3.0
setenv STC_TCL $AUTOTEST/bin/tclsh
setenv TCLLIBPATH1 /auto/wsvarasan-bgl/SPIRENT/hltapi/HLTAPI_4.52_GA/SourceCode
setenv PYTHONPATH "${PYTHONPATH}:$TCLLIBPATH1/hltapiForPython"

echo "starting execution of Trigger scripts in Testbed: $TESTBED" 

easypy $FRETTA_PATH/Triggers_Job.py -tf  /ws/ikyalnoo-bgl/Cafy10_Production/xProjects/Fretta_pmfc_Scripts/irfan/Triggers.yaml -mailto ikyalnoo -mail_subject "Triggers Script"

echo "completed execution of Trigger Script" 
