"""
This script will query one or more Solar Log devices
eg: solarlog_ardexa log 192.168.1.55 ABB new /opt/ardexa
{IP Address} = ..something like: 192.168.1.4
{inverter type} = SMA, REFUSOL, ABB, SOLARMAX are currently supported
{log directory} = logging directory; eg; /opt/logging/
{type of query} = "get" ... get the data
"""

# Copyright (c) 2018 Ardexa Pty Ltd
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


from __future__ import print_function
import time
import os
import sys
from shutil import copyfile
import urllib2
import datetime
import click
import requests
import ardexaplugin as ap

PY3K = sys.version_info >= (3, 0)

PIDFILE = 'ardexa-solar-log-'
LAST = 'last.csv'
CURRENT = 'current.csv'
COMPLETE_STRING = "\"777\":3,"
SMA_LOG_HEADER_LST = ["Datetime", "Inverter", "AC power (W)", "Daily Energy (Wh)", "Status", "Error", "DC Power 1 (W)",
                      "DC Voltage 1 (V)", "AC Voltage (V)", "DC Current 1 (A)", "AC Current (A)"]
REFUSOL_LOG_HEADER_LST = ["Datetime", "Inverter", "AC power (W)", "Daily Energy (Wh)", "Status", "Error", "DC Power 1 (W)",
                          "DC Voltage 1 (V)", "Temperature (C)", "AC Voltage (V)"]
ABB_LOG_HEADER_LST = ["Datetime", "Inverter", "AC power (W)", "Daily Energy (Wh)", "Status", "Error", "DC Power 1 (W)",
                      "DC Power 2 (W)", "DC Voltage 1 (V)", "DC Voltage 2 (V)", "Temperature (C)", "AC Voltage (V)"]
SOLARMAX_LOG_HEADER_LST = ["Datetime", "Inverter", "AC power (W)", "Daily Energy (Wh)", "Status", "DC Power 1 (W)",
                           "DC Power 2 (W)", "DC Power 3 (W)", "DC Voltage 1 (V)", "DC Voltage 2 (V)", "DC Voltage 3 (V)",
                           "Temperature (C)", "AC Voltage (V)"]

REFUSOL = 'refusol'
SMA = 'sma'
ABB = 'abb'
SOLARMAX = 'solarmax'

# These next items detail the number of items in a **RAW** event line
SMA_HEADER_ITEMS = 12
ABB_HEADER_ITEMS = 13
REFUSOL_HEADER_ITEMS = 11
SOLARMAX_HEADER_ITEMS = 14


def fix_time(sltime, debug):
    """ This will fix up the solar-log time. There are problems with it"""
    hour, minute, rest = sltime.split(':')
    seconds, pm = rest.split()

    if debug > 1:
        print("Before processing.....Hour: ", hour, " Minute: ", minute, " Seconds: ", seconds, " pm: ", pm)

    # if pm = PM, convert hour to int, add 12, but NOT if its 12 already
    if pm.lower() == "pm":
        hour_int = int(hour) + 12
        if hour_int > 23:
            hour_int = hour_int - 12

        hour = str(hour_int)

    # if hour is a single digit, add a leading zero
    if len(str(hour)) == 1:
        hour = '0' + hour

    if debug > 1:
        print("After processing.....Hour: ", hour, " Minute: ", minute, " Seconds: ", seconds, " pm: ", pm)

    return str(hour) + ":" + str(minute) + ":" + str(seconds)


def sma_line(line, debug):
    """This function is for SMA inverters
        This function will strip an Inverter line reported by solar-log
        The line will be in this format: #Date;Time;INV;Pac;DaySum;Status;Error;Pdc1;Udc1;Uac;Idc1;Iac
        Eg; 27/01/17;2:30:00 PM;1;941;4546;7;0;37301;228;252;4457;3720"""

    if debug >= 2:
        print("Raw SMA line: ", line)

    date_val, time_val, inverter, power, daily, status, error, pdc1, udc1, uac, idc1, iac = line.split(';')

    # Date and time will be in the format: 27/01/17;1:40:00 PM or 27.01.17;1:40:00 PM
    # Convert the date and time to format: 2017-01-29T13:00:00
    # There are problems with the SMA/solar-log time implementation:
    time_val = fix_time(time_val, debug)
    new_datetime = datetime.datetime.strptime(date_val + " " + time_val, '%d/%m/%y  %H:%M:%S').strftime('%Y-%m-%dT%H:%M:%S')

    return_line = str(new_datetime) + "," + str(inverter) + "," + str(power) + "," + str(daily) + "," + str(status) + "," + \
                  str(error) + "," + str(pdc1) + "," + str(udc1) + "," + str(uac) + "," + str(idc1) + "," + str(iac) + "\n"

    if debug >= 2:
        print("Writing the SMA line: ", return_line)

    return return_line


