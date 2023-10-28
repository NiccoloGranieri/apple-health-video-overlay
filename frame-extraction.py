import os
import cv2
import numpy as np
import sys
import json
import datetime
import ffmpeg
import csv

# ToDo: Write a README
# ToDo: Look at other data that could be potentially plotted
# ToDo: Re-Add audio to exported video 

# def CalcRollPitchYaw(accel):
#   accelerationX = float(accel[1]) * 3.9;
#   accelerationY = float(accel[2]) * 3.9;
#   accelerationZ = float(accel[3]) * 3.9;
#   pitch = 180 * np.arctan (accelerationX/np.sqrt(accelerationY*accelerationY + accelerationZ*accelerationZ))/np.pi;
#   roll = 180 * np.arctan (accelerationY/np.sqrt(accelerationX*accelerationX + accelerationZ*accelerationZ))/np.pi;
#   return [round(roll, 2), round(pitch, 2)]

parent = os.getcwd()
heart = cv2.imread("img/heart.png")
gyro = cv2.imread("img/gyro.png")
watch = cv2.imread("img/watch.png")
airpods = cv2.imread("img/airpods.png")


for file in os.listdir(parent):
    if file.lower().endswith(".mov"):
      videoFile = file
      videoPath = os.path.join(parent, file)
      videoProvenance = "iPhone"
    elif file.lower().endswith(".mp4"):
      videoFile = file
      videoPath = os.path.join(parent, file)
      videoProvenance = "GoPro"
    elif file.lower().endswith(".json"):
      workoutDataFile = file
      workoutDataPath = open(os.path.join(parent, file))
    elif file.lower().endswith(".csv"):
      if file.lower().startswith("watch"):
        csvWatchFile = file
        csvWatchPath = os.path.join(parent, file)
      elif file.lower().startswith("headphone"):
        csvHeadphonesFile = file
        csvHeadphonesPath = os.path.join(parent, file)

jsonMetadata = ffmpeg.probe(videoPath)
print(jsonMetadata)

for i in jsonMetadata["streams"]:
  if i.get("index") == 0:
    vidW = i.get("width")
    vidH = i.get("height")    
    vidLen = int(float(i.get("duration")))
    nested = i.get("tags")
    vidFR = float(i.get("r_frame_rate")[:-2])
    if videoProvenance != "GoPro":
      vidCrT = nested.get("com.apple.quicktime.creationdate")[:-5]
      adjVidCrT = datetime.datetime.strptime(vidCrT, '%Y-%m-%dT%H:%M:%S')
    else:
      vidCrT = datetime.datetime.strptime(nested.get("timecode"), '%H:%M:%S:%f')
      vidCrDate = datetime.datetime.strptime(nested.get("creation_time"), '%Y-%m-%dT%H:%M:%S.%fZ')
      temp = vidCrT.replace(year=vidCrDate.year, month=vidCrDate.month, day=vidCrDate.day)
      adjVidCrT = temp - datetime.timedelta(seconds=5, milliseconds=320)

vidEndT = adjVidCrT + datetime.timedelta(seconds=vidLen)
usefulMeta = [vidW, vidH, vidFR, vidLen, adjVidCrT, vidEndT]

timestampedHR = []
timestampedKCAL = []
totalKCAL = []
accellData = []
gyroDataWatch = []
gyroDataPods = []

data = json.load(workoutDataPath)

min = "00:00:00.00"
max = str(datetime.time(0, int(usefulMeta[3] / 60), usefulMeta[3] % 60))
for i in data["laps"][0]["points"]:
      readingTime = datetime.datetime.fromtimestamp(i.get("time"))
      if i.get("kcal"):
        totalKCAL.append([readingTime, i.get("kcal")])
      delta = readingTime - usefulMeta[4] if readingTime > usefulMeta[4] else "00:00:00.00"
      if datetime.datetime.strptime(str(delta), "%H:%M:%S.%f") > datetime.datetime.strptime(min, "%H:%M:%S.%f"):
        if datetime.datetime.strptime(str(delta), "%H:%M:%S.%f") <= datetime.datetime.strptime(max, "%H:%M:%S"):
          if i.get("hr"):
            timestampedHR.append([readingTime, i.get("hr")])
          if i.get("kcal"):
            timestampedKCAL.append([readingTime, i.get("kcal")])

