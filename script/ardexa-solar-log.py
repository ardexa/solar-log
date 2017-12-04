#! /usr/bin/python

# Copyright (c) 2013-2017 Ardexa Pty Ltd
#
# This code is licensed under the MIT License (MIT).
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
#
# This script will query a 'solar-log' device. Usage: python ardexa-solar-log.py {IP address} {inverter type} {solar-log-type} {log directory} {debug}
# eg: python ardexa-solar-log.py 192.168.1.55 ABB new /opt/ardexa 0
#
# For use on Linux systems
# Make sure the following tools have been installed
#		sudo apt-get install python-pip
#		sudo pip install requests
#

import requests
import time
import sys
from shutil import copyfile
import os
import urllib2
import datetime
from Supporting import *


PIDFILE = 'ardexa-solar-log-'
# Usage example: eg; python ardexa-solar-log.py 192.168.1.55 ABB new /opt/ardexa 0
USAGE = "python ardexa-solar-log.py {IP address} {inverter type} {solar-log-type} {log directory} {debug}"
LAST = 'last.csv'
CURRENT = 'current.csv'
COMPLETE_STRING = "\"777\":3,"
SMA_LOG_HEADER = "# datetime,inverter,power,daily,status,error,pdc1,udc1,uac,idc1,iac\n"
REFUSOL_LOG_HEADER = "# datetime,inverter,power,daily,status,error,pdc1,udc1,temperature,uac\n"
ABB_LOG_HEADER = "# datetime,inverter,power,daily,status,error,pdc1,pdc2,udc1,udc2,temperature,uac\n"
REFUSOL = 'refusol'
SMA = 'sma'
ABB = 'abb'

# These next items detail the number of items in a **RAW** event line
SMA_HEADER_ITEMS = 12
ABB_HEADER_ITEMS = 13
REFUSOL_HEADER_ITEMS = 11

#~~~~~~~~~~~~~~~~~~~   START Functions ~~~~~~~~~~~~~~~~~~~~~~~


# This will fix up the solar-log time. There are problems with it
def fix_time(time, debug):
	hour, minute, rest = time.split(':')
	seconds, pm = rest.split()

	if (debug > 1):
		print "Before processing.....Hour: ", hour, " Minute: ", minute, " Seconds: ", seconds, " pm: ",pm

	# if pm = PM, convert hour to int, add 12, but NOT if its 12 already
	if (pm.lower() == "pm" ):
		hour_int = int(hour) + 12
		if (hour_int > 23):
			hour_int = hour_int - 12

		hour = str(hour_int)
		
	# if hour is a single digit, add a leading zero
	if (len(str(hour)) == 1):
		hour = '0' + hour

	if (debug > 1):
		print "After processing.....Hour: ", hour, " Minute: ", minute, " Seconds: ", seconds, " pm: ",pm

	return(str(hour) + ":" + str(minute) + ":" + str(seconds))


# This function is for SMA inverters
# This function will strip an Inverter line reported by solar-log
# The line will be in this format: #Date;Time;INV;Pac;DaySum;Status;Error;Pdc1;Udc1;Uac;Idc1;Iac
# Eg; 27/01/17;2:30:00 PM;1;941;4546;7;0;37301;228;252;4457;3720
def SMA_line(line, debug):
	
	if (debug >= 2):
		print "Raw SMA line: ",line

	date_val,time_val,inverter,power,daily,status,error,pdc1,udc1,uac,idc1,iac = line.split(';')

	# Date and time will be in the format: 27/01/17;1:40:00 PM or 27.01.17;1:40:00 PM
	# Convert the date and time to format: 2017-01-29T13:00:00
	# There are problems with the SMA/solar-log time implementation:
	time = fix_time(time, debug)	
	new_datetime = datetime.datetime.strptime(date_val + " " + time_val, '%d/%m/%y  %H:%M:%S').strftime('%Y-%m-%dT%H:%M:%S')

	return_line = str(new_datetime) + "," + str(inverter) + "," + str(power) + "," + str(daily) + "," + str(status) + "," + \
					  str(error) + "," + str(pdc1) + "," + str(udc1) + "," + str(uac) + "," + str(idc1) + "," + str(iac) + "\n"
	
	if (debug >= 2):
		print "Writing the SMA line: ",return_line

	return return_line