def refusol_line(line, debug):
    """ This function is for Refusol inverters
        This function will strip an Inverter line reported by solar-log
        The line will be in this format: #Date;Time;INV;Pac;DaySum;Status;Error;Pdc1;Udc1;Temp;Uac;
        Eg; 01.04.17;12:00:00;1;12703;24000;4;0;12935;565;52;235;"""

    if debug >= 2:
        print("Raw Refusol line: ", line)

    date_val, time_val, inverter, power, daily, status, error, pdc1, udc1, temperature, uac = line.split(';')

    # Date and time will be in the format: 01.04.17;12:05:00 or 01.04.17;04:25:00
    # Convert the date and time to format: 2017-01-29T13:00:00
    # Refusol has no problems with date and time
    new_datetime = datetime.datetime.strptime(date_val + " " + time_val, '%d.%m.%y  %H:%M:%S').strftime('%Y-%m-%dT%H:%M:%S')

    return_line = str(new_datetime) + "," + str(inverter) + "," + str(power) + "," + str(daily) + "," + str(status) + "," + \
                  str(error) + "," + str(pdc1) + "," + str(udc1) + "," + str(temperature) + "," + str(uac) + "\n"

    if debug >= 2:
        print("Writing the Resfusol line: ", return_line)

    return return_line


def abb_line(line, debug):
    """This function is for ABB inverters
    This function will strip an Inverter line reported by solar-log
    The line will be in this format: #Date;Time;INV;Pac;DaySum;Status;Error;Pdc1;Pdc2;Udc1;Udc2;Temp
    Eg; 04.04.17;13:25:00;1;20119;43722;6;0;11275;9359;497;414;48"""

    if debug >= 2:
        print("Raw ABB line: ", line)

    date_val, time_val, inverter, power, daily, status, error, pdc1, pdc2, udc1, udc2, temperature, uac = line.split(';')

    # Date and time will be in the format: 04.04.17;12:05:00 or 01.04.17;04:25:00
    # Convert the date and time to format: 2017-01-29T13:00:00
    # ABB has no problems with date and time
    new_datetime = datetime.datetime.strptime(date_val + " " + time_val, '%d.%m.%y  %H:%M:%S').strftime('%Y-%m-%dT%H:%M:%S')

    return_line = str(new_datetime) + "," + str(inverter) + "," + str(power) + "," + str(daily) + "," + str(status) + "," + \
                  str(error) + "," + str(pdc1) + "," + str(pdc2) + "," + str(udc1) + "," + str(udc2) + "," + str(temperature) + "," + \
                  str(uac) + "\n"

    if debug >= 2:
        print("Writing the ABB line: ", return_line)

    return return_line


def solarmax_line(line, debug):
    """ This function is for Solarmax inverters
        This function will strip an Inverter line reported by solar-log
        The line will be in this format: #Date;Time;INV;Pac;DaySum;Status;Pdc1;Pdc2;Pdc3;Udc1;Udc2;Udc3;Temp;Uac
        Eg;  13.03.18;13:30:00;1;28853;140433;36;11475;11849;11449;645;640;645;59;0;"""

    if debug >= 2:
        print("Raw Solarmax line: ", line)

    date_val, time_val, inverter, power, daily, status, pdc1, pdc2, pdc3, udc1, udc2, udc3, temperature, uac = line.split(';')

    # Date and time will be in the format: 13.03.18;13:30:00
    # Convert the date and time to format: 2017-01-29T13:00:00Z
    # ABB has no problems with date and time
    new_datetime = datetime.datetime.strptime(date_val + " " + time_val, '%d.%m.%y  %H:%M:%S').strftime('%Y-%m-%dT%H:%M:%S%z')

    return_line = str(new_datetime) + "," + str(inverter) + "," + str(power) + "," + str(daily) + "," + str(status) + "," + \
                  str(pdc1) + "," + str(pdc2) + "," + str(pdc3) + "," + str(udc1) + "," + str(udc2) + "," + str(udc3) + "," + str(temperature) + "," + \
                  str(uac) + "\n"

    if debug >= 2:
        print("Writing the Solarmax line: ", return_line)

    return return_line


