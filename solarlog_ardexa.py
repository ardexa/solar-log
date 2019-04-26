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
import urllib2
import datetime
import click
import requests
from dateutil.parser import isoparse
import ardexaplugin as ap

PY3K = sys.version_info >= (3, 0)

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError

PIDFILE = 'ardexa-solar-log-'
LAST_READING = 'last.txt'
CURRENT = 'current.csv'
COMPLETE_STRING = "\"777\":3,"
HEADER_LST = {
    "sma": [
        "Datetime", "Inverter", "AC power (W)", "Daily Energy (Wh)", "Status", "Error", "DC Power 1 (W)",
        "DC Voltage 1 (V)", "AC Voltage (V)", "DC Current 1 (A)", "AC Current (A)"],
    "refusol": [
        "Datetime", "Inverter", "AC power (W)", "Daily Energy (Wh)", "Status", "Error", "DC Power 1 (W)",
        "DC Voltage 1 (V)", "Temperature (C)", "AC Voltage (V)"],
    "abb": [
        "Datetime", "Inverter", "AC power (W)", "Daily Energy (Wh)", "Status", "Error", "DC Power 1 (W)",
        "DC Power 2 (W)", "DC Voltage 1 (V)", "DC Voltage 2 (V)", "Temperature (C)", "AC Voltage (V)"],
    "solarmax": [
        "Datetime", "Inverter", "AC power (W)", "Daily Energy (Wh)", "Status", "DC Power 1 (W)",
        "DC Power 2 (W)", "DC Power 3 (W)", "DC Voltage 1 (V)", "DC Voltage 2 (V)", "DC Voltage 3 (V)",
        "Temperature (C)", "AC Voltage (V)"],
}

REFUSOL = 'refusol'
SMA = 'sma'
ABB = 'abb'
SOLARMAX = 'solarmax'

DEBUG = 0

# These next items detail the number of items in a **RAW** event line
INVERTER_ITEMS = {}
INVERTER_ITEMS[SMA] = 10
INVERTER_ITEMS[ABB] = 11
INVERTER_ITEMS[REFUSOL] = 9
INVERTER_ITEMS[SOLARMAX] = 12


def fix_time(sltime):
    """ This will fix up the solar-log time. There are problems with it"""
    hour, minute, rest = sltime.split(':')
    seconds, pm = rest.split()

    if DEBUG > 1:
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

    if DEBUG > 1:
        print("After processing.....Hour: ", hour, " Minute: ", minute, " Seconds: ", seconds, " pm: ", pm)

    return str(hour) + ":" + str(minute) + ":" + str(seconds)


def process_inverters(timestamp_with_tz, items, inverter_type, log_directory):
    """This function will split the items by inverter and log the results into
    separate files"""

    if inverter_type not in INVERTER_ITEMS:
        print("FATAL ERROR: Unknown inverter_type (header): " + inverter_type)
        sys.exit(1)

    items_per_inverter = INVERTER_ITEMS[inverter_type]

    num_items = len(items)
    # Once the date and time have been removed, the number of items in the
    # line should be divisible by the items_per_inverter. If this is not the case,
    # raise an error
    inverter_count = num_items / items_per_inverter
    remainder = num_items % items_per_inverter

    if DEBUG >= 2:
        print("Inverter type: " + inverter_type)
        print("Item count: " + num_items)
        print("Inverter count: " + inverter_count)
        print("Items: " + items)

    if remainder != 0:
        print("The line reported by solar-log is not recognised. Here is the line: {}".format(",".join(items)))
        return

    # Add inverter type to the log directory
    log_directory = os.path.join(log_directory, inverter_type)
    # All inverters use the same file name
    log_filename = time.strftime("%Y-%m-%d") + ".csv"

    # for each inverter, slice off the items, attach the datetime and write the output
    for _run in range(inverter_count):
        inverter_slice = items[:items_per_inverter]
        del items[:items_per_inverter]
        if DEBUG >= 2:
            print("Inverter slice: {}".format(inverter_slice))

        inverter_number = inverter_slice[0]
        inverter_slice.insert(0, timestamp_with_tz)

        converted_line = ",".join(inverter_slice) + "\n"
        header = "# " + ",".join(HEADER_LST[inverter_type]) + "\n"

        # Add inverter number to the log directory
        log_dir = os.path.join(log_directory, inverter_number)
        ap.write_log(log_dir, log_filename, header, converted_line, DEBUG, True, log_dir, "latest.csv")


