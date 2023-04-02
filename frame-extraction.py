import os
import cv2
import numpy as np
import sys
import csv
import json
import datetime
import ffmpeg
import copy

# ToDo: Write a README
# ToDo: Remove capitalisation in file extension search (i.e. mov MOV)
# ToDo: Simplify moving HR to one of the corners of the image
# ToDo: Start considering TimeStamps of every reading to make HR plotting more accurate
# ToDo: Start thinking of ways of automatically accepting videos from different cameras (i.e. GoPro)
# ToDo: Look at other data that could be potentially plotted
# ToDo: Re-Add audio to exported video 

os.remove("overlayed.mov")

parent = os.getcwd()

heart = cv2.imread("heart.png")

for file in os.listdir(parent):
    if file.endswith(".mov"):
      videoPath = os.path.join(parent, file)
    if file.endswith(".json"):
      workoutData = open(os.path.join(parent, file))

jsonMetadata = ffmpeg.probe(videoPath)

format = jsonMetadata["format"]

for i in jsonMetadata["streams"]:
  if i.get("index") == 0:
    tags = i.get("tags")
    for key in tags:
      if "GoPro" in tags[key]:
        videoProvenance = "GoPro"
      else:
        videoProvenance = "iPhone"
    vidLen = int(float(i.get("duration")))
    nested = format["tags"]
    if videoProvenance != "GoPro":
      vidW = i.get("width")
      vidH = i.get("height")
      vidFR = float(i.get("r_frame_rate")[:-2])
      vidCrT = nested.get("com.apple.quicktime.creationdate")[:-5]
    else:
      vidFR = 120
      vidCrT = nested.get("creation_time")[:-8]
  elif i.get("index") == 1:
    if videoProvenance == "GoPro":
      vidW = i.get("width")
      vidH = i.get("height")    

adjVidCrT = datetime.datetime.strptime(vidCrT, '%Y-%m-%dT%H:%M:%S')
vidEndT = adjVidCrT + datetime.timedelta(seconds=vidLen)
usefulMeta = [vidW, vidH, vidFR, vidLen, adjVidCrT, vidEndT]

print(usefulMeta)

hr = []

data = json.load(workoutData)

min = "00:00:00"
max = str(datetime.time(0, int(usefulMeta[3] / 60), usefulMeta[3] % 60))

for i in data["laps"][0]["points"]:
    if i.get("hr"):
        hrTime = datetime.datetime.fromtimestamp(i.get("time"))
        delta = hrTime - usefulMeta[4]
        try:
          if datetime.datetime.strptime(str(delta), "%H:%M:%S") >= datetime.datetime.strptime(min, "%H:%M:%S"):
            if datetime.datetime.strptime(str(delta), "%H:%M:%S") <= datetime.datetime.strptime(max, "%H:%M:%S"):
              hr.append(i.get("hr"))
        except:
           pass
        # print(i.get("time"))
        # print(datetime.datetime.fromtimestamp(i.get("time")))

hrFrameUpdate = (usefulMeta[2] * vidLen) / len(hr)

vidcap = cv2.VideoCapture(videoPath)
success,currentFrame = vidcap.read()
success,previousFrame = vidcap.read()
count = 0

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter(sys.path[0] + "/overlayed.mov", fourcc, usefulMeta[2], (usefulMeta[1], usefulMeta[0]))

count = 0
hrUpdate = 0
textPadding = 10

print("Processing video...")
while success:
  font = cv2.FONT_HERSHEY_SIMPLEX

  bg_color = (0,0,0)
  bg = np.full((currentFrame.shape), bg_color, dtype=np.uint8)

  cv2.putText(bg, str(hr[hrUpdate]), (80, 1000), font, 3, (0, 0, 255), 2, cv2.LINE_4)

  x,y,w,h = cv2.boundingRect(bg[:,:,2])

  bg[y:y+66,x+w+5:x+w+71,:] = heart[0:66,0:66,:]

  x -= textPadding
  y -= textPadding
  w += textPadding * 2 + 66
  h += textPadding * 2
  result = currentFrame.copy()
  result[y:y+h, x:x+w] = bg[y:y+h, x:x+w]

  writer.write(result)

  previousFrameBW = cv2.cvtColor(copy.deepcopy(currentFrame), cv2.COLOR_BGR2GRAY)
  success,currentFrame = vidcap.read()

  if success:
    currentFrameBW = cv2.cvtColor(currentFrame, cv2.COLOR_BGR2GRAY)

  comparison = cv2.absdiff(previousFrameBW, currentFrameBW)
  thresh = 55
  comparison[comparison < thresh] = 0
  comparison[comparison >= thresh] = 255
  
  if count == 0:
    # interpPF = np.interp(previousFrameBW, (0, 255), (0, 1))
    # interpCF = np.interp(currentFrameBW, (0, 255), (0, 1))
    # accumulateFrames = np.add(interpPF, interpCF)
    interComp = np.interp(comparison, (0, 255), (0, 1))
    accumulateFrames = copy.deepcopy(interComp)
  else:
    # interpPF = np.interp(comparison, (0, 255), (0, 1))
    # accumulateFrames = np.add(comparison, accumulateFrames)
    interComp = np.interp(comparison, (0, 255), (0, 1))
    add = np.add(accumulateFrames, interComp)
    accumulateFrames = copy.deepcopy(add)
  
  cv2.imshow('result', accumulateFrames)
  cv2.waitKey(1)
  print(accumulateFrames)
  
  count += 1

  if count % int(hrFrameUpdate) == 0 and hrUpdate < len(hr) - 1:
    hrUpdate += 1

writer.release()
# showFrames = np.interp(accumulateFrames, (accumulateFrames.min(), accumulateFrames.max() ), (0, 1))