try:
  for line in csv.reader(open(csvWatchPath)):
    if line[0] == "time":
      continue
    else:
      readingTime = datetime.datetime.strptime(line[0], "%Y/%m/%d %H:%M:%S.%f")
      if readingTime > usefulMeta[4] and readingTime < usefulMeta[5]:
        gyroDataWatch.append(line)
except:
  pass

try:
  for line in csv.reader(open(csvHeadphonesPath)):
    if line[0] == "time":
      continue
    else:
      readingTime = datetime.datetime.strptime(line[0], "%Y/%m/%d %H:%M:%S.%f")
      if readingTime > usefulMeta[4] and readingTime < usefulMeta[5]:
        gyroDataPods.append(line)
except:
  pass

accellData.sort()
timestampedHR.sort()
timestampedKCAL.sort()
totalKCAL.sort()
gyroDataWatch.sort()
gyroDataPods.sort()

print(len(accellData))
print(len(timestampedHR))
print(len(timestampedKCAL))
print(len(totalKCAL))

previousKcal = 0
totKcalUpdate = 0
foundVidStart = False
time = usefulMeta[4]
for i in totalKCAL:
  i[1] = i[1] + previousKcal
  previousKcal = i[1]
  if time > i[0] and not foundVidStart:
    totKcalUpdate += 1
  elif time <= i[0] and not foundVidStart:
    foundVidStart = True

vidcap = cv2.VideoCapture(videoPath)

if usefulMeta[0] > usefulMeta[1]:
  orientation = "Horizontal"
  width = usefulMeta[0]
  height = usefulMeta[1] + (usefulMeta[0] - usefulMeta[1])
elif usefulMeta[0] < usefulMeta[1]:
  orientation = "Vertical"
  width = usefulMeta[0] + (usefulMeta[1] - usefulMeta[0])
  height = usefulMeta[1]
else:
  orientation = "Square"
  width = usefulMeta[0]
  height = usefulMeta[1]

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter(sys.path[0] + "/overlayed.mov", fourcc, usefulMeta[2], (width, height))

hrUpdate = 0
gyroUpdate = 0
gyroUpdateWatch = 0
gyroUpdatePods = 0
textPadding = 10
kcal = timestampedKCAL[hrUpdate][1]
totKcal = totalKCAL[totKcalUpdate][1]

print("Processing video...")

expectedFrameCount = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
frameIndex = 0