def split_inverters(line, inverter_type, debug, log_directory):
    """# This function will split the inverters, so that date and time is in each line, but everything is in a separate line"""

    items = line.split(';')
    date_val = items[0]
    time_val = items[1]
    del items[:2]

    if inverter_type == SMA:
        item_number = SMA_HEADER_ITEMS
    elif inverter_type == ABB:
        item_number = ABB_HEADER_ITEMS
    elif inverter_type == REFUSOL:
        item_number = REFUSOL_HEADER_ITEMS
    elif inverter_type == SOLARMAX:
        item_number = SOLARMAX_HEADER_ITEMS

    # Subtract the date and time
    item_number = item_number - 2
    length = len(items)
    remainder = length % item_number
    whole = length / item_number

    if debug >= 2:
        print("Length: ", length)
        print("Whole: ", whole)
        print("Items: ", items)
        print("Inverter type: ", inverter_type)

    # Add inverter type to the log directory
    log_directory = os.path.join(log_directory, inverter_type)

    # Once the date and time have been removed, the number of items in the line should be divisible by the item_number
    # If so, process each inverter line separately. Else, report an error
    if remainder == 0:
        for run in range(whole):
            converted_line = ""
            header = ""
            inverter_slice = items[:item_number]
            if debug >= 2:
                print("Inverter slice: ", inverter_slice)

            del items[:item_number]
            inverter_slice.insert(0, time_val)
            inverter_slice.insert(0, date_val)
            inverter_line = ";".join(inverter_slice)
            inverter_number = inverter_slice[2]
            if inverter_type == REFUSOL:
                converted_line = refusol_line(inverter_line, debug)
                header = "# " + ",".join(REFUSOL_LOG_HEADER_LST) + "\n"

            elif inverter_type == SMA:
                converted_line = sma_line(inverter_line, debug)
                header = "# " + ",".join(SMA_LOG_HEADER_LST) + "\n"

            elif inverter_type == ABB:
                converted_line = abb_line(inverter_line, debug)
                header = "# " + ",".join(ABB_LOG_HEADER_LST) + "\n"

            elif inverter_type == SOLARMAX:
                converted_line = solarmax_line(inverter_line, debug)
                header = "# " + ",".join(SOLARMAX_LOG_HEADER_LST) + "\n"

            if debug >= 2:
                print("Split line: ", converted_line)

            # Add inverter number to the log directory
            log_dir = ""
            log_dir = os.path.join(log_directory, inverter_number)
            date_str = time.strftime("%d-%b-%Y")
            log_filename = date_str + ".csv"
            ap.write_log(log_dir, log_filename, header, converted_line, debug, True, log_dir, "latest.csv")

    else:
        print("The line reported by solar-log is not recognised. Here is the line: ", line)


def query_csv(current, ip_addr, debug):
    """ This function will query the latest solar-log CSV file"""

    success = False

    url1 = 'http://' + ip_addr + '/export_min.csv'
    url2 = 'http://' + ip_addr + '/sec/export_min.csv'
    if debug >= 2:
        print("URL being used for CSV download: ", url1)

    try:
        filew = open(current, "w")

        # Timeout the request
        response = requests.post(url1, timeout=30)
        if response.status_code == 200:
            if debug >= 2:
                print("Got a successful response from the solar-log device")
            success = True
            for item in response:
                filew.write(item)
            filew.close()
        else:
            # The script does sometimes return with a 404 error, due to unknown solar-log issues
            # if so, try a different URL
            if debug >= 2:
                print("Error for downloading the CSV file with URL:", url1, " Trying:", url2)

            # Timeout the request
            response = requests.post(url2, timeout=30)
            if response.status_code == 200:
                if debug >= 2:
                    print("Got a successful response from the solar-log device")
                success = True
                for item in response:
                    filew.write(item)
                filew.close()
            else:
                # The script does sometimes return with a 404 error, due to unknown solar-log issues
                # if so, try a different URL
                if debug >= 2:
                    print("Error for downloading the CSV file with URL:", url2)

    except:
        # The script does sometimes return with general error, due to unknown solar-log issues
        if debug >= 2:
            print("Error in main URL CSV download request loop")

    return success



def extract_latest_lines(last, current, inverter_type, debug, log_directory):
    """ This function will extract any new lines. It operates on the differences between 2 files
        'last' and 'current'. If there are any differences (ie; new lines), then they will be processed
        by this function"""

    # If 'last' doesn't exist, then copy 'current' to 'last', and return
    if not os.path.isfile(last):
        # Copy 'current.csv' to 'last.csv'
        copyfile(current, last)
        if debug >= 1:
            print('\'last.csv\' file doesn\'t exist. Copying across the \'current.csv\'. file.')
        return

    # If both files exist, process them. Detect any differences.
    if os.path.isfile(last) and os.path.isfile(current):
        with open(current, 'r') as current_file:
            with open(last, 'r') as last_file:
                diff = set(current_file).difference(last_file)

        current_file.close()
        last_file.close()

        for line in diff:
            newline = line.strip()
            if debug >= 1:
                dt = datetime.datetime.now()
                print("New Line at time: ", dt, " Line: ", newline)

            split_inverters(newline, inverter_type, debug, log_directory)

        # Copy 'current.csv' to 'last.csv'
        copyfile(current, last)

    return