# This function is for Refusol inverters
# This function will strip an Inverter line reported by solar-log
# The line will be in this format: #Date;Time;INV;Pac;DaySum;Status;Error;Pdc1;Udc1;Temp;Uac;
# Eg; 01.04.17;12:00:00;1;12703;24000;4;0;12935;565;52;235;
def REFUSOL_line(line, debug):
	
	if (debug >= 2):
		print "Raw Refusol line: ",line

	date_val,time_val,inverter,power,daily,status,error,pdc1,udc1,temperature,uac = line.split(';')

	# Date and time will be in the format: 01.04.17;12:05:00 or 01.04.17;04:25:00
	# Convert the date and time to format: 2017-01-29T13:00:00
	# Refusol has no problems with date and time
	new_datetime = datetime.datetime.strptime(date_val + " " + time_val, '%d.%m.%y  %H:%M:%S').strftime('%Y-%m-%dT%H:%M:%S')

	return_line = str(new_datetime) + "," + str(inverter) + "," + str(power) + "," + str(daily) + "," + str(status) + "," + \
					  str(error) + "," + str(pdc1) + "," + str(udc1) + "," + str(temperature) + "," + str(uac) + "\n"
	
	if (debug >= 2):
		print "Writing the Resfusol line: ",return_line

	return return_line


# This function is for ABB inverters
# This function will strip an Inverter line reported by solar-log
# The line will be in this format: #Date;Time;INV;Pac;DaySum;Status;Error;Pdc1;Pdc2;Udc1;Udc2;Temp
# Eg; 04.04.17;13:25:00;1;20119;43722;6;0;11275;9359;497;414;48
def ABB_line(line, debug):
	
	if (debug >= 2):
		print "Raw ABB line: ",line

	date_val,time_val,inverter,power,daily,status,error,pdc1,pdc2,udc1,udc2,temperature,uac = line.split(';')

	# Date and time will be in the format: 04.04.17;12:05:00 or 01.04.17;04:25:00
	# Convert the date and time to format: 2017-01-29T13:00:00
	# ABB has no problems with date and time
	new_datetime = datetime.datetime.strptime(date_val + " " + time_val, '%d.%m.%y  %H:%M:%S').strftime('%Y-%m-%dT%H:%M:%S')

	return_line = str(new_datetime) + "," + str(inverter) + "," + str(power) + "," + str(daily) + "," + str(status) + "," + \
					  str(error) + "," + str(pdc1) + "," + str(pdc2) + "," + str(udc1) + "," + str(udc2) + "," + str(temperature) + "," + \
					  str(uac) + "\n"

	if (debug >= 2):
		print "Writing the ABB line: ",return_line
	
	return return_line