while frameIndex <= expectedFrameCount:
    print("Frame {} of {}".format(frameIndex, expectedFrameCount))
    ret, frame = vidcap.read()

    if not ret:
      frameIndex -= 1
      continue
    
    if orientation == "Horizontal":
      sqrFrame = cv2.copyMakeBorder(frame, int((usefulMeta[0] - usefulMeta[1]) / 2), int((usefulMeta[0] - usefulMeta[1]) / 2), 0, 0, cv2.BORDER_CONSTANT, 0)
    else:
      sqrFrame = cv2.copyMakeBorder(frame, 0, 0, int((usefulMeta[1] - usefulMeta[0]) / 2), int((usefulMeta[1] - usefulMeta[0]) / 2), cv2.BORDER_CONSTANT, 0)

    font = cv2.FONT_HERSHEY_SIMPLEX

    # bg_color = (0,0,0)
    
    # try:
    #   hrFrame = np.full((sqrFrame.shape), bg_color, dtype=np.uint8)
    #   kcalFrame = np.full((sqrFrame.shape), bg_color, dtype=np.uint8)
    # except:
    #   pass
    
    cv2.putText(sqrFrame, "Apple Watch 6 - Synced Data", (80, sqrFrame.shape[1] - 325), font, 3, (255, 255, 255), 5, cv2.LINE_AA)
    sqrFrame[1625:1705,80:160,:] = heart[0:80,0:80,:]
    # sqrFrame[150:223,80:153,:] = gyro[0:73,0:73,:]
    sqrFrame[50:134,80:137,:] = watch[0:84,0:57,:]
    sqrFrame[250:319,80:187,:] = airpods[0:69,0:107,:]
    # # cv2.rectangle(sqrFrame, (80, 1650), (160, 1730), (0, 0, 255), -1)
    cv2.putText(sqrFrame, "X " + str(round(float(gyroDataWatch[gyroUpdateWatch][1]), 2)), (250, 125), font, 3, (0, 0, 255), 5, cv2.LINE_AA)
    cv2.putText(sqrFrame, "Y " + str(round(float(gyroDataWatch[gyroUpdateWatch][2]), 2)), (850, 125), font, 3, (0, 0, 255), 5, cv2.LINE_AA)
    cv2.putText(sqrFrame, "Z " + str(round(float(gyroDataWatch[gyroUpdateWatch][3]), 2)), (1450, 125), font, 3, (0, 0, 255), 5, cv2.LINE_AA)
    cv2.putText(sqrFrame, "X " + str(round(float(gyroDataPods[gyroUpdatePods][1]), 2)), (250, 315), font, 3, (0, 0, 255), 5, cv2.LINE_AA)
    cv2.putText(sqrFrame, "Y " + str(round(float(gyroDataPods[gyroUpdatePods][2]), 2)), (850, 315), font, 3, (0, 0, 255), 5, cv2.LINE_AA)
    cv2.putText(sqrFrame, "Z " + str(round(float(gyroDataPods[gyroUpdatePods][3]), 2)), (1450, 315), font, 3, (0, 0, 255), 5, cv2.LINE_AA)
    # cv2.putText(sqrFrame, "Pitch " + str(round(float(accellData[gyroUpdate][9]), 2)), (200, 225), font, 3, (0, 0, 255), 5, cv2.LINE_AA)
    # cv2.putText(sqrFrame, "Yaw " + str(round(float(accellData[gyroUpdate][10]), 2)), (800, 225), font, 3, (0, 0, 255), 5, cv2.LINE_AA)
    # cv2.putText(sqrFrame, "Roll " + str(round(float(accellData[gyroUpdate][8]), 2)), (1400, 225), font, 3, (0, 0, 255), 5, cv2.LINE_AA)
    cv2.putText(sqrFrame, str(timestampedHR[hrUpdate][1]) + " HR", (180, sqrFrame.shape[1] - 225), font, 3, (0, 0, 255), 5, cv2.LINE_AA)
    cv2.putText(sqrFrame, "Exercise kcal " + str(f'{kcal:.2f}'), (80, sqrFrame.shape[1] - 130), font, 3, (0, 0, 255), 5, cv2.LINE_AA)
    cv2.putText(sqrFrame, "Total workout kcal " + str(f'{totalKCAL[totKcalUpdate][1]:.2f}'), (80, sqrFrame.shape[1] - 25), font, 3, (0, 0, 255), 5, cv2.LINE_AA)
    
    # xHR,yHR,wHR,hHR = cv2.boundingRect(hrFrame[:,:,2])
    # xKCAL,yKCAL,wKCAL,hKCAL = cv2.boundingRect(kcalFrame[:,:,2])
    
    # xHR -= textPadding
    # yHR -= textPadding
    # hHR += textPadding * 2
    # wHR += textPadding * 2 + hHR

    # xKCAL -= textPadding
    # yKCAL -= textPadding
    # hKCAL += textPadding * 2
    # wKCAL += textPadding * 2 + hKCAL

    # hrFrame[yHR:yHR+180,xHR+wHR-180:xHR+wHR,:] = heart[0:180,0:180,:]
    
    # try:
    #   result = sqrFrame.copy()
    # except:
    #   pass

    # result[yHR:yHR+hHR, xHR:xHR+wHR] = hrFrame[yHR:yHR+hHR, xHR:xHR+wHR]
    # result[yKCAL:yKCAL+hKCAL, xKCAL:xKCAL+wKCAL] = kcalFrame[yKCAL:yKCAL+hKCAL, xKCAL:xKCAL+wKCAL]
    
    writer.write(sqrFrame)

    time += datetime.timedelta(milliseconds=1000/usefulMeta[2])
    
    if time < timestampedHR[hrUpdate][0]:
      pass
    elif time >= timestampedHR[hrUpdate][0] and hrUpdate < len(timestampedHR) - 1:
      hrUpdate += 1
      kcal += timestampedKCAL[hrUpdate][1]
      totKcalUpdate += 1

    try:
      for timestamps in accellData:
        if time < datetime.datetime.strptime(accellData[gyroUpdate][0], "%Y/%m/%d %H:%M:%S.%f"):
            break
        elif time >= datetime.datetime.strptime(accellData[gyroUpdate][0], "%Y/%m/%d %H:%M:%S.%f") and gyroUpdate < len(accellData) - 2:
          print(time)
          print(datetime.datetime.strptime(accellData[gyroUpdate][0], "%Y/%m/%d %H:%M:%S.%f"))
          gyroUpdate += 1
    except:
      pass

    try:
      for timestamps in gyroDataWatch:
        if time < datetime.datetime.strptime(gyroDataWatch[gyroUpdateWatch][0], "%Y/%m/%d %H:%M:%S.%f"):
            break
        elif time >= datetime.datetime.strptime(gyroDataWatch[gyroUpdateWatch][0], "%Y/%m/%d %H:%M:%S.%f") and gyroUpdateWatch < len(gyroDataWatch) - 2:
          print(time)
          print(datetime.datetime.strptime(gyroDataWatch[gyroUpdateWatch][0], "%Y/%m/%d %H:%M:%S.%f"))
          gyroUpdateWatch += 1
    except:
      pass

    try:
      for timestamps in gyroDataPods:
        if time < datetime.datetime.strptime(gyroDataPods[gyroUpdatePods][0], "%Y/%m/%d %H:%M:%S.%f"):
            break
        elif time >= datetime.datetime.strptime(gyroDataPods[gyroUpdatePods][0], "%Y/%m/%d %H:%M:%S.%f") and gyroUpdatePods < len(gyroDataPods) - 2:
          print(time)
          print(datetime.datetime.strptime(gyroDataPods[gyroUpdatePods][0], "%Y/%m/%d %H:%M:%S.%f"))
          gyroUpdatePods += 1
    except:
      pass
      
    frameIndex += 1

