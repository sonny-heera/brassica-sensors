# brassica-sensors
Garden monitoring sensor setup

## Dependencies
The following dependencies need to be installed on the development board. For a Raspberry Pico, start the micropython terminal and execute the following:
```console
import mip
mip.install("umqtt.simple")
```

Manually copy the bme280.py file to the development board.

## Configuration
Update the config.json file and copy to the development board.

## Running
Copy the the main.py file to the board.