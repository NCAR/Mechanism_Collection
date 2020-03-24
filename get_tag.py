#!/usr/bin/python3
import argparse
import os
import sys
from ftplib import FTP

from http.client import HTTPSConnection
import json

import requests
headers = {
        "cache-control": "no-cache",
        "x-dreamfactory-api-key": "YOUR_API_KEY"
}


# needs to check that ssl is enabled
#import socket
#socket.ssl
# expect something like<function ssl at 0x4038b0>

# needs to check the python v3 is running

# Parse arguments.  They override those defaults specified in the argument parser
default_tag_server = "chemistrycafe-devel.acom.ucar.edu"
default_preprocessor_server = "www.acom.ucar.edu"
parser = argparse.ArgumentParser(
                    description='Solve a mechanism tag using the sparse solver branch of MusicBox/MICM.',
                    formatter_class=argparse.ArgumentDefaultsHelpFormatter
                    )
parser.add_argument('-tag_id', type=int, required=True,
                    help='Tag number for Chemistry Cafe mechanism tag')
parser.add_argument('-tag_server', type=str, default=default_tag_server,
                    help='url of tag server')
parser.add_argument('-preprocessor', type=str, default=default_preprocessor_server,
                    help='url of preprocessor')
parser.add_argument('-target_dir', type=str, default="",
                    help='url of preprocessor')
parser.add_argument('-overwrite', type=bool, default=False,
                    help='overwrite the target_dir')
 


args = parser.parse_args()


if(args.target_dir):
  outpath = "configured_tags/"+args.target_dir+"/"
else:
  outpath = "configured_tags/"+str(args.tag_id)+"/"

# make target_tag_location director
try:
  if(args.overwrite):
    os.system("rm -rf "+outpath)
    os.mkdir(outpath)
  else:
    os.mkdir(outpath)
except Exception as e:
  print("Directory "+outpath+" already exists.  Delete it if you want new data.")
  print("Exception: "+str(3))
  sys.exit(1)


with open(outpath+'this_configuration', 'w') as configuration_filehandle:
  configuration_filehandle.write(str(args))

# Connection to the Cafe
mechanism_store_location = args.tag_server
mechanism_con = HTTPSConnection(mechanism_store_location)

# Connection to the preprocessor location
processor_location = args.preprocessor
preprocessor_con = HTTPSConnection(processor_location, 3000)

# check connection status:
#exception http.client.HTTPException
#  The base class of the other exceptions in this module. It is a subclass of Exception.
#exception http.client.NotConnected
#  A subclass of HTTPException.

# Simple authorization.  With this there could be 'man-in-middle'.
userAndPass = bytes('username' + ':' + 'password', "utf-8") #convert to utf-8
headers = { 'Authorization' : 'Basic %s' %  userAndPass }

#
#    Collect Tag and preprocess it
#
# Get tag from server
mechanism_con.request('GET', '/node_processes/tags.php?action=return_tag&tag_id='+str(args.tag_id), headers=headers)
res = mechanism_con.getresponse()
# Check status

# Collect the data, write a copy to file
# error testing?
mechanism = res.read()  
mech_json = json.loads(mechanism)
#print(mech_json)
with open(outpath+'mechanism.json', 'w') as mechanism_outfile:
  json.dump(mech_json, mechanism_outfile, indent=2)


#
#    Turn mechanism.json into fortran code!
#
# preprocessor headers
headers = { 'Authorization' : 'Basic %s' %  userAndPass, 'Content-type': 'application/json', 'Accept': 'text/plain' }

# Construct factor_solve_utilities.F90, kinetics_utilities.F90, rate_constants_utilities.F90
mech_json_string = json.dumps(mech_json)
#print(mech_json_string)
res = requests.post("http://"+args.preprocessor+"/constructJacobian", auth=('user', 'pass'), json=mech_json)
print(res.status_code)
print(res.encoding)
print(res.json)
if res.status_code != 200 : exit()
jacobian = res.text
jacobian_json = json.loads(jacobian)
print(jacobian_json)

#service = '/preprocessor/constructJacobian'
#preprocessor_con.request('POST', service, mechanism, headers=headers)
#res = preprocessor_con.getresponse()
#jacobian = res.read()  
#jacobian_json = json.loads(jacobian)


# factor_solve_utilities.F90, kinetics_utilities.F90, rate_constants_utilities.F90
with open(outpath+'kinetics_utilities.F90', 'w') as k_file:
  k_file.write(jacobian_json["kinetics_utilities_module"])

with open(outpath+'rate_constants_utility.F90', 'w') as r_file:
  r_file.write(jacobian_json["rate_constants_utility_module"])

with open(outpath+'factor_solve_utilities.F90', 'w') as f_file:
  f_file.write(jacobian_json["factor_solve_utilities_module"])