# This function will split the inverters, so that date and time is in each line, but everything is in a separate line
def split_inverters(line, inverter_type, debug, log_directory):
	items = line.split(';')
	date_val = items[0]
	time_val = items[1]
	del items[:2]

	if (inverter_type == SMA):
		item_number = SMA_HEADER_ITEMS
	elif (inverter_type == ABB):
		item_number = ABB_HEADER_ITEMS
	elif (inverter_type == REFUSOL):
		item_number = REFUSOL_HEADER_ITEMS

	# Subtract the date and time
	item_number = item_number - 2

	length = len(items)
	remainder = length % item_number
	whole = length / item_number

	if (debug >= 2):
		print "Length: ",length
		print "Whole: ",whole
		print "Items: ",items
		print "Inverter type: ",inverter_type

	# Add inverter type to the log directory
	log_directory = os.path.join(log_directory, inverter_type)

	# Once the date and time have been removed, the number of items in the line should be divisible by the item_number
	# If so, process each inverter line separately. Else, report an error
	if (remainder == 0):
		for run in range(whole):
			converted_line = ""
			header = ""
			inverter_slice = items[:item_number]
			if (debug >= 2):
				print "Inverter slice: ",inverter_slice
			del items[:item_number]
			inverter_slice.insert(0, time_val)
			inverter_slice.insert(0, date_val)
			inverter_line = ";".join(inverter_slice)
			inverter_number = inverter_slice[2]
			if (inverter_type == REFUSOL):
				converted_line = REFUSOL_line(inverter_line, debug)
				header = REFUSOL_LOG_HEADER

			elif (inverter_type == SMA):
				converted_line = SMA_line(inverter_line, debug)
				header = SMA_LOG_HEADER

			elif (inverter_type == ABB):
				converted_line = ABB_line(inverter_line, debug)
				header = ABB_LOG_HEADER

			if (debug >= 2):
				print "Split line: ",converted_line

			# Add inverter number to the log directory
			log_dir = ""
			log_dir = os.path.join(log_directory, inverter_number)
			date_str = time.strftime("%d-%b-%Y")
			log_filename = date_str + ".csv"
			write_log(log_dir, log_filename, header, converted_line, debug, True, log_dir, "latest.csv")

	else:
		print "The line reported by solar-log is not recognised. Here is the line: ", line

	return


# This function will query the latest solar-log CSV file
def query_csv(current, ip_addr, debug):
	success = False

	url = 'http://' + ip_addr + '/export_min.csv'
	if (debug >= 2):		
		print "URL being used for CSV download: ",url

	try:
		filew = open(current, "w")

		# Timeout the request 
		response = requests.post(url, timeout=30)
		if (response.status_code == 200):
			if (debug >= 2):
				print "Got a successful response from the solar-log device"
			success = True
			for x in response:
				filew.write(x)
			filew.close()
		else:
			# The script does sometimes return with a 404 error, due to unknown solar-log issues
			if (debug >= 2):
				print "404 error for downloading the CSV file\n"
	except:
			# The script does sometimes return with general error, due to unknown solar-log issues
			if (debug >= 2):
				print "Error in main URL CSV download request loop\n"	 

	return success



# This function will extract any new lines. It operates on the differences between 2 files
# 'last' and 'current'. If there are any differences (ie; new lines), then they will be processed
# by this function
def extract_latest_lines(last, current, inverter_type, debug, log_directory):

	# If 'last' doesn't exist, then copy 'current' to 'last', and return
	if not (os.path.isfile(last)):
		# Copy 'current.csv' to 'last.csv'
		copyfile(current, last)
		if (debug >= 1):
			print '\'last.csv\' file doesn\'t exist. Copying across the \'current.csv\'. file.'
		return

	# If both files exist, process them. Detect any differences.
	if ((os.path.isfile(last)) and (os.path.isfile(current))):
		with open(current, 'r') as current_file:
			with open(last, 'r') as last_file:
				diff = set(current_file).difference(last_file)

		current_file.close()
		last_file.close()
		
		for line in diff:
			newline = line.strip()
			if (debug >= 1):
				datetime = get_datetime()
				print "New Line at time: ",datetime," Line: ",newline

			split_inverters(newline, inverter_type, debug, log_directory)


		# Copy 'current.csv' to 'last.csv'
		copyfile(current, last)

	return 	


