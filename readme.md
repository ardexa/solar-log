
# Purpose
The purpose of this project is to collect data from Solar Log devices and send the data to the cloud using Ardexa. Data from Solar Log is read using a Linux device such as a Raspberry Pi, or an X86 intel powered computer. 

## How does it work
A Solar Log device is a product that allows data to be collected from solar inverters. See -> http://www.solar-log.com. This product does not make it easy to store data locally. This project allows data to be collected and either stored locally and/or sent to the Ardexa cloud. These python scripts have been tested on Linux systems and a number of Solar Log devices. If there are any issues with other Solar Log devices, please let us know.

This script will take an IP address of the Solar Log device, and do the following:
- Query a Solar Log device and call down all available data using http.
- Compare the changes to the previous run (so the first run will NOT produce any data)
- Send any changes to a local file and/or to the cloud via the Ardexa agent
- All data is stored in a user specified log directory.
- A check to make sure it can only run once. 
- Extract data from connected SMA, ABB or Refusol inverters. Other inverters can be supported. If they are not, please contact us

The Solar Log will take about 5 to 10 minutes to download a month's worth of data (yes, that long!). So the frequency (time between runs) of the script should not be lower than about 10 minutes. Some of the newer models will return data in less than 5 minutes. Also, data from the inverter is copied by the Solar Log every 5 minutes. This is not configurable in Solar Log.

## Installation
To install the scripts, do the following
```
sudo apt-get update
sudo apt-get install -y python-pip
sudo pip install requests
cd
git clone https://github.com/ardexa/solar-log.git
cd solar-log/script
```

## Running the script
The script does not need root privileges. So you an run it as follows:
```
python ardexa-solar-log.py {IP address} {inverter type} {solar-log-type} {log directory} {debug} 
example: `python ardexa-solar-log.py 192.168.1.55 ABB new /opt/ardexa 0`
```

- The `IP Address` is the IP address of the Solar Log device. 
- The `inverter-type` is either `SMA`, `ABB` or `Refusol` inverters. If you need other inverter types, contact us.
- The 'solar log type is either `NEW` or `OLD`. Older Solar Log devices with a software firmware of less than about 3.0 (Build 60. March 2014), then that is an `OLD` version. Also note that the `OLD` style Solar Log devices may stop recording when the inverter is turned off (ie; when the Sun goes down), whereas the `NEW` inverters will write a record all times.
- The `log directory` is where data will be written.
- Debug is a number between 0 (no debug) and 3

## Collecting to the Ardexa cloud
Collecting to the Ardexa cloud is free for up to 3 Raspberry Pis (or equivalent). Ardexa provides free agents for ARM, Intel x86 and MIPS based processors. To collect the data to the Ardexa cloud do the following:
- Create a `RUN` scenario to schedule the Ardexa Kaco script to run at regular intervals, but no less than about 330 seconds.
- Then use a `CAPTURE` scenario to collect the csv (comma separated) data from the filename `/opt/ardexa/solar-log/logs/{inverter}/latest.csv`. This file contains a header entry (as the first line) that describes the CSV elements of the file.

## Help
Contact Ardexa at support@ardexa.com, and we'll do our best efforts to help.


