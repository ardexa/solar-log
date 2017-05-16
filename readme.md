
# Purpose
The purpose of this project is to collect from Solar Log devices and send the data to your cloud using Ardexa. Data from Solar Log is read using a Linux device such as a Raspberry Pi, or an X86 intel powered computer. 

## How does it work
A Solar Log device allows data to be collected from solar inverters. See -> http://www.solar-log.com/en/home.html. This python script allows data to be collected and either stored locally and/or sent to another site, and/or sent to the Ardexa cloud.
The python script has been tested on Linux systems. The script has been tested on a Solar-1200. If there are any issues with other Solar Log devices, please let us know.

This script will take an IP address of the Solar Log device, and do the following:
- Query a Solar Log device and call down all available data. The Solar Log stores a maximum of 1 month's worth of data.
- Compare the changes to the previous run (so the first run will NOT produce any data)
- Send any changes to a local file and to the cloud via the Ardexa agent
- All data is stored in the /opt/ardexa/solar-log directory. Data is stored in a daily file
- A check to make sure it can only run once
- Extract data from connected SMA, ABB or Refusol inverters. Other inverters should be supported. If they are not, please contact us

The Solar Log will take about 5 minutes to download a month's worth of data (yes, about 5 minutes!). So the frequency (time between runs) of the script should not be lower than about 6 minutes. Also, 
data from the inverter is copied by the Solar Log every 5 minutes. This is not configurable in Solar Log.

Make sure the Solar Log is installed and running, as per the manufacturer's instructions.

## Configure the script
Firstly, make sure you have the dependancies to run the script
```
sudo apt-get update
sudo apt-get install -y python-pip
sudo pip install requests
```

Then install and run it as follows:
Note that the applications should be run as root only since needs access to a device in the `/dev` directory. 
```
cd
git clone https://github.com/ardexa/solar-log.git
cd solar-log
sudo python ./ardexa-solar-log.py {inverter-type} {IP Address} .... example: `sudo python ./ardexa-solar-log.py refusol 192.168.0.109`
```

The `{inverter-type}` is either `SMA`, `ABB` or `Refusol` inverters. The `{IP Address}` is the IP address of the Solar Log device. Data will be written to the directory `/opt/ardexa/solar-log/logs/`, based on inverter number.

## Collecting to the Ardexa cloud
Collecting to the Ardexa cloud is free for up to 3 Raspberry Pis (or equivalent). Ardexa provides free agents for ARM, Intel x86 and MIPS based processors. To collect the data to the Ardexa cloud do the following:
a. Create a `RUN` scenario to schedule the Ardexa Kaco script to run at regular intervals, but no less than about 330 seconds.
b. Then use a `CAPTURE` scenario to collect the csv (comma separated) data from the filename `/opt/ardexa/solar-log/logs/{inverter}/latest.csv`. This file contains a header entry (as the first line) that describes the CSV elements of the file.

## Help
Contact Ardexa at support@ardexa.com, and we'll do our best efforts to help.


