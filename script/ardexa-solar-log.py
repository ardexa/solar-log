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

# This script will query a 'solar-log' device. Usage: sudo python ./ardexa-solar-log.py {inverter-type} {IP Address}
# eg: sudo python ./ardexa-solar-log.py refusol 192.168.0.109
# eg; sudo python ./ardexa-solar-log.py SMA 192.168.0.10
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

# Change these 2 settings to suit your installation, if required
DEBUG = 0
LOG_DIR = '/opt/ardexa/solar-log/logs/'


DIR = '/opt/ardexa/solar-log/'
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


# This function logs the inverter data to both a 'date' file, and a 'latest' file
# Directory structure is as follows: LOG_DIR + inverter_type + inverter_number
def write_log(inverter_type, inverter_number, header, logline):
	write_header = False
	# Check date file exists
	date_str = (time.strftime("%d-%b-%Y"))

	# The logging directory is the LOG_DIR + inverter_type and then inverter_number
	log_directory = os.path.join(LOG_DIR, inverter_type)
	log_directory = os.path.join(log_directory, inverter_number)
	if not os.path.exists(log_directory):
		os.makedirs(log_directory)

	full_path_date = os.path.join(log_directory, date_str + ".csv")
	full_path_latest = os.path.join(log_directory, "latest.csv")

	if (DEBUG > 1):
		print "FULL: ", full_path_date
		print "LATEST: ", full_path_latest

	# If the date file doesn't exist, create it, and remove the "latest" file
	if not (os.path.isfile(full_path_date)):
		if (DEBUG > 1):
			print "Date file doesn't exist: ", full_path_date, " . Removing the default file"
			# Remove the default file (beware, it may not exist)
		if (os.path.isfile(full_path_latest)):
			os.remove(full_path_latest)
		write_header = True


	# Now create both (or open both) and write to them
	if (DEBUG >= 1):
		print "Writing the line: ", logline

	write_latest = open(full_path_latest,"a")
	write_date = open(full_path_date,"a")
	if (write_header):
		write_date.write(header)
		write_latest.write(header)

	write_date.write(logline)
	write_latest.write(logline)
	write_date.close()
	write_latest.close()


# This will fix up the solar-log time. There are problems with it
def fix_time(time):
	hour, minute, rest = time.split(':')
	seconds, pm = rest.split()

	if (DEBUG > 1):
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

	if (DEBUG > 1):
		print "After processing.....Hour: ", hour, " Minute: ", minute, " Seconds: ", seconds, " pm: ",pm

	return(str(hour) + ":" + str(minute) + ":" + str(seconds))


# This function is for SMA inverters
# This function will strip an Inverter line reported by solar-log
# The line will be in this format: #Date;Time;INV;Pac;DaySum;Status;Error;Pdc1;Udc1;Uac;Idc1;Iac
# Eg; 27/01/17;2:30:00 PM;1;941;4546;7;0;37301;228;252;4457;3720
def SMA_line(line):
	
	if (DEBUG >= 2):
		print "Raw SMA line: ",line

	date,time,inverter,power,daily,status,error,pdc1,udc1,uac,idc1,iac = line.split(';')
	# Date and time will be in the format: 27/01/17;1:40:00 PM or 27.01.17;1:40:00 PM
	# Convert the date and time to format: 2017-01-29T13:00:00
	# There are problems with the SMA/solar-log time implementation:
	time = fix_time(time)
	
	new_datetime = datetime.datetime.strptime(date + " " + time, '%d/%m/%y  %H:%M:%S').strftime('%Y-%m-%dT%H:%M:%S')

	return_line = str(new_datetime) + "," + str(inverter) + "," + str(power) + "," + str(daily) + "," + str(status) + "," + \
					  str(error) + "," + str(pdc1) + "," + str(udc1) + "," + str(uac) + "," + str(idc1) + "," + str(iac) + "\n"
	
	if (DEBUG >= 2):
		print "Writing the SMA line: ",return_line

	return return_line

# This function is for Refusol inverters
# This function will strip an Inverter line reported by solar-log
# The line will be in this format: #Date;Time;INV;Pac;DaySum;Status;Error;Pdc1;Udc1;Temp;Uac;
# Eg; 01.04.17;12:00:00;1;12703;24000;4;0;12935;565;52;235;
def REFUSOL_line(line):
	
	if (DEBUG >= 2):
		print "Raw Refusol line: ",line

	date,time,inverter,power,daily,status,error,pdc1,udc1,temperature,uac = line.split(';')
	# Date and time will be in the format: 01.04.17;12:05:00 or 01.04.17;04:25:00
	# Convert the date and time to format: 2017-01-29T13:00:00
	# Refusol has no problems with date and time
	
	new_datetime = datetime.datetime.strptime(date + " " + time, '%d.%m.%y  %H:%M:%S').strftime('%Y-%m-%dT%H:%M:%S')

	return_line = str(new_datetime) + "," + str(inverter) + "," + str(power) + "," + str(daily) + "," + str(status) + "," + \
					  str(error) + "," + str(pdc1) + "," + str(udc1) + "," + str(temperature) + "," + str(uac) + "\n"
	
	if (DEBUG >= 2):
		print "Writing the Resfusol line: ",return_line

	return return_line