def prepare_new(ip_addr, debug):
    """For the new types of Solar Log, issue a prepare URL and wait for it to finish"""

    # URL to use for this query
    url = 'http://' + ip_addr + '/getjp'
    if debug >= 2:
        print("URL being used for PREPARE: ", url)

    try:
        # Firstly issue a request with the following data
        data = '{"737": null}'
        req = urllib2.Request(url, data)
        response = urllib2.urlopen(req)
        response.close()

        # The process to call *prepare* a CSV file on Solar-Log can take up to 5 mins, sometimes more
        complete = False
        attempt = 0
        while not complete:
            # Wait for 10 seconds, and check if it has finished 'compiling' the csv file
            time.sleep(10)

            # Issue a request for the CSV file
            data = '{"801":{"777":null,"778":null}}'
            request = urllib2.Request(url, data)
            response = urllib2.urlopen(request)
            for line in response:
                if line.find(COMPLETE_STRING) != -1:
                    complete = True
                if debug > 1:
                    print("Result from URL query: ", line, " and complete status: ", complete)

            response.close()
            attempt += 1

            # If it takes more than about 8 minutes, bail out
            if attempt > 50:
                complete = True

    except:
        if debug >= 1:
            print("404 error for \'prepare\'\n")


def prepare_old(ip_addr, debug):
    """ For the old types of Solar Log, issue a prepare URL and wait about 10 minutes"""

    # URL to use for this query
    url = 'http://' + ip_addr + '/expcsv.dat?1'
    if debug >= 2:
        print("URL being used for PREPARE: ", url)

    # Request data from Solar Log
    req = urllib2.Request(url)
    response = urllib2.urlopen(req)
    if debug > 1:
        print("Response", response)


class Config(object):
    """Config object for click"""
    def __init__(self):
        self.verbosity = 0


CONFIG = click.make_pass_decorator(Config, ensure=True)

@click.group()
@click.option('-v', '--verbose', count=True)
@CONFIG
def cli(config, verbose):
    """Command line entry point"""
    config.verbosity = verbose


@cli.command()
@click.argument('ip_address')
@click.argument('inverter_type')
@click.argument('solar_log_type')
@click.argument('output_directory')
@CONFIG
def log(config, ip_address, inverter_type, solar_log_type, output_directory):
    """Connect to the target IP address and log the inverter output for the given bus addresses"""

    # If the logging directory doesn't exist, create it
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # Check that no other scripts are running
    # Add IP Address to the PIDFILE
    pidfile = os.path.join(output_directory, PIDFILE) + ip_address + ".pid"
    if ap.check_pidfile(pidfile, config.verbosity):
        print("This script is already running")
        sys.exit(3)

    solar_log_type = solar_log_type.lower()
    if solar_log_type not in ('old', 'new'):
        print("Solar Log Type can only be \'NEW\' or \'OLD\'")
        sys.exit(7)

    inverter_type = inverter_type.lower()
    if inverter_type not in (SMA, REFUSOL, ABB, SOLARMAX):
        print("Only Solarmax, Refusol, ABB or SMA inverters collected by Solar-Log are supported at this time")
        sys.exit(8)

    start_time = time.time()

    # Issue a query to get the solar-log to 'prepare' the CSV file
    if solar_log_type == 'new':
        prepare_new(ip_address, config.verbosity)
    else:
        prepare_old(ip_address, config.verbosity)

    # Define the current and last files
    last_file = os.path.join(output_directory, LAST)
    current_file = os.path.join(output_directory, CURRENT)

    # Try to download the CSV file from the solar-log device
    success = query_csv(current_file, ip_address, config.verbosity)

    if success:
        # If CSV file could be extracted, compare this run to the last
        # New lines will then be written to file
        extract_latest_lines(last_file, current_file, inverter_type, config.verbosity, output_directory)

    elapsed_time = time.time() - start_time
    if config.verbosity > 0:
        print("This request took: ", elapsed_time, " seconds.")

    # Remove the PID file
    if os.path.isfile(pidfile):
        os.unlink(pidfile)
