#           Foobot Plugin
#
#           Author:     Vincent Saugey, 2018
#
"""
<plugin key="FooBot" name="Foobot (foobot.io)" author="Vincent Saugey <vincent@vsa.ovh>" version="0.1.0" externallink="https://foobot.io/">
    <description>
This is a Domoticz plugin for the FooBot device.
Foobot provides air monitoring products, services and technologies that allow the measurement of indoor pollution, leading to improved air quality in homes, places of work, and indoor public spaces.<br/><br/>
You should request for a <a url="https://api.foobot.io/apidoc/index.html">key</a> to make work this plugin<br/>
<br/>
    </description>
    <params>
        <param field="Username" label="userName" width="300px" required="true"/>
        <param field="Password" label="key" width="800px" required="true"/>
        <param field="Mode5" label="uuid (if many devices are attached to same FooBot account)" width="300px"/>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="No" value="No"/>
                <option label="Yes" value="Yes"/>
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import urllib.parse
import json

class BasePlugin:
    httpConn = None
    runAgain = 10
   
    def __init__(self):
        return

    def onStart(self):
        Domoticz.Heartbeat(30)
        if Parameters["Mode6"] != "No":
            Domoticz.Debugging(1)
            DumpConfigToLog()
        self.createdevices = "Yes" if (len(Devices) == 0) else "No"
        self.httpConn = Domoticz.Connection(Name="Foobot", Transport="TCP/IP", Protocol="HTTPS", Address="api.foobot.io", Port=str(443))
        self.httpConn.Connect()

    def onStop(self):
        Domoticz.Log("onStop - Plugin is stopping.")

    def onConnect(self, Connection, Status, Description):
        if (Status == 0):
            Domoticz.Debug("foobot.io connected successfully.")
            if self.createdevices == "Yes":
                Domoticz.Debug("Send data to list devices")
                url = 'https://api.foobot.io/v2/owner/' + urllib.parse.quote(Parameters["Username"]) + '/device/'
            else:
                Domoticz.Debug("Send data to update devices")
                url = 'https://api.foobot.io/v2/device/' + str(Devices[1].DeviceID) + '/datapoint/0/last/0/'
            sendData = { 'Verb' : 'GET',
                         'URL'  : url,
                         'Headers' : { 'Accept': "application/json; charset=UTF-8", \
                                       'X-API-KEY-TOKEN' : Parameters["Password"], \
                                       'Connection': 'keep-alive', \
                                       'Host': 'https://api.foobot.io', \
                                       'User-Agent':'Domoticz/1.0' }
                       }  
            Connection.Send(sendData)
        else:
            Domoticz.Error("Failed to connect ("+str(Status)+") to: "+api.foobot.io+":"+443+" with error: "+Description)

    def onMessage(self, Connection, Data):
        DumpHTTPResponseToLog(Data)  
        Domoticz.Debug(Data["Data"].decode("utf-8", "ignore"))
        Status = int(Data["Status"])
        if (Status == 200):
            Domoticz.Debug("Good Reply received from Foobot (HTTP 200).")
            if self.createdevices == "Yes":
                resp = json.loads (Data["Data"])
                CreateDevices(resp)
                self.createdevices="No"
                return
            Domoticz.Debug("update devices")
            resp = json.loads (Data["Data"])
            datas=resp['datapoints'][0]
            Domoticz.Log("Update Device with values :" + str(datas))
            Devices[1].Update(nValue = 0, sValue = (str(datas[2]) + ";" + str(datas[3]) + ";1"))
            Devices[2].Update(nValue = int(datas[6]), sValue=str(datas[6]) )  # (Air Quality)
            Devices[3].Update(nValue = int(datas[1]), sValue=str(datas[1])) # pm (ugm3)
            Devices[4].Update(nValue = datas[4], sValue=str(datas[4])) #  co2 (ppm)
            Devices[5].Update(nValue = datas[5], sValue=str(datas[5])) # voc (ppb)
            self.httpConn.Disconnect()
        else:
            Domoticz.Error("Footbot returned a status: "+str(Status))

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

    def onDisconnect(self, Connection):
        Domoticz.Debug("onDisconnect called for connection to: "+Connection.Address+":"+Connection.Port)

    def onHeartbeat(self):
        if (self.httpConn.Connecting() or self.httpConn.Connected()):
            Domoticz.Debug("onHeartbeat called, Connection is alive.")
        else:
            self.runAgain = self.runAgain - 1
            if self.runAgain <= 0:
                self.httpConn.Connect()
                self.runAgain = 10
            else:
                Domoticz.Debug("onHeartbeat called, run again in "+str(self.runAgain)+" heartbeats.")

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

# Generic helper functions
def CreateDevices(resp):
    name = ""
    uuid = 0
    if Parameters["Mode5"]:
        for dev in resp:
            Domoticz.Debug("Found in Reply device Named:" + dev['name'] + " with uuid :" + dev['uuid'])
            if (dev['uuid'] == Parameters["Mode5"]):
                uuid = dev['uuid']
                name = dev['name']
    else:
        if resp[0]:
            uuid = resp[0]['uuid']
            name = resp[0]['name']

    if uuid == 0:    
        Domoticz.Error("Cannot found a device with uuid :" + Parameters["Mode5"] + " in account:" + Parameters["Username"])
        return

    Domoticz.Log("Create devices for :" + name + " with uuid :" + uuid)
    Domoticz.Device(Name=name + " (Temp+Hum)", Unit=1, TypeName="Temp+Hum", DeviceID=uuid).Create()
    Domoticz.Device(Name=name + " (Air Quality)", Unit=2, TypeName="Custom",DeviceID=uuid, Options={"Custom":"1"}).Create()
    Domoticz.Device(Name=name + " pm (ugm3)", Unit=3, TypeName="Custom", DeviceID=uuid, Options={"Custom":"1;µg/m3"}).Create()
    Domoticz.Device(Name=name + " co2 (ppm)", Unit=4, TypeName="Air Quality", DeviceID=uuid).Create()
    Domoticz.Device(Name=name + " voc (ppb)", Unit=5, TypeName="Custom", DeviceID=uuid, Options={"Custom":"1;ppb"}).Create()
       
       
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

def DumpHTTPResponseToLog(httpDict):
    if isinstance(httpDict, dict):
        Domoticz.Debug("HTTP Details ("+str(len(httpDict))+"):")
        for x in httpDict:
            if isinstance(httpDict[x], dict):
                Domoticz.Debug("--->'"+x+" ("+str(len(httpDict[x]))+"):")
                for y in httpDict[x]:
                    Domoticz.Debug("------->'" + y + "':'" + str(httpDict[x][y]) + "'")
            else:
                Domoticz.Debug("--->'" + x + "':'" + str(httpDict[x]) + "'")