# This function is for ABB inverters
# This function will strip an Inverter line reported by solar-log
# The line will be in this format: #Date;Time;INV;Pac;DaySum;Status;Error;Pdc1;Pdc2;Udc1;Udc2;Temp
# Eg; 04.04.17;13:25:00;1;20119;43722;6;0;11275;9359;497;414;48
def ABB_line(line):
	
	if (DEBUG >= 2):
		print "Raw ABB line: ",line

	date,time,inverter,power,daily,status,error,pdc1,pdc2,udc1,udc2,temperature,uac = line.split(';')
	# Date and time will be in the format: 04.04.17;12:05:00 or 01.04.17;04:25:00
	# Convert the date and time to format: 2017-01-29T13:00:00
	# ABB has no problems with date and time
	
	new_datetime = datetime.datetime.strptime(date + " " + time, '%d.%m.%y  %H:%M:%S').strftime('%Y-%m-%dT%H:%M:%S')

	return_line = str(new_datetime) + "," + str(inverter) + "," + str(power) + "," + str(daily) + "," + str(status) + "," + \
					  str(error) + "," + str(pdc1) + "," + str(pdc2) + "," + str(udc1) + "," + str(udc2) + "," + str(temperature) + "," + \
					  str(uac) + "\n"

	if (DEBUG >= 2):
		print "Writing the ABB line: ",return_line
	
	return return_line


# Check that the correct number of arguments, and extract the IP Address of solar-log
def check_args():
	# Get the IP Address of Solar-Log from the argument
	if (len(sys.argv) != 3):
		print "There can only be 3 arguments, the script name, inverter type and the IP Address"
		return ""
	else:
		# return the inverter type and the IP address
		return str(sys.argv[1]), str(sys.argv[2])


# Check that a process is not running more than once, using PIDFILE
def check_PIDFILE(pidfile):

	# Check PID exists and see if the PID is running
	if os.path.isfile(pidfile):
		pidfile_handle = open(pidfile, 'r')
		try: 
			pid = int(pidfile_handle.read())
			if (check_pid(pid)):
				return True
		except:
			# do nothing here
			pass
			
		pidfile_handle.close()
		# PID is not active, remove the PID file
		os.unlink(pidfile)

	# Create a PID file, to ensure this is script is only run once (at a time)
	pid = str(os.getpid())
	file(pidfile, 'w').write(pid)

	return False


# This function will query the solar-log CSV file
def query_csv(current, ip_addr):

	success = False

	url = 'http://' + ip_addr + '/export_min.csv'
	if (DEBUG >= 2):		
		print "URL being used for CSV download: ",url

	try:
		filew = open(current, "w")

		# Timeout the request 
		response = requests.post(url, timeout=30)
		if (response.status_code == 200):
			if (DEBUG >= 2):
				print "Got a successful response from the solar-log device"
			success = True
			for x in response:
				filew.write(x)
			filew.close()
		else:
			# The script does sometimes return with a 404 error, due to unknown solar-log issues
			if (DEBUG >= 2):
				print "404 error for downloading the CSV file\n"
	except:
			# The script does sometimes return with general error, due to unknown solar-log issues
			if (DEBUG >= 2):
				print "Error in main URL CSV download request loop\n"	 

	return success

# This function will split the inverters, so that date and time is in each line, but everything is in a separate line
def split_inverters(line, inverter_type):
	items = line.split(';')
	date = items[0]
	time = items[1]
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

	if (DEBUG >= 2):
		print "Length: ",length
		print "Whole: ",whole
		print "Items: ",items
		print "Inverter type: ",inverter_type

	# Once the date and time have been removed, the number of items in the line should be divisible by the item_number
	# If so, process each inverter line separately
	# Else, report an error
	if (remainder == 0):
		for run in range(whole):
			inverter_slice = items[:item_number]
			if (DEBUG >= 2):
				print "Inverter slice: ",inverter_slice
			del items[:item_number]
			inverter_slice.insert(0, time)
			inverter_slice.insert(0, date)
			inverter_line = ";".join(inverter_slice)
			inverter_number = inverter_slice[2]
			if (inverter_type == REFUSOL):
				converted_line = REFUSOL_line(inverter_line)
				if (DEBUG >= 2):
					print "Split line: ",converted_line
				write_log(inverter_type, inverter_number, REFUSOL_LOG_HEADER, converted_line)

			elif (inverter_type == SMA):
				converted_line = SMA_line(inverter_line)
				if (DEBUG >= 2):
					print "Split line: ",converted_line
				write_log(inverter_type, inverter_number, SMA_LOG_HEADER, converted_line)

			elif (inverter_type == ABB):
				converted_line = ABB_line(inverter_line)
				if (DEBUG >= 2):
					print "Split line: ",converted_line
				write_log(inverter_type, inverter_number, ABB_LOG_HEADER, converted_line)


	else:
		print "The line reported by solar-log is not recognised. Here is the line: ", line
		sys.exit(3)