# For the new types of Solar Log, issue a prepare URL and wait for it to finish
def prepare_new(ip_addr, debug):
	# URL to use for this query
	url = 'http://' + ip_addr + '/getjp'
	if (debug >= 2):		
		print "URL being used for PREPARE: ",url

	try:
		# Firstly issue a request with the following data
		data = '{"737": null}'
		req = urllib2.Request(url, data)
		response = urllib2.urlopen(req)
		response.close()

		# The process to call *prepare* a CSV file on Solar-Log can take up to 5 mins, sometimes more
		complete = False
		attempt = 0
		while(not complete):
			# Wait for 10 seconds, and check if it has finished 'compiling' the csv file
			time.sleep(10)

			# Issue a request for the CSV file
			data = '{"801":{"777":null,"778":null}}'
			request = urllib2.Request(url, data)
			response = urllib2.urlopen(request)
			for line in response:
				if (line.find(COMPLETE_STRING) != -1):
					complete = True
				if (debug > 1):
					print "Result from URL query: ",line," and complete status: ",complete				
						 	
			response.close()
			attempt += 1
			
			# If it takes more than about 8 minutes, bail out
			if (attempt > 50):
				complete = True

	except:
		if (debug >= 1):
			print "404 error for \'prepare\'\n"


# For the old types of Solar Log, issue a prepare URL and wait about 10 minutes
def prepare_old(ip_addr, debug):
	# URL to use for this query
	url = 'http://' + ip_addr + '/expcsv.dat?1'
	if (debug >= 2):		
		print "URL being used for PREPARE: ",url

	# Request data from Solar Log 
	req = urllib2.Request(url)
	response = urllib2.urlopen(req)


#~~~~~~~~~~~~~~~~~~~   END Functions ~~~~~~~~~~~~~~~~~~~~~~~

# Check the arguments
arguments = check_args(5)
if (len(arguments) < 5):
	print "The arguments cannot be empty. Usage: ", USAGE
	sys.exit(3)

IP_address = arguments[1]
inverter_type = arguments[2]
solar_log_type = arguments[3] 
log_directory = arguments[4]
debug_str = arguments[5]

# Convert debug
retval, debug = convert_to_int(debug_str)
if (not retval):
	print "Debug needs to be an integer number. Value entered: ",debug_str
	sys.exit(4)

# if any args are empty, exit with error
if ((not IP_address) or (not inverter_type) or (not log_directory) or (not solar_log_type)):
	print "The arguments cannot be empty. Usage: ", USAGE
	sys.exit(5)

# If the logging directory doesn't exist, create it
if (not os.path.exists(log_directory)):
	os.makedirs(log_directory)

# Check that no other scripts are running
pidfile = os.path.join(log_directory, PIDFILE) + IP_address + ".pid"
if check_pidfile(pidfile, debug):
	print "This script is already running"
	sys.exit(6)

solar_log_type = solar_log_type.lower()
if ((solar_log_type != 'old') and (solar_log_type != 'new') ):
	print "Solar Log Type can only be \'NEW\' or \'OLD\'"
	sys.exit(7)

inverter_type = inverter_type.lower()
if ((inverter_type != SMA) and (inverter_type != REFUSOL) and (inverter_type != ABB) ):
	print "Only Refusol, ABB or SMA inverters collected by Solar-Log are supported at this time"
	sys.exit(8)

start_time = time.time()
# Issue a query to get the solar-log to 'prepare' the CSV file
if (solar_log_type == 'new'):
	prepare_new(IP_address, debug)
else:
	prepare_old(IP_address, debug)

# Define the current and last files
last_file = os.path.join(log_directory, LAST)
current_file = os.path.join(log_directory, CURRENT)

# Try to download the CSV file from the solar-log device	
success = query_csv(current_file, IP_address, debug)

if (success):
	# If CSV file could be extracted, compare this run to the last
	# New lines will then be written to file
	line = extract_latest_lines(last_file, current_file, inverter_type, debug, log_directory)

elapsed_time = time.time() - start_time
if (debug > 0):
	print "This request took: ",elapsed_time, " seconds."
	print "IP address used: ", IP_address, " and inverter type: ", inverter_type

# Remove the PID file	
if os.path.isfile(pidfile):
	os.unlink(pidfile)

sys.exit(0)













	