def query_csv(current, ip_addr, debug):
    """ This function will query the latest solar-log CSV file"""

    success = False

    url1 = 'http://' + ip_addr + '/sec/export_min.csv'
    url2 = 'http://' + ip_addr + '/export_min.csv'
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


# Naive date parsing
def parse_time(inverter_type, date_val, time_val):
    if inverter_type == SMA:
        time_val = fix_time(time_val)

    date_val = date_val.replace('/', '.')
    return datetime.datetime.strptime(date_val + " " + time_val, '%d.%m.%y  %H:%M:%S')


def extract_latest_lines(current, inverter_type, log_directory):
    """ This function will extract any new lines. If there is a last_reading file, it will read through the current file logging all newer entries and then quit when it finds a time beyond this. If there is no last_reading, it will simply log the latest reading only and then quit"""

    checkpoint_file = os.path.join(log_directory, LAST_READING)
    last_timestamp = None
    most_recent_timestamp = None
    try:
        with open(checkpoint_file, 'rb') as last_file:
            last_timestamp_str = last_file.readline().strip()
            # The datetime is deliberately treated in a naive way
            last_timestamp = isoparse(last_timestamp_str)
            if last_timestamp.utcoffset() is not None:
                print("FATAL ERROR: LAST timestamp contains an unexpected timezone offset")
                sys.exit(1)
            last_timestamp = last_timestamp.replace(microsecond=0)
    except:
        pass

    if DEBUG:
        print("Last Timestamp:", last_timestamp)

    try:
        with open(current, 'r') as current_file:
            for line in current_file:
                if line[0] == '#':
                    continue

                record = line.strip().split(';')
                date_val = record.pop(0)
                time_val = record.pop(0)
                line_timestamp = parse_time(inverter_type, date_val, time_val)
                # Times from solarlog are local, attach a timezone
                timestamp_with_tz = line_timestamp.strftime('%Y-%m-%dT%H:%M:%S') + time.strftime("%z")

                if DEBUG:
                    print("Current line Timestamp:", line_timestamp)
                    print("Current line Timestamp_tz:", timestamp_with_tz)
                if DEBUG >= 2:
                    print("Current Line:", line)

                if last_timestamp is None or line_timestamp > last_timestamp:
                    if DEBUG:
                        print("New Line at time: {} Line: {}".format(timestamp_with_tz, ",".join(record)))

                    process_inverters(timestamp_with_tz, record, inverter_type, log_directory)
                    # track the latest timestamp to write to our config file
                    if most_recent_timestamp is None or line_timestamp > most_recent_timestamp:
                        most_recent_timestamp = line_timestamp

                    # if there was no "last" datetime, only log one record
                    if last_timestamp is None:
                        break
    except FileNotFoundError:
        pass

    if most_recent_timestamp is not None:
        try:
            with open(checkpoint_file, 'w') as last_reading_file:
                last_reading_file.write(most_recent_timestamp.strftime('%Y-%m-%dT%H:%M:%S'))
        except FileNotFoundError:
            print("ERROR: Failed to update LAST reading state")


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
    global DEBUG
    DEBUG = verbose
    config.verbosity = verbose


@cli.command()
@click.argument('ip_address')
@click.argument('inverter_type')
@click.argument('output_directory')
@click.option('--old', is_flag=True)
@click.option('--skip-prep', is_flag=True)
@CONFIG
def log(config, ip_address, inverter_type, output_directory, old, skip_prep):
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

    inverter_type = inverter_type.lower()
    if inverter_type not in (SMA, REFUSOL, ABB, SOLARMAX):
        print("Only Solarmax, Refusol, ABB or SMA inverters collected by Solar-Log are supported at this time")
        sys.exit(8)

    start_time = time.time()

    # Issue a query to get the solar-log to 'prepare' the CSV file
    if not skip_prep:
        if old:
            prepare_old(ip_address, config.verbosity)
        else:
            prepare_new(ip_address, config.verbosity)

    # Define the current
    current_file = os.path.join(output_directory, CURRENT)

    # Try to download the CSV file from the solar-log device
    success = query_csv(current_file, ip_address, config.verbosity)

    if success:
        # If CSV file could be extracted, compare this run to the last
        # New lines will then be written to file
        extract_latest_lines(current_file, inverter_type, output_directory)

    elapsed_time = time.time() - start_time
    if config.verbosity > 0:
        print("This request took: ", elapsed_time, " seconds.")

    # Remove the PID file
    if os.path.isfile(pidfile):
        os.unlink(pidfile)

if __name__ == "__main__":
    cli()