# This function will extract any new lines. It operates on the differences between 2 files
# 'last' and 'current'. If there are any differences (ie; new lines), then they will be processed
# by this function
def extract_latest_lines(last, current, inverter_type):

	converted_line = ""

	# If 'last' doesn't exist, then copy 'current' to 'last', and process. No results will be extracted anyway
	if not (os.path.isfile(last)):
		# Copy 'current.csv' to 'last.csv'
			copyfile(current, last)
			if (DEBUG >= 1):
				print '\'last.csv\' file doesn\'t exist. Copy across the \'current.csv\'. file.'


	# If both files exist, process them. Detect any differences.
	if ((os.path.isfile(last)) and (os.path.isfile(current))):
		with open(current, 'r') as current_file:
			with open(last, 'r') as last_file:
				diff = set(current_file).difference(last_file)

		current_file.close()
		last_file.close()

		localtime = time.asctime( time.localtime(time.time()) )
		for line in diff:
			newline = line.strip()
			if (DEBUG >= 1):
				print "New Line at time: ",localtime," Line: ",newline

			split_inverters(newline, inverter_type)


		# Copy 'current.csv' to 'last.csv'
		copyfile(current, last)

		# For this test, append line diff into a file

	return converted_line	


def prepare(ip_addr):
	# URL to use for this query
	url = 'http://' + ip_addr + '/getjp'
	if (DEBUG >= 2):		
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
				if (DEBUG > 1):
					print "Result from URL query: ",line," and complete status: ",complete				
						 	
			response.close()
			attempt += 1
			
			# If it takes more than about 8 minutes, bail out
			if (attempt > 50):
				complete = True

	except:
		print "404 error for \'prepare\'\n"

# This function will check whether a PID is currently running
def check_pid(pid):  	

	try:
		# A Kill of 0 is to check if the PID is active. It won't kill the process
		os.kill(pid, 0)
		if (DEBUG > 1):
			print "Script has a PIDFILE where the process is still running"
		return True
	except OSError:
		if (DEBUG > 1):
			print "Script does not appear to be running"
		return False
	

#~~~~~~~~~~~~~~~~~~~   END Functions ~~~~~~~~~~~~~~~~~~~~~~~

# If the operating and logging directories don't exist, create them
if not os.path.exists(DIR):
	os.makedirs(DIR)

if not os.path.exists(LOG_DIR):
	os.makedirs(LOG_DIR)

inverter_type, ip_address = check_args()
# if IP address is empty, exit with error
if not ip_address:
	print "The IP Address cannot be empty"
	sys.exit(2)

inverter_type = inverter_type.lower()
if ((inverter_type != SMA) and (inverter_type != REFUSOL) and (inverter_type != ABB) ):
	print "Only Refusol, ABB or SMA inverters collected by Solar-Log are supported at this time"
	sys.exit(3)

# Check that no other scripts are running
pidfile =  str(DIR + 'ardexa-solar-log.pid')
if check_PIDFILE(pidfile):
	print "This script is already running"
	sys.exit(4)


start_time = time.time()
# Issue a query to get the solar-log to 'prepare' the CSV file
prepare(ip_address)

# Try to download the CSV file from the solar-log device	
success = query_csv(DIR + CURRENT, ip_address)

line = ""
if (success):
	# If CSV file could be extracted, compare this run to the last
	line = extract_latest_lines(DIR + LAST, DIR + CURRENT, inverter_type)

elapsed_time = time.time() - start_time
if (DEBUG >= 1):
	print "This request took: ",elapsed_time, " seconds."
	print "IP address used: ", ip_address, " and inverter type: ", inverter_type

# Remove the PID file	
if os.path.isfile(pidfile):
	os.unlink(pidfile)

# Print the line if one is available, otherwise the success of the 'query_csv' command
if not line:
	print success
else:
	print line
	