# else:
#   success,currentFrame = vidcap.read()
#   frameIndex = 0
#   while success:
#       if orientation == "Horizontal":
#         sqrFrame = cv2.copyMakeBorder(currentFrame, int((usefulMeta[0] - usefulMeta[1]) / 2), int((usefulMeta[0] - usefulMeta[1]) / 2), 0, 0, cv2.BORDER_CONSTANT, 0)
#       else:
#         sqrFrame = cv2.copyMakeBorder(currentFrame, 0, 0, int((usefulMeta[1] - usefulMeta[0]) / 2), int((usefulMeta[1] - usefulMeta[0]) / 2), cv2.BORDER_CONSTANT, 0)
      
#       font = cv2.FONT_HERSHEY_SIMPLEX

#       bg_color = (0,0,0)
      
#       try:
#         bg = np.full((sqrFrame.shape), bg_color, dtype=np.uint8)
#       except:
#         pass
      
#       cv2.putText(bg, str(timestampedHR[hrUpdate][1]), (80, sqrFrame.shape[1] - 200), font, 7, (0, 0, 255), 10, cv2.LINE_AA)

#       x,y,w,h = cv2.boundingRect(bg[:,:,2])
      
#       x -= textPadding
#       y -= textPadding
#       h += textPadding * 2
#       w += textPadding * 2 + h

#       bg[y:y+180,x+w-180:x+w,:] = heart[0:180,0:180,:]
      
#       try:
#         result = sqrFrame.copy()
#       except:
#         pass

#       result[y:y+h, x:x+w] = bg[y:y+h, x:x+w]
      
#       writer.write(result)

#       count += 1

#       if count % usefulMeta[2] == 0:
#         time += datetime.timedelta(0,1)
      
#       if time < timestampedHR[hrUpdate][0]:
#         pass
#       elif time >= timestampedHR[hrUpdate][0] and hrUpdate < len(timestampedHR) - 1:
#         hrUpdate += 1
        
#       frameIndex += 1

writer.release()
os.rename(videoPath, os.path.join(parent, "Done", videoFile))
os.rename(os.path.join(parent, workoutDataFile), os.path.join(parent, "Done", workoutDataFile))
# os.rename(os.path.join(parent, csvFile), os.path.join(parent, "Done", csvFile))
os.rename(os.path.join(parent, "overlayed.mov"), os.path.join(parent, "Exports", str(datetime.datetime.today().replace(microsecond=0)).replace(" ", "_") + ".mov"))