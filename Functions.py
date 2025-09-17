import os; import pandas as pd;import numpy as np; 
import time; import serial

# connect to the LCR meter through serial communication
def DeviceConnect(COMPort):
    ser = serial.Serial(COMPort, 9600, timeout = 1)
    return ser

# disconnect the LCR meter 
def DeviceDisconnect(ser):
    return ser.close()

# send commands to the LCR meter and wait for response
def LCRDataReadout(ser):
    # encode text to ascii. using FETCH? to queary current readout
    ser.write('FETCH?\n'.encode()) 

    # create a readout to store the results
    readout = []

    # read the query response. the second non-empty response is the reading.
    while True:
        readout.append(ser.readline().decode().strip())
        if len(readout) == 2:
            break
        
    return readout[1]

# define function to send commands to the LCR meter and wait for a response.
def LCRCommander(ser, command):
    # encode text to ascii.
    ser.write(f'{command} \n'.encode())

    # read the response. the second non-empty response is confirmation.
    while True:
        # print(ser.readline().decode().strip())
        if ser.readline().decode().strip() == 'exec success':
            break

# define the frequency range and the number of points evenly spaced
def Frequencies(minFreq, maxFreq, numberOfpoints):
    frequencies = np.logspace(np.log10(minFreq), np.log10(maxFreq), num = numberOfpoints)
    return np.round(frequencies).astype(int)

# collect the average data values with standard deviations
def DataAveraging(ser):
    # preallocate data storage array
    data = np.array([0,2])

    # take 10 measurements
    for i in range(0,10):
        data = np.vstack([data, np.float16(LCRDataReadout(ser).split(','))])
    
    # remove the first element which was used to preallocatte the array
    data = np.delete(data, 0, axis = 0)

    # determine the data statistics.
    data = np.array([np.mean(data[::,0]), np.std(data[::,0]), np.mean(data[::,1]), np.std(data[::,1])])
    return data

# create a stablity timer based on frequency
def TimeAdjustments(freq):
    if freq < 100:
        time.sleep(10)
    elif freq <= 1000:
        time.sleep(2)

    
# actual experiment
def Experiment(ser, freqencies, mainMeasurement, minorMeasurement, voltage, biasVoltage):
    # preallocate the data storage dataframe
    df = pd.DataFrame(freqencies, columns = ['Frequency'])
    
    # set the desired voltage and any bias voltage
    LCRCommander(ser, f'VOLT {voltage*1e3}')
    if biasVoltage is not None:
        LCRCommander(ser, f'BIAS:VOLT {int(biasVoltage*1e3)}')

    # setup and measure 
    for k in mainMeasurement:
        # set the major parameter to be measured
        LCRCommander(ser, f'FUNC:IMP:A {k}')

        for i in minorMeasurement:
            # set the minor parameter to be measured
            LCRCommander(ser, f'FUNC:IMP:B {i}')
            
            # create a name for the column
            minorParmName = "-".join([k,i])

            # preallocate data lists to populate per frequency
            majorParamAvg = []
            majorParamStd = []
            minorParamAvg = []
            minorParamStd = []

            for j in freqencies:
                # set the new frequency in the LCR meter
                LCRCommander(ser, f'FREQ {j}')

                # apply some time to allow the measurement to stablize
                TimeAdjustments(j)

                # record a 10 value average
                measurements = DataAveraging(ser)

                # store the values in the lists. each entry is for the corresponding frequency
                majorParamAvg.append(measurements[0])
                majorParamStd.append(measurements[1])
                minorParamAvg.append(measurements[2])
                minorParamStd.append(measurements[3])

            # store the data in the dataframe
            df[f'{k} Avg.'] = majorParamAvg
            df[f'{k} Std.'] = majorParamStd
            df[f'{minorParmName} Avg.'] = minorParamAvg
            df[f'{minorParmName} Std.'] = minorParamStd

    # remove the index column
    df.reset_index(drop = True, inplace = True)
    print(df)
    print('Test completed ✅\n\n')
    return df