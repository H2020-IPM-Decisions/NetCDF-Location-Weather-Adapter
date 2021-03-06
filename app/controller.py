#    Copyright (C) 2021  Tor-Einar Skog,  NIBIO
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

from models import WeatherData, LocationWeatherData
from interpolator import Interpolator
from negotiator import Negotiator
from datetime import datetime
import time
import os
import sys

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

filename= SITE_ROOT + '/../weather_data/all.nc'
#print (filename, file =sys.stderr)
param_mapping = {
    1001: "t2m",
    1002: "t2m",
    2001: "rr",
    3001: "rh2m",
    3002: "rh2m",
    4002: "ff10m",
    4012: "ff10m"
}

kelvin_0c = 272.15

interval = 3600 # Hourly values, always

class Controller:
    def __init__(self):
        pass
        #start_time = time.time()
        #self.ip = Interpolator(filename, config)
        #print("New Controller initialized. It took %s seconds." % (time.time() - start_time), file =sys.stderr)

    def get_weather_data(self, longitude, latitude, parameters):
        # If no parameters, use all that DWD provides
        if parameters == None:
            parameters = [1001,2001,3001,4012]
        qc = [1 for p in parameters] # We trust Deutsche WetterDienst. Aber natürlich!
        
        retval = WeatherData(
            weatherParameters=parameters, interval=interval
            )
        location_weather_data = LocationWeatherData(longitude=longitude, latitude=latitude, QC=qc)
        

        # TESTING
        
        #ip=Interpolator(filename,config);

        lons = [float(longitude)] # Working example: [10.965]
        lats = [float(latitude)] # Working example: [50.109]
        #res = self.ip.interpolate(lats,lons)[0] # Using only one coordinate for now

        directory= SITE_ROOT + "/../coms";
        negotiator=Negotiator(directory);
        path=negotiator.request(lats,lons);
        res=negotiator.listen(path);
        #print(ret);

        #return retval.as_dict()

        
        #print("Results:",res)
        if res == []:
            return {}
        first_epoch = res[0]["time"]
        last_epoch = res[len(res)-1]["time"]

        retval.timeStart = "%sZ" % datetime.utcfromtimestamp(first_epoch).isoformat()
        retval.timeEnd = "%sZ" % datetime.utcfromtimestamp(last_epoch).isoformat()

        #data = [None] * (1 + int((last_epoch - first_epoch) / interval))
        data = []
        previous_time = first_epoch
        for time_paramdict in res:
            row_index = int((time_paramdict["time"] - first_epoch) / interval)
            # If the interval changes from hourly to something else, 
            # adjust timeEnd and stop adding data
            if (row_index > 0) and (time_paramdict["time"] - previous_time > interval):
                retval.timeEnd = "%sZ" % datetime.utcfromtimestamp(previous_time).isoformat()
                break
            data.append([None] * len(parameters))
            #data[row_index] = 
            for idx, parameter in enumerate(parameters):
                strval = time_paramdict.get(param_mapping[parameter], None)
                value = float(strval) if strval is not None else None
                
                if value is not None and parameter < 2000: # Temp is in kelvin
                    value = value - kelvin_0c
                # Rainfall must be shifted 1 hr back
                #print(data)
                if parameter == 2001 and row_index > 0:
                    data[row_index - 1][idx] = value
                else:
                    data[row_index][idx] = value
            previous_time = time_paramdict["time"]
            #print("%sZ: %s" % (datetime.utcfromtimestamp(time_paramdict["time"]).isoformat(), time_paramdict["rr"]))
        
        location_weather_data.data = data
        retval.locationWeatherData.append(location_weather_data)
        return retval.as_dict()